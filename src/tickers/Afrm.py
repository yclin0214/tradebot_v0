import threading

from ib_insync import *
from datetime import datetime, date, timedelta
from TradeManager import TradeManager

# On start-up, scan the account positions related to this ticker; register callback to handle event accordingly
# data_stream -> callback -> buy_sell_decision -> trade_event -> trade_event_callback
class Afrm:
    def __init__(self, ib_client: IB, short_term_dte=30, long_term_dte=360):
        self.symbol = 'AFRM'
        self.ib = ib_client
        # Todo: subscribe to the stock data streams and option streams and account position
        self.account_position = []
        self.share_count = 0
        self.option_positions = []
        self.lt_call_contract = None
        self.st_call_contract = None
        self.lt_call_position = None
        self.st_call_position = None

        self.stock_ticker = None

        self.short_term_dte_limit = short_term_dte  # need to be less than a month
        self.long_term_dte_limit = long_term_dte  # need to be more than a year
        self.existing_contract_cache_map = {}
        self.potential_contract_cache_map = {}
        self.volume_price_multiplier_list = []

        self.st_call_trade_lock = threading.Lock()
        self.lt_call_trade_lock = threading.Lock()
        self.trade_manager_existing_st_call = TradeManager(self.ib,  to_sell=False, to_buy=True)
        self.trade_manager_existing_lt_call = TradeManager(self.ib,  to_sell=False, to_buy=True)
        self.trade_manager_candidate_st_call = TradeManager(self.ib, to_sell=True, to_buy=False)
        self.trade_manager_candidate_lt_call = TradeManager(self.ib, to_sell=True, to_buy=False)

        self.st_call_mkt_data_sub_list = []
        self.lt_call_mkt_data_sub_list = []

        self.subscribe_to_stock_data_streams()
        self.subscribe_to_option_data_streams()

        self.ib.disconnectedEvent += self.on_ib_disconnect
        self.ib.connectedEvent += self.on_ib_connect
        self.ib.positionEvent += self.on_position_event

    def on_ib_disconnect(self):
        self.unsub_all_mkt_data()
        return

    def on_ib_connect(self):
        self.subscribe_to_stock_data_streams()
        self.subscribe_to_option_data_streams()
        return

    def on_position_event(self):
        self.subscribe_to_option_data_streams()
        return

    def refresh_ticker_positions(self):
        positions = self.ib.positions()
        for position in positions:
            current_contract = position.contract
            if isinstance(current_contract, Stock) and current_contract.symbol == self.symbol:
                self.share_count = position.position
            elif isinstance(current_contract, Option) and current_contract.symbol == self.symbol:
                self.option_positions.append(position)
        self.short_term_call_position()
        self.long_term_call_position()

        return

    def long_term_call_position(self):
        for position in self.option_positions:
            expiration_date_str = position.contract.lastTradeDateOrContractMonth
            expiration_date = datetime.strptime(expiration_date_str, "%Y%m%d")
            today_date = datetime.now()
            if (expiration_date - today_date).days >= self.long_term_dte_limit:
                self.lt_call_position = position
                self.lt_call_contract = position.contract
                self.lt_call_contract.exchange = 'SMART'
                return
        return

    def short_term_call_position(self):
        for position in self.option_positions:
            expiration_date_str = position.contract.lastTradeDateOrContractMonth
            expiration_date = datetime.strptime(expiration_date_str, "%Y%m%d")
            today_date = datetime.now()
            if (expiration_date - today_date).days <= self.short_term_dte_limit:
                self.st_call_position = position
                self.st_call_contract = position.contract
                self.st_call_contract.exchange = "SMART"
                return
        return

    def subscribe_to_stock_data_streams(self):
        stk_contract = Stock(self.symbol, "SMART", currency="USD")
        self.stock_ticker = self.ib.reqMktData(stk_contract)
        self.stock_ticker.updateEvent += self.share_price_update_cb
        return

    def subscribe_to_option_data_streams(self):
        # Reset subscription
        self.unsub_all_lt_call_mkt_data()
        self.unsub_all_st_call_mkt_data()
        self.refresh_ticker_positions()
        # For now, for partially filled case, we want to fully fill first before buying them back
        if self.lt_call_position is not None and self.lt_call_position.position * 100 + self.share_count == 0:
            print("Found long term call position")
            lt_ticker = self.ib.reqMktData(self.lt_call_contract)
            lt_ticker.updateEvent += self.lt_existing_call_cb
            self.lt_call_mkt_data_sub_list.append(self.lt_call_contract)
        elif self.lt_call_position is None or self.lt_call_position.position * 100 + self.share_count > 0:
            # subscribe to candidate stream positions
            print("No long term short call position")
            lt_call_contracts = self.get_lt_call_candidate()
            print(lt_call_contracts)
            for lt_call_contract in lt_call_contracts:
                lt_ticker = self.ib.reqMktData(lt_call_contract)
                lt_ticker.updateEvent += self.lt_candidate_call_cb
                self.lt_call_mkt_data_sub_list.append(lt_call_contract)
        if self.st_call_position is not None and self.st_call_position.position * 100 + self.share_count == 0:
            print("Found short term short call position")
            st_ticker = self.ib.reqMktData(self.st_call_contract)
            st_ticker.updateEvent += self.st_existing_call_cb
            self.st_call_mkt_data_sub_list.append(self.st_call_contract)
        elif self.st_call_position is None or self.st_call_position.position * 100 + self.share_count > 0:
            # subscribe to candidate stream positions
            print("No short term short call position")
            st_call_contracts = self.get_st_call_candidate(Afrm.get_next_n_fridays(4))
            for st_call_contract in st_call_contracts:
                st_ticker = self.ib.reqMktData(st_call_contract)
                st_ticker.updateEvent += self.st_candidate_call_cb
                self.st_call_mkt_data_sub_list.append(st_call_contract)
        return

    def unsub_all_st_call_mkt_data(self):
        for st_contract in self.st_call_mkt_data_sub_list:
            self.ib.cancelMktData(st_contract)
        self.st_call_mkt_data_sub_list = []
        return

    def unsub_all_lt_call_mkt_data(self):
        for lt_contract in self.lt_call_mkt_data_sub_list:
            self.ib.cancelMktData(lt_contract)
        self.lt_call_mkt_data_sub_list = []
        return

    def unsub_all_mkt_data(self):
        self.unsub_all_st_call_mkt_data()
        self.unsub_all_lt_call_mkt_data()
        stk_contract = Stock(self.symbol, "SMART", currency="USD")
        self.ib.cancelMktData(stk_contract)
        return

    def lt_existing_call_cb(self, ticker_event: Ticker):
        option_contract = ticker_event.contract
        ask = ticker_event.ask
        bid = ticker_event.bid

        key = Afrm.get_contract_key(option_contract)
        if key not in self.existing_contract_cache_map:
            self.existing_contract_cache_map[key] = []

        self.existing_contract_cache_map[key].append((ask + bid) / 2)

        print("long-term cost basis: " + str(self.lt_call_position.avgCost))

        return

    def lt_candidate_call_cb(self, ticker_event: Ticker):
        option_contract = ticker_event.contract
        ask = ticker_event.ask
        bid = ticker_event.bid

        key = Afrm.get_contract_key(option_contract)

        self.potential_contract_cache_map[key].append((ask + bid) / 2)
        return

    def st_candidate_call_cb(self, ticker_event: Ticker):
        option_contract = ticker_event.contract
        ask = ticker_event.ask
        bid = ticker_event.bid

        key = Afrm.get_contract_key(option_contract)
        if key not in self.potential_contract_cache_map:
            self.existing_contract_cache_map[key] = []

        self.potential_contract_cache_map[key].append((ask + bid) / 2)
        return

    def st_existing_call_cb(self, ticker_event: Ticker):
        option_contract = ticker_event.contract
        ask = ticker_event.ask
        bid = ticker_event.bid

        key = Afrm.get_contract_key(option_contract)
        if key not in self.existing_contract_cache_map:
            self.existing_contract_cache_map[key] = []

        self.existing_contract_cache_map[key].append((ask + bid) / 2)
        return

    def share_price_update_cb(self, ticker_event: Ticker):
        stock_contract = ticker_event.contract
        ask = ticker_event.ask
        bid = ticker_event.bid

        key = Afrm.get_contract_key(stock_contract)
        if key not in self.existing_contract_cache_map:
            self.existing_contract_cache_map[key] = []

        self.existing_contract_cache_map[key].append((ask + bid) / 2)
        return

    def place_sell_order_for_st_call(self, call_contract, quantity, current_ask, minimum_ask):
        open_trades = self.ib.openTrades()
        self.ib.sleep(1)
        for open_trade in open_trades:
            if open_trade.contract.symbol == self.symbol and open_trade.orderStatus not in OrderStatus.DoneStates and isinstance(open_trade.contract, Option):
                expiration_date = datetime.strptime(open_trade.contract.lastTradeDateOrContractMonth, "%Y%m%d")
                today_date = datetime.now()
                if (expiration_date - today_date).days <= self.short_term_dte_limit:
                    print("There are other pending trades for short term call; won't proceed")
                    return
        if self.trade_manager_candidate_st_call.is_trade_manager_busy():
            return
        self.trade_manager_candidate_st_call.execute_trade(self.symbol, call_contract, self.stock_ticker, quantity, minimum_ask, current_ask)

    def place_sell_order_for_lt_call(self, call_contract, quantity, current_ask, minimum_ask):
        open_trades = self.ib.openTrades()
        self.ib.sleep(1)
        for open_trade in open_trades:
            if open_trade.contract.symbol == self.symbol and open_trade.orderStatus not in OrderStatus.DoneStates and isinstance(open_trade.contract, Option):
                expiration_date = datetime.strptime(open_trade.contract.lastTradeDateOrContractMonth, "%Y%m%d")
                today_date = datetime.now()
                if (expiration_date - today_date).days >= self.long_term_dte_limit/2:
                    print("There are other pending trades for long term call; won't proceed")
                    return
        if self.trade_manager_candidate_lt_call.is_trade_manager_busy():
            return
        self.trade_manager_candidate_lt_call.execute_trade(self.symbol, call_contract, self.stock_ticker, quantity, minimum_ask, current_ask)

    def place_buy_order_for_st_call(self, call_contract, quantity, maximum_bid, current_bid):
        open_trades = self.ib.openTrades()
        self.ib.sleep(1)
        for open_trade in open_trades:
            if open_trade.contract.symbol == self.symbol and open_trade.orderStatus not in OrderStatus.DoneStates and isinstance(open_trade.contract, Option):
                expiration_date = datetime.strptime(open_trade.contract.lastTradeDateOrContractMonth, "%Y%m%d")
                today_date = datetime.now()
                if (expiration_date - today_date).days <= self.short_term_dte_limit:
                    print("There are other pending trades for short term call; won't proceed")
                    return
        if self.trade_manager_existing_st_call.is_trade_manager_busy():
            return
        self.trade_manager_existing_st_call.execute_trade(self.symbol, call_contract, self.stock_ticker, quantity, current_bid, maximum_bid)

    def place_buy_order_for_lt_call(self, call_contract, quantity, maximum_bid, current_bid):
        open_trades = self.ib.openTrades()
        self.ib.sleep(1)
        for open_trade in open_trades:
            if open_trade.contract.symbol == self.symbol and open_trade.orderStatus not in OrderStatus.DoneStates and isinstance(open_trade.contract, Option):
                expiration_date = datetime.strptime(open_trade.contract.lastTradeDateOrContractMonth, "%Y%m%d")
                today_date = datetime.now()
                if (expiration_date - today_date).days >= self.long_term_dte_limit/2:
                    print("There are other pending trades for short term call; won't proceed")
                    return
        if self.trade_manager_existing_lt_call.is_trade_manager_busy():
            return
        self.trade_manager_existing_lt_call.execute_trade(self.symbol, call_contract, self.stock_ticker, quantity, current_bid, maximum_bid)

    def get_lt_call_candidate(self):
        # Todo: to add delta metrics to it. For now we hardcode the price target
        # Todo: we also hard code the date
        lt_target_price_list = [90, 95, 100, 105, 110, 120, 125]
        lt_contracts = [Option(symbol=self.symbol,
                               lastTradeDateOrContractMonth='20240119',
                               strike=strike,
                               right='C',
                               exchange='SMART',
                               currency="USD") for strike in lt_target_price_list]

        for lt_contract in lt_contracts:
            key = Afrm.get_contract_key(lt_contract)
            self.potential_contract_cache_map[key] = []

        return lt_contracts

    def get_st_call_candidate(self, date_str_list):
        # to return a list of short term call contract
        df = self.req_1day_data()
        price_list = df["close"].values.tolist()
        adaptive_pred = [0] * len(price_list)
        for i in range(40, len(price_list)):
            if price_list[i] >= price_list[i - 40] * 1.35:
                adaptive_pred[i] = 1.05 * price_list[i]
            elif price_list[i] >= price_list[i - 10] * 1.15:
                adaptive_pred[i] = 1.1 * price_list[i]
            else:
                adaptive_pred[i] = 1.15 * price_list[i]

        potential_strike_price_list = [int(adaptive_pred[-1]/5) * 5 + k*5 for k in range(3)]

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
            key = Afrm.get_contract_key(st_contract)
            self.potential_contract_cache_map[key] = []

        return st_contracts

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

    def get_potential_contract_cache(self):
        return self.potential_contract_cache_map

    def get_existing_contract_cache(self):
        return self.existing_contract_cache_map

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
