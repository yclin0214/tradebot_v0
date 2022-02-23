from abc import ABC, abstractmethod


class AbstractStrategy(ABC):
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
    def update_price_and_volume(self):
        pass

    @abstractmethod
    def should_trigger_call_selling(self):
        pass

    @abstractmethod
    def should_trigger_call_closing(self, option_contract):
        pass

    @abstractmethod
    def select_call_option_to_sell(self):
        pass



