import datetime
import threading

from datetime import datetime, date, timedelta
from ib_insync import *
# the caller might try to invoke the TradeManager many times when a trade is pending. So we need to use a lock
# to expose the status. Also this should be run as a separate thread as it will sleep during the bid/ask intervals
# The first priority is to prevent double trade


class TradeController:
    def __init__(self, bid_ask_list):
        assert len(bid_ask_list) > 0
        self.current_price = bid_ask_list[0]
        self.bid_ask_list = bid_ask_list
        self.last_trade_timestamp = None
        self.is_disabled = False

    def is_trade_disabled(self):
        return self.is_disabled

    def disable(self):
        self.is_disabled = True

    def enable(self):
        self.is_disabled = False

    def get_next_trade_price(self):
        for i in range(len(self.bid_ask_list)):
            if self.current_price == self.bid_ask_list[i]:
                if i < len(self.bid_ask_list) - 1:
                    return self.bid_ask_list[i+1]
                return self.bid_ask_list[i]
        return self.current_price

    def get_current_price(self):
        return self.current_price

    # We MUST call this function whenever a new order is submitted and confirmed by IB. Otherwise states will be lost
    def set_current_price_and_submitted_time(self, price, current_time):
        self.current_price = price
        self.last_trade_timestamp = current_time

    def should_update_bid_ask(self):
        idx = 0
        for k in range(len(self.bid_ask_list)):
            if self.bid_ask_list[k] == self.current_price:
                idx = k + 1
                break
        interval_in_seconds = TradeController.order_interval(len(self.bid_ask_list), idx)
        now_time = datetime.datetime.now()
        if (now_time - self.last_trade_timestamp).seconds >= interval_in_seconds:
            return True
        return False

    # basic intuition behind this is any order should have around 2min effective window to close.
    # That's 120 sec. We want to have faster pacing at the beginning and slower pacing as the bid/ask continue.
    @staticmethod
    def order_interval(list_size, idx):
        avg_time = 120/list_size

        # first third, bid with fastest speed. Minimum 2sec
        if idx <= list_size/3:
            return max(avg_time/3, 2)

        # last third, bid with slowest speed. Minimum 5sec
        if idx >= list_size*2/3:
            return max(5*avg_time/3, 5)

        # middle part, bid with average speed. Minimum 3sec
        return max(avg_time, 3)


