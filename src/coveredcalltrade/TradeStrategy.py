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
    def sell_call_trigger_condition(self, stock_price, stock_volume, option_data, option_contract):
        return False

    @abstractmethod
    def buy_call_trigger_condition(self, stock_price, stock_volume, option_data, option_contract):
        return False

