from src.trade import TradeActivityManager, BidAskManager, AccountPositionManager, StrategyExecutionManager
from ib_insync import *


# Note that it is not advisable to place new requests inside an event handler as it may lead to too much recursion.
class PubSubManager:
    def __init__(self, bid_manager: BidAskManager,
                 trade_activity_manager: TradeActivityManager,
                 strategy_execution_manager: StrategyExecutionManager,
                 account_position_manager: AccountPositionManager):
        self.bid_manager = bid_manager
        self.trade_activity_manager = trade_activity_manager
        self.strategy_execution_manager = strategy_execution_manager
        self.account_position_manager = account_position_manager
        self.latest_stock_price_map = {} # store the latest ticker price locally
        return

    # Todo: to add connect and disconnect callback handlers
    # Todo: account position manager manages the state of the account; any order that impacts
    # the account position need to be synced with the account manager. The reason is that
    # some strategies should only be accepted if the position of a ticker doesn't have infinite loss
    # potential

    # In this function, there are 3 types of states we need to be synced with
    # 1. the account position state - ticker position and calibrated margin used
    # 2. Open orders state
    # 3. Static strategy config file - loaded locally
    def ib_client_connected_handler(self):
        self.account_position_manager.request_current_account_position()
        # Todo: might need to load db and read the db data into trade_activity_manager
        self.trade_activity_manager.load_open_trades()
        # Todo: to decide how to load this file/config
        self.strategy_execution_manager.load_strategy_config()
        # Todo: initialize a logger
        return

    def ib_client_disconnected_handler(self):
        # Todo: add logger
        # Todo: what else?
        pass

    # Todo: this is a crucial function to implement - it needs to read the data, check the current
    # order status, check the strategy configurations and eventually decide what to do
    def pending_tickers_handler(self, tickers):
        self.strategy_execution_manager.strategize_tickers(tickers)
        return

    def bar_update_handlers(self, bars):
        pass

    # For IB callback - openOrderEvent
    def open_order_handler(self, trade: Trade):
        self.trade_activity_manager.add_open_trade(trade)
        return

    def order_status_handler(self, trade: Trade):
        self.trade_activity_manager.check_order_update_status(trade)
        return

    # Todo: what's the difference between new_order and open_order?
    def new_order_handler(self, trade: Trade):
        self.trade_activity_manager.add_open_trade(trade)
        return

    # For position event
    def position_change_handler(self):
        self.account_position_manager.request_current_account_position()
        return

    # There are multiple ways to handle this. For now we can implement a simple write mechanism
    def ticker_news_handler(self, news):
        pass

    def new_bulletin_handler(self, bulletin):
        pass

    def timeout_handler(self):
        pass

    def error_msg_handler(self, reqId: int, errorCode: int, errorString: str, contract: Contract):
        pass
