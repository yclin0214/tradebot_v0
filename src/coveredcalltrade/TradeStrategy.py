from abc import ABC, abstractmethod


class TradeStrategy(ABC):
    def __init__(self, name):
        self.symbol = name
        self.stock_1day_df = None
        self.active = False

    def enable(self):
        self.active = True

    def is_operational(self):
        return self.active

    def get_symbol_name(self):
        return self.symbol

    def set_stock_1day_df(self, stock_1day_df):
        self.stock_1day_df = stock_1day_df
        return

    @abstractmethod
    def should_trigger_call_selling(self):
        pass

    @abstractmethod
    def should_trigger_call_buying(self):
        pass

    @abstractmethod
    def get_call_candidates(self):
        pass



