from IndicatorDecorator import IndicatorDecorator


def decorate_1day_resolution_df(df, bb_config_map=None, window_config_map=None):
    if window_config_map is None:
        kl_config_map = dc_config_map = mfi_config_map = rsi_config_map = ema_config_map = \
            {"1day": [{"window": 3}, {"window": 5}, {"window": 10}, {"window": 15}]}
    else:
        kl_config_map = dc_config_map = mfi_config_map = rsi_config_map = ema_config_map = window_config_map
    if bb_config_map is None:
        bb_config_map = {
            "1day": [{"window": 3, "window_dev": 2}, {"window": 5, "window_dev": 2}, {"window": 10, "window_dev": 2},
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


def decorate_and_merge(df_5min, df_1hour, df_1day):
    rn_1day_df = df_1day.rename(columns={"open": "1day_open", "high": "1day_high", "low": "1day_low",
                                         "close": "1day_close", "volume": "1day_volume", "average": "1day_average"})

    rn_1hour_df = df_1hour.rename(columns={"open": "1hour_open", "high": "1hour_high", "low": "1hour_low",
                                          "close": "1hour_close", "volume": "1hour_volume", "average": "1hour_average"})

    rn_5min_df = df_5min.rename(columns={"open": "5min_open", "high": "5min_high", "low": "5min_low",
                                         "close": "5min_close", "volume": "5min_volume", "average": "5min_average"})
    df_1day_decorated = decorate_1day_resolution_df(rn_1day_df)
    df_1hour_decorated = decorate_1hour_resolution_df(rn_1hour_df)
    df_5min_decorated = decorate_5min_resolution_df(rn_5min_df)

    df_1hour_merged = IndicatorDecorator.merge_two_df_based_on_date(df_1hour_decorated, df_1day_decorated)
    df_5min_merged = IndicatorDecorator.merge_two_df_based_on_date(df_5min_decorated, df_1hour_merged)

    return df_5min_merged