class TradeManager:
    def __init__(self, ib_client: IB, to_sell=True, to_buy=True):
        self.ib = ib_client
        self.to_sell = to_sell
        self.to_buy = to_buy

        self.is_busy = False
        self.trade = None
        self.symbol = None
        self.trade_to_controller_map = {}
        self.is_busy_lock = threading.Lock()

        self.ib.connectedEvent += self.on_ib_connect
        self.ib.disconnectedEvent += self.on_ib_disconnect

    def get_is_busy_lock(self):
        return self.is_busy_lock

        # if IB is disconnected and reconnected again, need to cancel any trade that's active currently
        # because when IB is disconnected, we turn off the trade_controller, the cancellation will be once and for all
    def on_ib_connect(self):
        print("IB reconnected: Trade Manager is trying to cancel all active orders")
        if self.is_busy or self.trade is not None:
            self.ib.cancelOrder(self.trade.order)

        # disable trade_controller, so that when it reconnects, one cancellation request will terminate the
        # trade entirely
    def on_ib_disconnect(self):
        print("IB disconnected: Trade Manager is disabling all the TradeControllers")
        for key in self.trade_to_controller_map.keys():
            self.trade_to_controller_map[key].disable()
        return

    def reset(self):
        self.trade = None
        self.symbol = None
        self.trade_to_controller_map = {}
        self.is_busy = False

    def execute_trade(self, symbol, option_contract: Option, stock_ticker: Ticker, quantity, min_price, max_price):

        self.reset()
        self.symbol = symbol
        is_lock_acquired = self.is_busy_lock.acquire(blocking=False)

        if is_lock_acquired is False:
            print("Trade Manager is active. Cannot sell additional contracts")
            return

        self.is_busy = True

        can_trade = self.validate_no_pending_trade_for_contract(option_contract)
        if can_trade is False:
            self.reset()
            self.is_busy_lock.release()
            return

        key = TradeManager.get_option_trade_key(option_contract)
        # XOR. either buy or sell, not both
        assert self.to_sell ^ self.to_buy
        assert max_price - min_price >= 0
        assert symbol == option_contract.symbol

        if self.to_sell:
            price_list = TradeManager.get_ask_list(min_price, max_price)
            trade_controller = TradeController(price_list)
            self.trade_to_controller_map[key] = trade_controller
            starting_price = trade_controller.get_current_price()
            assert starting_price == price_list[0]
            limit_order = LimitOrder('SELL', quantity, starting_price)
        elif self.to_buy:
            price_list = TradeManager.get_bid_list(min_price, max_price)
            trade_controller = TradeController(price_list)
            self.trade_to_controller_map[key] = trade_controller
            starting_price = trade_controller.get_current_price()
            assert starting_price == price_list[0]
            limit_order = LimitOrder('BUY', quantity, starting_price)
        else:
            raise Exception("Either sell or buy; not both!")

        current_trade = self.ib.placeOrder(option_contract, limit_order)
        self.trade = current_trade
        stock_ticker += self.on_stock_ticker_update
        self.trade.statusEvent += self.on_trade_status_change
        self.trade.cancelledEvent += self.on_order_cancelled
        self.trade.filledEvent += self.on_order_filled

        return current_trade

    def validate_no_pending_trade_for_contract(self, option_contract: Option):
        print("validating no pending trade")
        open_trades = self.ib.openTrades()
        self.ib.sleep(1)
        expiration_date_str = option_contract.lastTradeDateOrContractMonth
        expiration_date = datetime.strptime(expiration_date_str, "%Y%m%d")
        symbol_str = option_contract.symbol
        strike_price = option_contract.strike
        # if symbol, strike price and expire date all match, then we shouldn't trade

        for open_trade in open_trades:
            if isinstance(open_trade.contract, Option):
                current_expiration_date = datetime.strptime(open_trade.contract.lastTradeDateOrContractMonth, "%Y%m%d")
                # no contract should be in pending state with the same symbol while the strike price is within $15/share difference
                if abs((current_expiration_date - expiration_date).days) <= 30 and \
                   open_trade.contract.symbol == symbol_str and abs(open_trade.contract.strike - strike_price) <= 15:
                    print("There is pending trade for this particular contract. Exit")
                    return False
        print("Contract is trade-able")
        return True

    # might need to use the stock ticker, the option ticker update is too slow
    # check the trade controller to decide whether or not to cancel the pending trade
    def on_stock_ticker_update(self, ticker_event: Ticker):
        if self.trade is None:
            return
        # now enable to pacing by calling the trade controller
        option_contract = self.trade.contract
        key = TradeManager.get_option_trade_key(option_contract)
        controller = self.trade_to_controller_map[key]
        if self.trade.orderStatus.status not in OrderStatus.DoneStates and controller.should_update_bid_ask():
            self.ib.cancelOrder(self.trade.order)

    # We are only interested in submitted event; we have cancelled callback and filled callback to handle those cases
    def on_trade_status_change(self, trade: Trade):
        if trade.orderStatus.status is not OrderStatus.Submitted:
            return

        print("** order submitted **")
        print(datetime.datetime.now())
        print(trade)
        key = TradeManager.get_option_trade_key(trade.contract)
        # Update the trade controller in order to control the bid/ask pacing
        trade_controller: TradeController = self.trade_to_controller_map[key]
        trade_controller.set_current_price_and_submitted_time(trade.order.lmtPrice, datetime.datetime.now())

    def on_order_cancelled(self, trade: Trade):
        print("** order cancelled **")
        print(datetime.datetime.now())
        print(trade)
        option_contract = trade.contract
        order_status = trade.orderStatus

        key = TradeManager.get_option_trade_key(option_contract)
        trade_controller: TradeController = self.trade_to_controller_map[key]
        # if the trade controller is disabled by ib.disconnectedEvent, any cancellation request issued
        # after ib re-connection will disable the trade manager
        if trade_controller.is_trade_disabled():
            self.reset()
            self.is_busy_lock.release()
            return

        # We exhaust the bid/ask candidate list. No more trade to be made, we need to exit
        if order_status.remaining == 0 or trade_controller.get_next_trade_price() == trade_controller.get_current_price():
            self.reset()
            self.is_busy_lock.release()
            return

        next_price = trade_controller.get_next_trade_price()
        action = trade.order.action
        limit_order = LimitOrder(action, order_status.remaining, next_price)
        self.ib.placeOrder(option_contract, limit_order)

    # For partial filled case, we don't really care. We let the caller to make decision regarding how many quantity
    # to be filled next time
    def on_order_filled(self, trade: Trade):
        assert trade.orderStatus.status in OrderStatus.Filled
        print("** order filled **")
        print(datetime.datetime.now())
        print(trade)
        self.reset()
        self.is_busy_lock.release()

    def is_trade_manager_busy(self):
        return self.is_busy

    @staticmethod
    def get_option_trade_key(option_contract: Contract):
        return option_contract.symbol + "_" + str(int(option_contract.strike)) + "_" + str(option_contract.lastTradeDateOrContractMonth)

    @staticmethod
    def get_bid_list(bid, ask):
        interval = 0.05
        if ask - bid >= 3:
            interval = 0.1
        cur_bid = bid
        bid_list = []
        while cur_bid + interval < ask:
            bid_list.append(round(cur_bid + interval, 2))
            cur_bid += interval
        assert len(bid_list) > 1 and bid_list[0] < bid_list[-1]
        return bid_list

    @staticmethod
    def get_ask_list(bid, ask):
        interval = 0.05
        if ask - bid >= 3:
            interval = 0.1
        cur_bid = bid
        bid_list = []
        while cur_bid + interval < ask:
            bid_list.append(round(cur_bid + interval, 2))
            cur_bid += interval
        ask_list = bid_list[::-1]
        assert len(ask_list) > 1 and ask_list[0] > ask_list[-1]
        return ask_list

