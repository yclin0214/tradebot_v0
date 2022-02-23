from ib_insync import *
from datetime import datetime
from src.execution.TradeManager import TradeManager
from src.coveredcalltrade.AbstractStrategy import AbstractStrategy


# setting short_term_dte_up_bound and short_term_dte_low_bound is a bit intricate if you want to
# sell two different calls with different DTE. Normally the intervals for different instance of
# this class needs to be overlapped for a bit to avoid selling more than intended
# For example, first nearest term call we want to sell at is between day1 and day30; the second
# nearest term call needs to be between day29 and day60. We do this so that we won't have any gap
# in the logic of validating the trade status
class CoveredCallOperation:
    def __init__(self, stock_symbol: str, ib_client: IB, trade_strategy: AbstractStrategy,
                 short_term_dte_up_bound, short_term_dte_low_bound):
        self.symbol = stock_symbol
        self.ib = ib_client
        # Position tracker for the symbol
        self.account_position = []
        self.share_count = 0
        self.option_positions = []
        self.short_term_call_contract = None
        self.short_term_call_position = None

        # Managing analytics
        self.short_term_dte_up_bound = short_term_dte_up_bound
        self.short_term_dte_low_bound = short_term_dte_low_bound

        # Managing trade activities
        self.trade_strategy = trade_strategy
        self.trade_manager_to_buyback_calls = TradeManager(self.ib,
                                                           short_term_dte_up_bound,
                                                           short_term_dte_low_bound,
                                                           to_sell=False,
                                                           to_buy=True)
        self.trade_manager_to_sell_calls = TradeManager(self.ib,
                                                        short_term_dte_up_bound,
                                                        short_term_dte_low_bound,
                                                        to_sell=True,
                                                        to_buy=False)

        # Managing subscription; un/subscribe to the ticker data streams
        self.stock_ticker = None
        self.short_term_call_data_sub_list = []
        self.subscribe_to_stock_data_streams()

        # Managing IB_Insync client
        # On position event important. Only release the trade lock when the position event is changed,
        # Or the trade is cancelled from the trade manager
        self.ib.disconnectedEvent += self.on_ib_disconnect
        self.ib.connectedEvent += self.on_ib_connect
        self.ib.positionEvent += self.on_position_event

    def on_ib_disconnect(self):
        self.unsubscribe_to_stock_data_streams()
        return

    def on_ib_connect(self):
        self.subscribe_to_stock_data_streams()
        return

    def on_position_event(self):
        self.refresh_ticker_positions()
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
            if self.short_term_dte_low_bound <= \
                    (expiration_date - today_date).days \
                    <= self.short_term_dte_up_bound and contract_type in ['C', 'CALL']:
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

    def unsubscribe_to_stock_data_streams(self):
        if self.stock_ticker is not None:
            self.ib.cancelMktData(self.stock_ticker.contract)
        return

    # Todo: refactor this part of the code - need to add option buying logic
    def share_price_update_callback(self, ticker_event: Ticker):
        # every ticker event tries to alert the trade_strategy object to refresh the 1min dataset
        self.trade_strategy.update_price_and_volume()
        should_trigger_call_selling = self.trade_strategy.should_trigger_call_selling()
        if should_trigger_call_selling is False:
            return
        if self.short_term_call_position is not None:
            return

        target_option_contract = self.trade_strategy.select_call_option_to_sell()
        if target_option_contract is None:
            return
        self.place_sell_order(target_option_contract, self.share_count/100)
        return

    # only sell when there's no active trade position, and the trade_manager is not busy
    def place_sell_order(self, call_contract, quantity):
        open_trades = self.ib.openTrades()
        self.ib.sleep(1)
        for open_trade in open_trades:
            if open_trade.contract.symbol == self.symbol \
                    and open_trade.orderStatus not in OrderStatus.DoneStates \
                    and isinstance(open_trade.contract, Option):
                expiration_date = datetime.strptime(open_trade.contract.lastTradeDateOrContractMonth, "%Y%m%d")
                today_date = datetime.now()
                if self.short_term_dte_low_bound <= (expiration_date - today_date).days <= self.short_term_dte_up_bound \
                        and open_trade.contract.right in ['C', "CALL"]:
                    print("There are other pending call option trades for short term; won't proceed")
                    return
        if self.trade_manager_to_sell_calls.is_trade_manager_busy():
            print("Trade manager is busy. Need to wait until trade manager finishes the work. Exit for now")
            return
        self.trade_manager_to_sell_calls.execute_trade(self.symbol, call_contract, quantity)
        return

    def place_buy_order(self, call_contract, quantity):
        open_trades = self.ib.openTrades()
        self.ib.sleep(1)
        for open_trade in open_trades:
            if open_trade.contract.symbol == self.symbol \
                    and open_trade.orderStatus not in OrderStatus.DoneStates \
                    and isinstance(open_trade.contract, Option):
                expiration_date = datetime.strptime(open_trade.contract.lastTradeDateOrContractMonth, "%Y%m%d")
                today_date = datetime.now()
                if self.short_term_dte_low_bound <= (expiration_date - today_date).days <= self.short_term_dte_up_bound \
                        and open_trade.contract.right in ['C', "CALL"]:
                    print("There are other pending call option trades for short term; won't proceed")
                    return
        if self.trade_manager_to_buyback_calls.is_trade_manager_busy():
            print("Trade manager is busy. Need to wait until trade manager finishes the work. Exit for now")
            return
        self.trade_manager_to_buyback_calls.execute_trade(self.symbol, call_contract, quantity)
        return

    # For testing purpose
    def print_ticker_position(self):
        print("share count %s: " % self.share_count)
        print("option position below ** ")
        print(self.short_term_call_position)
        print("short term call options subscription list below: **")
        for st_call_contract in self.short_term_call_data_sub_list:
            print("contract subscribed to data streams: ")
            print(st_call_contract)

