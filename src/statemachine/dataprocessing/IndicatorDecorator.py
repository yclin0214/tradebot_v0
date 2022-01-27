from ta.trend import *
from ta.volume import *
from ta.volatility import *
from ta.momentum import *
import pandas as pd


class DatasetResolutions:
    ONE_MIN = "one_min"
    FIVE_MIN = "five_min"
    THIRTY_MIN = "thirty_min"
    ONE_HOUR = "one_hour"
    ONE_DAY = "one_day"
    ONE_WEEK = "one_week"


class Columns:
    DATE = "date"
    OPEN = "open"
    CLOSE = "close"
    HIGH = "high"
    LOW = "low"
    VOLUME = "volume"
    AVG = "average"
    # 5 min resolution
    FIVE_MIN_OPEN = "5min_open"
    FIVE_MIN_CLOSE = "5min_close"
    FIVE_MIN_HIGH = "5min_high"
    FIVE_MIN_LOW = "5min_low"
    FIVE_MIN_VOLUME = "5min_volume"
    FIVE_MIN_AVG = "5min_average"
    # 1 hour resolution
    ONE_HOUR_OPEN = "1hour_open"
    ONE_HOUR_CLOSE = "1hour_close"
    ONE_HOUR_HIGH = "1hour_high"
    ONE_HOUR_LOW = "1hour_low"
    ONE_HOUR_VOLUME = "1hour_volume"
    ONE_HOUR_AVG = "1hour_average"
    # 1 day resolution
    ONE_DAY_OPEN = "1day_open"
    ONE_DAY_CLOSE = "1day_close"
    ONE_DAY_HIGH = "1day_high"
    ONE_DAY_LOW = "1day_low"
    ONE_DAY_VOLUME = "1day_volume"
    ONE_DAY_AVG = "1day_average"


