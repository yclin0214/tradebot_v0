import threading

from ib_insync import *
from datetime import datetime, date, timedelta
from TradeManager import TradeManager
from TradeStrategy import TradeStrategy


AVG_24HR = "avg_24hr"
HIGH_24HR = "high_24hr"
AVG_15DAY = "avg_15day"
HIGH_15DAY = "high_15day"
DTE = "dte"
ESTIMATED_THETA = "estimated_theta"
STRIKE = "strike"


# On start-up, scan the account positions related to this ticker; register callback to handle event accordingly
# data_stream -> callback -> buy_sell_decision -> trade_event -> trade_event_callback
class CoveredCallOperation:
    def __init__(self, stock_symbol: str, ib_client: IB, trade_strategy: TradeStrategy, short_term_dte=30):
        self.symbol = stock_symbol
        self.ib = ib_client
        # Position tracker for the symbol
        self.account_position = []
        self.share_count = 0
        self.option_positions = []
        self.short_term_call_contract = None
        self.short_term_call_position = None

        self.stock_1day_df = None

        # Managing analytics
        self.short_term_dte_limit = short_term_dte  # need to be less than a month
        self.existing_option_analytics_map = {}
        self.option_analytics_map = {}
        # Managing trade activities
        self.trade_strategy = trade_strategy
        self.trade_manager_to_buyback_calls = TradeManager(self.ib, to_sell=False, to_buy=True)
        self.trade_manager_to_sell_calls = TradeManager(self.ib, to_sell=True, to_buy=False)

        # Managing subscription; un/subscribe to the ticker data streams
        self.stock_ticker = None
        self.short_term_call_data_sub_list = []
        self.subscribe_to_stock_data_streams()
        self.subscribe_option_data_streams()

        # Managing IB_Insync client
        # On position event important. Only release the trade lock when the position event is changed,
        # Or the trade is cancelled from the trade manager
        self.ib.disconnectedEvent += self.on_ib_disconnect
        self.ib.connectedEvent += self.on_ib_connect
        self.ib.positionEvent += self.on_position_event

    def on_ib_disconnect(self):
        self.unsubscribe_option_data_streams()
        return

    def on_ib_connect(self):
        self.stock_1day_df = self.req_1day_data()
        self.subscribe_to_stock_data_streams()
        self.subscribe_option_data_streams()
        return

    def on_position_event(self):
        self.subscribe_option_data_streams()
        return

    def refresh_ticker_positions(self):
        positions = self.ib.positions()
        for position in positions:
            current_contract = position.contract
            if current_contract.symbol != self.symbol:
                continue
            if isinstance(current_contract, Stock):
                self.share_count = position.position
            elif isinstance(current_contract, Option):
                self.option_positions.append(position)
        self.short_term_call_position()

        return

    def short_term_call_position(self):
        for position in self.option_positions:
            expiration_date_str = position.contract.lastTradeDateOrContractMonth
            contract_type = position.contract.right
            expiration_date = datetime.strptime(expiration_date_str, "%Y%m%d")
            today_date = datetime.now()
            if (expiration_date - today_date).days <= self.short_term_dte_limit and contract_type in ['C', 'CALL']:
                self.short_term_call_position = position
                self.short_term_call_contract = position.contract
                self.short_term_call_contract.exchange = "SMART"
                return
        return

    def subscribe_to_stock_data_streams(self):
        stk_contract = Stock(self.symbol, "SMART", currency="USD")
        self.stock_ticker = self.ib.reqMktData(stk_contract)
        self.stock_ticker.updateEvent += self.share_price_update_callback
        return

    def subscribe_option_data_streams(self):
        # Reset subscription
        self.unsubscribe_option_data_streams()
        self.refresh_ticker_positions()
        if self.short_term_call_position is None:
            return
        if self.short_term_call_position.position != 0:
            print("Found short term short call position. Let's see if we need to buy back")
            st_ticker = self.ib.reqMktData(self.short_term_call_contract)
            st_ticker.updateEvent += self.buy_short_term_call_callback
            self.short_term_call_data_sub_list.append(self.short_term_call_contract)
        else:
            # subscribe to candidate stream positions
            print("More short term positions can be open. Let's see if we can sell some")
            st_call_contracts = self.get_covered_call_candidates(CoveredCallOperation.get_next_n_fridays(4))
            for st_call_contract in st_call_contracts:
                st_ticker = self.ib.reqMktData(st_call_contract)
                st_ticker.updateEvent += self.sell_short_term_call_callback
                self.short_term_call_data_sub_list.append(st_call_contract)
        return

    def unsubscribe_option_data_streams(self):
        for st_contract in self.short_term_call_data_sub_list:
            self.ib.cancelMktData(st_contract)
        # reset the subscription list
        self.short_term_call_data_sub_list = []
        return

    def sell_short_term_call_callback(self, ticker_event: Ticker):
        option_contract = ticker_event.contract
        if not isinstance(option_contract, Option):
            return

        key = CoveredCallOperation.get_contract_key(option_contract)

        # we don't support selling multiple different short term options at different strikes/expiration date
        if self.short_term_call_position.position != 0 or self.short_term_call_contract is not None:
            if self.get_contract_key(self.short_term_call_contract) != key:
                return

        ask = ticker_event.ask
        bid = ticker_event.bid
        expected_price = (ask + bid)/2

        if key not in self.option_analytics_map:
            self.get_option_contract_analytics_data(option_contract)

        dte = self.option_analytics_map[key][DTE]

        expected_theta = expected_price / dte
        self.option_analytics_map[key][ESTIMATED_THETA] = expected_theta
        # If the theta is too low, then we need to pass up as there isn't much time decay left to collect
        if expected_theta < 0.12:
            print("Not going to trade. Theta too low. DTE: " + str(dte) + " Expected_Theta: " + str(expected_theta))
            return

        quantity = self.share_count - abs(100 * self.short_term_call_position.position)

        # Execute the trade
        if expected_price >= self.option_analytics_map[key][HIGH_15DAY]:
            self.place_sell_order(option_contract, quantity, ask, round(1.1 * bid, 1))
            return

        if expected_price >= self.option_analytics_map[key][HIGH_24HR]:
            self.place_sell_order(option_contract, quantity, ask, round(1.1 * bid, 1))
            return

        if 2 * expected_price >= self.option_analytics_map[key][HIGH_24HR] + self.option_analytics_map[key][AVG_24HR]:
            self.place_sell_order(option_contract, quantity, ask, round(1.1 * bid, 1))
            return

        if expected_price >= self.option_analytics_map[key][AVG_15DAY]:
            self.place_sell_order(option_contract, quantity, ask, round(1.1 * bid, 1))
            return

        self.place_sell_order(option_contract, quantity, ask, round(expected_price, 1))

        return

    def buy_short_term_call_callback(self, ticker_event: Ticker):
        option_contract = ticker_event.contract
        ask = ticker_event.ask
        bid = ticker_event.bid

        assert self.get_contract_key(option_contract) == self.get_contract_key(self.short_term_call_contract)

        key = CoveredCallOperation.get_contract_key(option_contract)
        if key not in self.existing_option_analytics_map:
            self.get_option_contract_analytics_data(self.short_term_call_contract)

        expected_price = (ask + bid) / 2
        dte = self.existing_option_analytics_map[key][DTE]
        if dte < 8: # friday, weekend -> to next friday
            if expected_price/dte < 0.04:  # for a week, it means less than 0.2/contract value left
                self.place_buy_order(self.short_term_call_contract,
                                     self.short_term_call_position.position,
                                     ask, bid)
        return

    def share_price_update_callback(self, ticker_event: Ticker):
        stock_contract = ticker_event.contract
        ask = ticker_event.ask
        bid = ticker_event.bid
        volume = ticker_event.volume
        return

    # Todo: here - we need to consider the scenario of potential double trade
    def place_sell_order(self, call_contract, quantity, current_ask, minimum_ask):
        open_trades = self.ib.openTrades()
        self.ib.sleep(1)
        for open_trade in open_trades:
            if open_trade.contract.symbol == self.symbol \
                    and open_trade.orderStatus not in OrderStatus.DoneStates \
                    and isinstance(open_trade.contract, Option):
                expiration_date = datetime.strptime(open_trade.contract.lastTradeDateOrContractMonth, "%Y%m%d")
                today_date = datetime.now()
                if (expiration_date - today_date).days <= self.short_term_dte_limit \
                        and open_trade.contract.right in ['C', "CALL"]:
                    print("There are other pending call option trades for short term; won't proceed")
                    return
        if self.trade_manager_to_sell_calls.is_trade_manager_busy():
            print("Trade manager is busy. Need to wait until trade manager finishes the work. Exit for now")
            return
        # Todo: can add callback to current trade object
        current_trade = self.trade_manager_to_sell_calls.execute_trade(
            self.symbol,
            call_contract,
            self.stock_ticker,
            quantity,
            minimum_ask,
            current_ask)
        return current_trade

    def place_buy_order(self, call_contract, quantity, maximum_bid, current_bid):
        open_trades = self.ib.openTrades()
        self.ib.sleep(1)
        for open_trade in open_trades:
            if open_trade.contract.symbol == self.symbol \
                    and open_trade.orderStatus not in OrderStatus.DoneStates \
                    and isinstance(open_trade.contract, Option):
                expiration_date = datetime.strptime(open_trade.contract.lastTradeDateOrContractMonth, "%Y%m%d")
                today_date = datetime.now()
                if (expiration_date - today_date).days <= self.short_term_dte_limit \
                        and open_trade.contract.right in ['C', "CALL"]:
                    print("There are other pending call option trades for short term; won't proceed")
                    return
        if self.trade_manager_to_buyback_calls.is_trade_manager_busy():
            print("Trade manager is busy. Need to wait until trade manager finishes the work. Exit for now")
            return
        current_trade = self.trade_manager_to_buyback_calls.execute_trade(
            self.symbol,
            call_contract,
            self.stock_ticker,
            quantity,
            current_bid,
            maximum_bid)
        return current_trade

    # if the trade order is cancelled but trade manager is still busy, it means the trade manager
    # is still executing the trade; the cancellation is temporary and we shouldn't reset in that case.
    # Simply by querying the is_busy_lock status will give us the information
    def on_order_cancelled(self, trade: Trade):
        if self.trade_manager_to_sell_calls.get_is_busy_lock().locked() or \
                self.trade_manager_to_buyback_calls.get_is_busy_lock().locked():
            print("Trade Manager is busy. Cannot reset option trade for now")
            return
        # because the event loop is single-threaded, we don't need to acquire the lock again
        self.reset_option_trade()

        return

    def on_order_filled(self, trade: Trade):
        self.reset_option_trade()
        return

    def reset_option_trade(self):
        self.refresh_ticker_positions()
        self.unsubscribe_option_data_streams()
        self.subscribe_option_data_streams()
        return

    # Todo: this needs to be replaced by the strategy class
    def get_covered_call_candidates(self, date_str_list):
        # to return a list of short term call contract
        price_list = self.stock_ticker["close"].values.tolist()
        adaptive_pred = [0] * len(price_list)
        for i in range(40, len(price_list)):
            if price_list[i] >= price_list[i - 30] * 1.35:
                adaptive_pred[i] = 1.1 * price_list[i]
            elif price_list[i] >= price_list[i - 10] * 1.15:
                adaptive_pred[i] = 1.15 * price_list[i]
            else:
                adaptive_pred[i] = 1.2 * price_list[i]

        potential_strike_price_list = [int(adaptive_pred[-1]/5) * 5 + k*5 for k in range(1, 4)]

        st_contracts = []
        for date_str in date_str_list:
            for strike_price in potential_strike_price_list:
                st_contracts.append(Option(symbol=self.symbol,
                                           lastTradeDateOrContractMonth=date_str,
                                           strike=strike_price,
                                           right='C',
                                           exchange='SMART',
                                           currency="USD"))

        for st_contract in st_contracts:
            self.get_option_contract_analytics_data(st_contract)

        return st_contracts

    def get_option_contract_analytics_data(self, option_contract: Option):
        expiration_date = datetime.strptime(option_contract.lastTradeDateOrContractMonth, "%Y%m%d")
        today_date = datetime.now()
        dte = (expiration_date - today_date).days
        assert dte > 0
        option_df = self.req_15day_1hour_option_data(option_contract)
        high_list = option_df["high"].values.tolist()
        avg_24hr = sum(high_list[-24:]) / len(high_list[-24:])
        high_24hr = max(high_list[-24:])
        avg_15day = sum(high_list) / len(high_list)
        high_15day = max(high_list)
        key = CoveredCallOperation.get_contract_key(option_contract)
        self.option_analytics_map[key] = {}
        self.option_analytics_map[key][AVG_24HR] = avg_24hr
        self.option_analytics_map[key][HIGH_24HR] = high_24hr
        self.option_analytics_map[key][AVG_15DAY] = avg_15day
        self.option_analytics_map[key][HIGH_15DAY] = high_15day
        self.option_analytics_map[key][DTE] = dte
        self.option_analytics_map[key][ESTIMATED_THETA] = avg_15day/dte
        self.option_analytics_map[key][STRIKE] = option_contract.strike
        return

    def req_15day_1hour_option_data(self, option_contract: Option):
        bars = self.ib.reqHistoricalData(option_contract, durationStr='15 D',
                                         endDateTime='',
                                         barSizeSetting='1 hour',
                                         whatToShow='TRADES',
                                         useRTH=True)
        return util.df(bars)

    def req_1day_data(self):
        stock_contract = Stock(self.symbol, 'SMART', currency='USD')
        bars = self.ib.reqHistoricalData(stock_contract,
                                         endDateTime='',
                                         durationStr='120 D',
                                         barSizeSetting='1 day',
                                         whatToShow='TRADES',
                                         useRTH=True)
        df = util.df(bars)
        return df

    def get_existing_contract_cache(self):
        return self.existing_option_analytics_map

    # For testing purpose
    def print_ticker_position(self):
        print("share count %s: " % self.share_count)
        print("option position below ** ")
        print(self.short_term_call_position)
        print("short term call options subscription list below: **")
        for st_call_contract in self.short_term_call_data_sub_list:
            print("contract subscribed to data streams: ")
            print(st_call_contract)

    @staticmethod
    def get_contract_key(input_contract):
        if isinstance(input_contract, Stock):
            return "stock_key"
        if isinstance(input_contract, Option):
            return str(int(input_contract.strike)) + "_" + input_contract.lastTradeDateOrContractMonth

    @staticmethod
    def price_adjusted(price, low_threshold, high_threshold):
        if price <= low_threshold:
            return 1.2
        if price >= high_threshold:
            return 0.9
        return 1

    @staticmethod
    def get_next_n_fridays(n):
        res_list = []
        d = date.today()
        while len(res_list) < n:
            while d.weekday() != 4:
                d += timedelta(1)
            res_list.append(d.strftime("%Y%m%d"))
            d += timedelta(1)
        return res_list
