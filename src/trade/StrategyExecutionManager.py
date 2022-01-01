import TradeActivityManager, BidAskManager, StrategyLoader, AccountPositionManager


# This class needs to load a strategy config file
# Todo: add strategy config fetcher
class StrategyExecutionManager:
    def __init__(self,
                 strategy_loader: StrategyLoader,
                 trade_activity_manager: TradeActivityManager,
                 bid_ask_manager: BidAskManager,
                 account_position_manager: AccountPositionManager):
        self.trade_activity_manager = trade_activity_manager
        self.bid_ask_manager = bid_ask_manager
        self.strategy_loader = strategy_loader
        self.strategy_config = {}  # this should be initialized to some value
        self.account_position_manager = account_position_manager
        self.strategy_config = self.load_strategy_config()
        return

    # Todo: load strategy from some kind of config file with a config fetcher
    def load_strategy_config(self):
        latest_strategy_config = {}
        return latest_strategy_config

    def refresh_strategy_config(self):
        refreshed_strategy_config = {}
        if len(refreshed_strategy_config) > 0:
            self.strategy_config = refreshed_strategy_config
        return

    def strategize_tickers(self, tickers):

        pass
