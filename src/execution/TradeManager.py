import datetime
import random
import threading

from datetime import datetime, date, timedelta
from ib_insync import *
# the caller might try to invoke the TradeManager many times when a trade is pending. So we need to use a lock
# to expose the status. Also this should be run as a separate thread as it will sleep during the bid/ask intervals
# The first priority is to prevent double trade


class TradeManager:
    def __init__(self, ib_client: IB, days_to_expiration_up_bound, days_to_expiration_low_bound, to_sell=True, to_buy=True):
        self.ib = ib_client
        self.to_sell = to_sell
        self.to_buy = to_buy
        self.dte_up_bound = days_to_expiration_up_bound
        self.dte_low_bound = days_to_expiration_low_bound

        self.is_busy = False
        self.option_ticker = None
        self.trade = None
        self.symbol = None
        self.quantity = 0

        self.is_busy_lock = threading.Lock()

        self.ib.connectedEvent += self.on_ib_connect
        self.ib.disconnectedEvent += self.on_ib_disconnect

        self.last_bid_ask_timestamp = None
        self.trade_start_timestamp = None

    def get_is_busy_lock(self):
        return self.is_busy_lock

    # if IB is disconnected and reconnected again, need to cancel any trade that's active currently
    def on_ib_connect(self):
        print("IB reconnected: Trade Manager is trying to cancel all active orders")
        if self.is_busy or self.trade is not None:
            self.ib.cancelOrder(self.trade.order)

    def on_ib_disconnect(self):
        print("IB disconnected: Trade Manager is disabling all the TradeControllers")
        if self.option_ticker is not None:
            self.ib.cancelMktData(self.option_ticker.contract)
        return

    def reset(self):
        self.trade = None
        self.option_ticker = None
        self.symbol = None
        self.is_busy = False
        self.quantity = 0
        self.last_bid_ask_timestamp = None
        self.trade_start_timestamp = None

    def execute_trade(self, symbol, option_contract: Option, quantity):

        self.reset()
        self.symbol = symbol
        is_lock_acquired = self.is_busy_lock.acquire(blocking=False)

        if is_lock_acquired is False:
            print("Trade Manager is active. Cannot sell additional contracts")
            return

        self.is_busy = True
        self.quantity = quantity

        can_trade = self.validate_no_pending_trade_for_contract(option_contract)
        if can_trade is False:
            self.reset()
            self.is_busy_lock.release()
            return

        # XOR. either buy or sell, not both
        assert self.to_sell ^ self.to_buy
        assert symbol == option_contract.symbol
        assert self.quantity > 0

        contract_ticker = self.ib.reqMktData(option_contract)

        # active trade and bidding adjustment is through each option ticker update
        contract_ticker.updateEvent += self.on_option_ticker_update

        return

    # all the bidding/asking logic happens here, with timer control
    def on_option_ticker_update(self, option_ticker: Ticker):
        bid = option_ticker.bid
        ask = option_ticker.ask
        option_contract = option_ticker.contract
        current_time = datetime.now()
        if self.trade is None and self.trade_start_timestamp is None and self.last_bid_ask_timestamp is None:
            if self.to_sell:
                if ask - bid <= 0.4:
                    my_initial_ask = ask - 0.05
                else:
                    my_initial_ask = ask - 0.1
                limit_order = LimitOrder('SELL', self.quantity, my_initial_ask)
                self.trade: Trade = self.ib.placeOrder(option_contract, limit_order)
                self.last_bid_ask_timestamp = current_time
                self.trade_start_timestamp = current_time

        elif self.trade is not None and self.trade_start_timestamp is not None and \
                self.last_bid_ask_timestamp is not None:
            # if larger than 200 secs, cancel the order
            time_since_trade_start = current_time - self.trade_start_timestamp
            time_since_last_trade = current_time - self.last_bid_ask_timestamp
            # Still in transition stage, so not doing anything
            if self.trade.orderStatus != OrderStatus.Submitted:
                return
            if time_since_trade_start.seconds >= 180: # more than 3 minutes. we should cancel the trade
                self.trade = self.ib.cancelOrder(self.trade.order)
                self.trade.cancelledEvent += self.on_trade_status_change
                return
            if time_since_last_trade.seconds < 5:  # less than 5 seconds, no action
                return
            # Now we start to compete, when the last trade is 5 sec ago
            current_order: Order = self.trade.order
            current_limit_price = current_order.lmtPrice
            min_price = round((bid + ask)/2, 2) - 0.1
            # bidding logic
            if self.to_sell:
                random_init = random.randint(1, 10)
                if current_limit_price == ask:
                    if random_init <= 3:  # 3/10 chance to drop ask by 0.1 usd
                        updated_limit_price = max(ask - 0.1, min_price)
                    elif random_init <= 6:  # 3/10 chance to drop ask by 0.05 usd
                        updated_limit_price = max(ask - 0.05, min_price)
                    elif random_init == 7:  # 1/10 chance to increase ask by 0.2
                        updated_limit_price = max(ask + 0.2, min_price)
                    elif random_init == 8:  # 1/10 chance to increase ask by 0.1
                        updated_limit_price = max(ask + 0.1, min_price)
                    else:  # 2/10 chance to stay the same
                        updated_limit_price = ask
                    current_order.lmtPrice = updated_limit_price
                    self.trade = self.ib.placeOrder(option_contract, current_order)
                    self.last_bid_ask_timestamp = datetime.now()
                else:
                    if random_init <= 4:
                        updated_limit_price = max(ask - 0.15, min_price)
                    elif random_init <= 9:
                        updated_limit_price = max(ask - 0.1, min_price)
                    else:
                        updated_limit_price = max(ask - 0.05, min_price)
                    current_order.lmtPrice = updated_limit_price
                    self.trade = self.ib.placeOrder(option_contract, current_order)
                    self.last_bid_ask_timestamp = datetime.now()

                self.trade.cancelledEvent += self.on_trade_status_change
                self.trade.filledEvent += self.on_trade_status_change

            # Todo: to implemnt self.to_buy case
            return

        else:
            raise Exception("Unknown status in TradeManager")

    def validate_no_pending_trade_for_contract(self, option_contract: Option):
        print("validating no pending trade")
        open_trades = self.ib.openTrades()
        self.ib.sleep(1)
        expiration_date_str = option_contract.lastTradeDateOrContractMonth
        expiration_date = datetime.strptime(expiration_date_str, "%Y%m%d")
        symbol_str = option_contract.symbol
        # if symbol, strike price and expire date all match, then we shouldn't trade

        for open_trade in open_trades:
            if isinstance(open_trade.contract, Option):
                current_expiration_date = datetime.strptime(open_trade.contract.lastTradeDateOrContractMonth, "%Y%m%d")
                # no contract should be in pending state with the same symbol
                if self.dte_low_bound <= abs((current_expiration_date - expiration_date).days) <= self.dte_up_bound and \
                   open_trade.contract.symbol == symbol_str:
                    print("There is pending trade for this particular contract. Exit")
                    return False
        print("Contract is trade-able")
        return True

    # We are only interested in submitted event; we have cancelled callback and filled callback to handle those cases
    def on_trade_status_change(self, trade: Trade):
        # Cancelled or change
        if trade.orderStatus.status in OrderStatus.DoneStates:
            self.reset()
            self.is_busy_lock.release()
        return

    def is_trade_manager_busy(self):
        return self.is_busy