# dataset should be pre-processed already
class IndicatorDecorator:

    @staticmethod
    def decorate_1day_resolution_df(df, bb_config_map=None, window_config_map=None):
        if window_config_map is None:
            kl_config_map = dc_config_map = mfi_config_map = rsi_config_map = ema_config_map = \
                {"1day": [{"window": 3}, {"window": 5}, {"window": 10}, {"window": 15}]}
        else:
            kl_config_map = dc_config_map = mfi_config_map = rsi_config_map = ema_config_map = window_config_map
        if bb_config_map is None:
            bb_config_map = {
                "1day": [{"window": 3, "window_dev": 2}, {"window": 5, "window_dev": 2},
                         {"window": 10, "window_dev": 2},
                         {"window": 15, "window_dev": 2}]}

        resolution = "1day"
        df_0 = IndicatorDecorator.add_bollinger(df, resolution, bb_config_map)
        df_1 = IndicatorDecorator.add_ema(df_0, resolution, ema_config_map)
        df_2 = IndicatorDecorator.add_rsi(df_1, resolution, rsi_config_map)
        df_3 = IndicatorDecorator.add_moneyflow(df_2, resolution, mfi_config_map)
        df_4 = IndicatorDecorator.add_donchian(df_3, resolution, dc_config_map)
        df_5 = IndicatorDecorator.add_keltner(df_4, resolution, kl_config_map)
        df_6 = IndicatorDecorator.add_volume_ema(df_5, resolution, ema_config_map)
        return df_6

    @staticmethod
    def decorate_1hour_resolution_df(df, bb_config_map=None, window_config_map=None):
        if window_config_map is None:
            kl_config_map = dc_config_map = mfi_config_map = rsi_config_map = ema_config_map = {
                "1hour": [{"window": 3}, {"window": 6}, {"window": 12}, {"window": 24}]}
        else:
            kl_config_map = dc_config_map = mfi_config_map = rsi_config_map = ema_config_map = window_config_map
        if bb_config_map is None:
            bb_config_map = {
                "1hour": [{"window": 3, "window_dev": 2},
                          {"window": 6, "window_dev": 2},
                          {"window": 12, "window_dev": 2},
                          {"window": 24, "window_dev": 2}]}

        resolution = "1hour"
        df_0 = IndicatorDecorator.add_bollinger(df, resolution, bb_config_map)
        df_1 = IndicatorDecorator.add_ema(df_0, resolution, ema_config_map)
        df_2 = IndicatorDecorator.add_rsi(df_1, resolution, rsi_config_map)
        df_3 = IndicatorDecorator.add_moneyflow(df_2, resolution, mfi_config_map)
        df_4 = IndicatorDecorator.add_donchian(df_3, resolution, dc_config_map)
        df_5 = IndicatorDecorator.add_keltner(df_4, resolution, kl_config_map)
        df_6 = IndicatorDecorator.add_volume_ema(df_5, resolution, ema_config_map)
        return df_6

    @staticmethod
    def decorate_5min_resolution_df(df, bb_config_map=None, window_config_map=None):
        if window_config_map is None:
            kl_config_map = dc_config_map = mfi_config_map = rsi_config_map = ema_config_map = {
                "5min": [{"window": 3}, {"window": 6}, {"window": 12}, {"window": 24}]}
        else:
            kl_config_map = dc_config_map = mfi_config_map = rsi_config_map = ema_config_map = window_config_map
        if bb_config_map is None:
            bb_config_map = {
                "5min": [{"window": 3, "window_dev": 2},
                         {"window": 6, "window_dev": 2},
                         {"window": 12, "window_dev": 2},
                         {"window": 24, "window_dev": 2}]}

        resolution = "5min"
        df_0 = IndicatorDecorator.add_bollinger(df, resolution, bb_config_map)
        df_1 = IndicatorDecorator.add_ema(df_0, resolution, ema_config_map)
        df_2 = IndicatorDecorator.add_rsi(df_1, resolution, rsi_config_map)
        df_3 = IndicatorDecorator.add_moneyflow(df_2, resolution, mfi_config_map)
        df_4 = IndicatorDecorator.add_donchian(df_3, resolution, dc_config_map)
        df_5 = IndicatorDecorator.add_keltner(df_4, resolution, kl_config_map)
        df_6 = IndicatorDecorator.add_volume_ema(df_5, resolution, ema_config_map)
        return df_6

    @staticmethod
    def decorate_and_merge(df_5min, df_1hour, df_1day):
        rn_1day_df = df_1day.rename(columns={"open": "1day_open", "high": "1day_high", "low": "1day_low",
                                             "close": "1day_close", "volume": "1day_volume", "average": "1day_average"})

        rn_1hour_df = df_1hour.rename(columns={"open": "1hour_open", "high": "1hour_high", "low": "1hour_low",
                                               "close": "1hour_close", "volume": "1hour_volume",
                                               "average": "1hour_average"})

        rn_5min_df = df_5min.rename(columns={"open": "5min_open", "high": "5min_high", "low": "5min_low",
                                             "close": "5min_close", "volume": "5min_volume", "average": "5min_average"})
        df_1day_decorated = IndicatorDecorator.decorate_1day_resolution_df(rn_1day_df)
        df_1hour_decorated = IndicatorDecorator.decorate_1hour_resolution_df(rn_1hour_df)
        df_5min_decorated = IndicatorDecorator.decorate_5min_resolution_df(rn_5min_df)

        df_1hour_merged = IndicatorDecorator.merge_two_df_based_on_date(df_1hour_decorated, df_1day_decorated)
        df_5min_merged = IndicatorDecorator.merge_two_df_based_on_date(df_5min_decorated, df_1hour_merged)

        return df_5min_merged

    @staticmethod
    def round_to_decimal(input_val, decimal=3):
        return round(input_val, decimal)

    # {"1hour": [{"window": 24, "window_dev": 2}, {"window": 16, "window_dev": 2}, {"window": 8, "window_dev": 2}]}
    @staticmethod
    def add_bollinger(df, resolution, indicator_config_map):
        indicator_configs = indicator_config_map.get(resolution, [])

        for indicator_config in indicator_configs:
            # config
            window = indicator_config.get("window")
            window_dev = indicator_config.get("window_dev")
            # column names
            current_close = IndicatorDecorator.close(resolution)
            bb_high = IndicatorDecorator.bollinger_high(resolution, str(window), str(window_dev))
            bb_low = IndicatorDecorator.bollinger_low(resolution, str(window), str(window_dev))

            # indicator instantiation
            indicator = BollingerBands(close=df[current_close],
                                       window=window,
                                       window_dev=window_dev)
            df[bb_high] = IndicatorDecorator.round_to_decimal(indicator.bollinger_hband())
            df[bb_low] = IndicatorDecorator.round_to_decimal(indicator.bollinger_lband())

        return df

    # {"1hour": [{"window": 8}, {"window": 16}, {"window": 24}]}
    @staticmethod
    def add_ema(df, resolution, indicator_config_map):
        indicator_configs = indicator_config_map.get(resolution, [])
        for indicator_config in indicator_configs:
            window = indicator_config.get("window")
            # column names
            current_close = IndicatorDecorator.close(resolution)
            ema = IndicatorDecorator.ema(resolution, str(window))
            indicator = EMAIndicator(close=df[current_close], window=window)
            df[ema] = IndicatorDecorator.round_to_decimal(indicator.ema_indicator())
        return df

    # volume ema helps to create some stateful comparison between current volume and historical volume
    @staticmethod
    def add_volume_ema(df, resolution, indicator_config_map):
        indicator_configs = indicator_config_map.get(resolution, [])
        for indicator_config in indicator_configs:
            window = indicator_config.get("window")
            # column names
            current_volume = IndicatorDecorator.volume(resolution)
            ema = IndicatorDecorator.volume_ema(resolution, str(window))
            indicator = EMAIndicator(close=df[current_volume], window=window)
            df[ema] = IndicatorDecorator.round_to_decimal(indicator.ema_indicator())
        return df

    @staticmethod
    def add_rsi(df, resolution, indicator_config_map):
        indicator_configs = indicator_config_map.get(resolution, [])
        for indicator_config in indicator_configs:
            window = indicator_config.get("window")
            # column names
            current_close = IndicatorDecorator.close(resolution)
            rsi_val = IndicatorDecorator.rsi(resolution, str(window))
            indicator = RSIIndicator(close=df[current_close], window=window)
            df[rsi_val] = IndicatorDecorator.round_to_decimal(indicator.rsi())
        return df

    @staticmethod
    def add_tsi(df, resolution, indicator_config_map):
        pass

    @staticmethod
    def add_moneyflow(df, resolution, indicator_config_map):
        indicator_configs = indicator_config_map.get(resolution, [])
        for indicator_config in indicator_configs:
            window = indicator_config.get("window")
            # column names
            current_high = IndicatorDecorator.high(resolution)
            current_low = IndicatorDecorator.low(resolution)
            current_close = IndicatorDecorator.close(resolution)
            current_volume = IndicatorDecorator.volume(resolution)
            mfi = IndicatorDecorator.mfi(resolution, str(window))

            indicator = MFIIndicator(high=df[current_high],
                                     low=df[current_low],
                                     close=df[current_close],
                                     volume=df[current_volume],
                                     window=window
                                     )
            df[mfi] = IndicatorDecorator.round_to_decimal(indicator.money_flow_index())
        return df

    @staticmethod
    def add_donchian(df, resolution, indicator_config_map):
        indicator_configs = indicator_config_map.get(resolution, [])
        for indicator_config in indicator_configs:
            window = indicator_config.get("window")
            # column names
            current_high = IndicatorDecorator.high(resolution)
            current_low = IndicatorDecorator.low(resolution)
            current_close = IndicatorDecorator.close(resolution)
            dc_h = IndicatorDecorator.donchian_high(resolution, str(window))
            dc_l = IndicatorDecorator.donchian_low(resolution, str(window))
            indicator = DonchianChannel(high=df[current_high],
                                        low=df[current_low],
                                        close=df[current_close],
                                        window=window)
            df[dc_h] = IndicatorDecorator.round_to_decimal(indicator.donchian_channel_hband())
            df[dc_l] = IndicatorDecorator.round_to_decimal(indicator.donchian_channel_lband())
        return df

    @staticmethod
    def add_keltner(df, resolution, indicator_config_map):
        indicator_configs = indicator_config_map.get(resolution, [])
        for indicator_config in indicator_configs:
            window = indicator_config.get("window")
            # column names
            current_high = IndicatorDecorator.high(resolution)
            current_low = IndicatorDecorator.low(resolution)
            current_close = IndicatorDecorator.close(resolution)
            keltner_h = IndicatorDecorator.keltner_high(resolution, str(window))
            keltner_l = IndicatorDecorator.keltner_low(resolution, str(window))
            indicator = KeltnerChannel(high=df[current_high],
                                       low=df[current_low],
                                       close=df[current_close],
                                       window=window)
            df[keltner_h] = IndicatorDecorator.round_to_decimal(indicator.keltner_channel_hband())
            df[keltner_l] = IndicatorDecorator.round_to_decimal(indicator.keltner_channel_lband())
        return df

    @staticmethod
    def filter_dataset_later_than_date(df, yyyy_mm_dd, date_columns="date"):
        df.date = pd.to_datetime(df[date_columns])
        return df[(df[date_columns] >= yyyy_mm_dd)]

    @staticmethod
    def filter_dataset_earlier_than_date(df, yyyy_mm_dd, date_columns="date"):
        df.date = pd.to_datetime(df[date_columns])
        return df[(df[date_columns] <= yyyy_mm_dd)]

    @staticmethod
    def filter_dataset_between_dates(df, yyyy_mm_dd_t0, yyyy_mm_dd_t1, date_columns="date"):
        df.date = pd.to_datetime(df[date_columns])
        return df[(df[date_columns] >= yyyy_mm_dd_t0) & (df[date_columns] <= yyyy_mm_dd_t1)]

    @staticmethod
    def merge_two_df_based_on_date(df1, df2):
        df1.date = pd.to_datetime(df1['date'])
        df2.date = pd.to_datetime(df2['date'])
        return pd.merge_asof(df1, df2, on='date')

    @staticmethod
    def high(resolution):
        name = resolution + "_" + Columns.HIGH
        return name

    @staticmethod
    def low(resolution):
        return resolution + "_" + Columns.LOW

    @staticmethod
    def open(resolution):
        return resolution + "_" + Columns.OPEN

    @staticmethod
    def close(resolution):
        return resolution + "_" + Columns.CLOSE

    @staticmethod
    def average(resolution):
        return resolution + "_" + Columns.AVG

    @staticmethod
    def volume(resolution):
        return resolution + "_" + Columns.VOLUME

    @staticmethod
    def bollinger_high(resolution, window, window_dev):
        return resolution + "_" + "bb_h" + "_" + window + "_" + window_dev

    @staticmethod
    def bollinger_low(resolution, window, window_dev):
        return resolution + "_" + "bb_l" + "_" + window + "_" + window_dev

    @staticmethod
    def ema(resolution, window):
        return resolution + "_" + "ema" + "_" + window

    @staticmethod
    def volume_ema(resolution, window):
        return resolution + "_" + "volume_ema" + "_" + window

    @staticmethod
    def rsi(resolution, window):
        return resolution + "_" + "rsi" + "_" + window

    @staticmethod
    def mfi(resolution, window):
        return resolution + "_" + "mfi" + "_" + window

    @staticmethod
    def donchian_high(resolution, window):
        return resolution + "_" + "dc_h" + "_" + window

    @staticmethod
    def donchian_low(resolution, window):
        return resolution + "_" + "dc_l" + "_" + window

    @staticmethod
    def keltner_high(resolution, window):
        return resolution + "_" + "kl_h" + "_" + window

    @staticmethod
    def keltner_low(resolution, window):
        return resolution + "_" + "kl_l" + "_" + window