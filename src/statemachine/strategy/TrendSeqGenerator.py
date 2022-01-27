import pandas as pd
import numpy as np
import pandas.core.series

# we use the following formula as short term trend indicator:
# 1day_high - bollinger_band_low & 1day_low - bollinger_band_high
# bollinger_band_low = SMA - 2*sigma and bollinger_band_high = SMA + 2*sigma
# When there's a clear uptrend momentum, 1day_high should be significantly higher than SMA with high volatility
# When there's a clear downtrend momentum, 1day_low should be significantly lower than SMA with high volatility
# Therefore, in the uptrend,
# 1day_high - bollinger_band_low (high - SMA + 2*sigma) >> 1day_low - bollinger_band_high (low - SMA - 2*Sigma)
# in the downtrend, abs(1day_high - bollinger_band_low) << abs(1day_low - bollinger_band_high)

# Let's represent the threshold = abs(1day_high - bollinger_band_low) - abs(1day_low - bollinger_band_high)
# Now the lower the absolute value of the threshold, the more signal we will get, vice versa.

# Ideally, for each 100 1-day stock data points, we want to have 70% (~10/15) - 20% (~3/15) signal. We don't want to
# over sample or under sample.
# Proposed threshold range: range(1day_close/5, 1day_close/50) -> roughly (2%, 20%) of variations
# threshold = [1day_close/x for x in range(5, 55, 5)]
# Then we need to create the amplitude of the signal. The intuition is to assign the corresponding 1day_volume
# normalized by the x day ema of the volume (could be 5/10/15 days) - this can be an input variable to the signal
# generation function

# Comment: calibration for the threshold should be made such that the indicator ratio (+/-) should be closer to
# underlying stock's (+/-)

# The next step is to perform signal processing on different granularity levels to generate level-2 signals
# The next step is to perform signal processing for level-2 signals on various granularity.
# The final step is to reconcile different granularity's results from previous step to generate the final inputs
# to the underlying strategy.
import pandas.core.series

UNCLEAR = 0.0
UPTREND = 1.0
DOWNTREND = -1.0
TRANSITION_TO_DOWNTREND = -0.5
TRANSITION_TO_UPTREND = 0.5


class TrendSeqGenerator:

    @staticmethod
    def generate_level2_signal(df: pd.Series, one_day_high_col, one_day_low_col, one_day_volume_col, volume_ema_col,
                               bb_high_col, bb_low_col, threshold, trend_signal_col, signal_rectifying_trend_col):
        uptrend_signal_col = "uptrend_signal"
        downtrend_signal_col = "downtrend_signal"
        df[uptrend_signal_col] = df[one_day_high_col] - df[bb_low_col]
        df[downtrend_signal_col] = df[one_day_low_col] - df[bb_high_col]

        abs_diff = abs(df[uptrend_signal_col]) - abs(df[downtrend_signal_col])

        stock_price_based_threshold = df[one_day_high_col] * threshold

        df[trend_signal_col] = 0
        df.loc[abs_diff > stock_price_based_threshold, trend_signal_col] = df[one_day_volume_col] / df[volume_ema_col]
        df.loc[abs_diff < stock_price_based_threshold, trend_signal_col] = -df[one_day_volume_col] / df[volume_ema_col]

        TrendSeqGenerator.add_level2_signal_rectifying_column(df, trend_signal_col, signal_rectifying_trend_col)

        return

    # [-3, -2, -1, 0, 1, 2, 3] -> df[one_day_volume_col] / df[volume_ema_col]:
    # ratio of the today's volume over ema volumes of 5 days
    @staticmethod
    def add_level2_signal_rectifying_column(df, trend_signal_col, signal_rectifying_trend_col):
        df[signal_rectifying_trend_col] = 0

        df.loc[df[trend_signal_col] >= 2, signal_rectifying_trend_col] = 3
        df[signal_rectifying_trend_col] = np.where((df[trend_signal_col] >= 1) & (df[trend_signal_col] < 2),
                                                   2, df[signal_rectifying_trend_col])
        df[signal_rectifying_trend_col] = np.where((df[trend_signal_col] > 0.2) & (df[trend_signal_col] < 1),
                                                   1, df[signal_rectifying_trend_col])
        df[signal_rectifying_trend_col] = np.where((df[trend_signal_col] >= -1) & (df[trend_signal_col] < -0.2),
                                                   -1, df[signal_rectifying_trend_col])
        df[signal_rectifying_trend_col] = np.where((df[trend_signal_col] >= -2) & (df[trend_signal_col] < -1),
                                                   -2, df[signal_rectifying_trend_col])
        df.loc[df[trend_signal_col] < -2, signal_rectifying_trend_col] = -3
        return

    # prioritize analyzing the highest amplitude signals first; use recursion to finish the analysis of entire signal seq
    # The noise reduction logic is that if the length of a uptrend/downtrend is shorter than the threshold, it's then treated as unclear trend
    # In the case of unclear trend, we assign penalty factor of -0.5/0.5; otherwise the trend is -1/1

    @staticmethod
    def reduce_level2_signal_noise(signal_window_list, up_threshold, down_threshold):
        res_list = [UNCLEAR] * len(signal_window_list)
        if len(signal_window_list) <= 1:
            return res_list

        max_up_signal = max(signal_window_list)
        min_down_signal = min(signal_window_list)

        max_up_signal_index = signal_window_list.index(max_up_signal)
        min_down_signal_index = signal_window_list.index(min_down_signal)

        up_left_bound_index = None
        up_right_bound_index = None

        down_left_bound_index = None
        down_right_bound_index = None

        if max_up_signal > 0:
            # perform analysis around the region from the left and right of this signal
            up_left_bound_index = TrendSeqGenerator.find_first_negative_left(signal_window_list, max_up_signal_index)
            up_right_bound_index = TrendSeqGenerator.find_first_negative_right(signal_window_list, max_up_signal_index)

            meet_up_threshold = (up_right_bound_index - up_left_bound_index) >= up_threshold
            for i in range(up_left_bound_index + 1, up_right_bound_index):
                if meet_up_threshold:
                    res_list[i] = UPTREND
                else:
                    res_list[i] = TRANSITION_TO_UPTREND
        if min_down_signal < 0:
            down_left_bound_index = TrendSeqGenerator.find_first_positive_left(signal_window_list,
                                                                               min_down_signal_index)
            down_right_bound_index = TrendSeqGenerator.find_first_positive_right(signal_window_list,
                                                                                 min_down_signal_index)

            meet_down_threshold = (down_right_bound_index - down_left_bound_index) >= down_threshold
            for j in range(down_left_bound_index + 1, down_right_bound_index):
                if meet_down_threshold:
                    res_list[j] = DOWNTREND
                else:
                    res_list[j] = TRANSITION_TO_DOWNTREND

        if up_left_bound_index is None and down_left_bound_index is None:
            return res_list

        if up_left_bound_index is None or down_left_bound_index is None:
            return res_list

        # Otherwise, uptrend and downtrend exist in the same window

        if up_right_bound_index <= down_left_bound_index:
            left_sub_window_list = signal_window_list[:up_left_bound_index + 1]
            right_sub_window_list = signal_window_list[down_right_bound_index:]
            mid_sub_window_list = signal_window_list[up_right_bound_index:down_left_bound_index + 1]
            result_left_window = TrendSeqGenerator.reduce_level2_signal_noise(left_sub_window_list, up_threshold,
                                                                              down_threshold)
            result_right_window = TrendSeqGenerator.reduce_level2_signal_noise(right_sub_window_list, up_threshold,
                                                                               down_threshold)
            result_mid_window = TrendSeqGenerator.reduce_level2_signal_noise(mid_sub_window_list, up_threshold,
                                                                             down_threshold)

            final_result = result_left_window + res_list[up_left_bound_index + 1: up_right_bound_index] \
                           + result_mid_window + res_list[down_left_bound_index + 1: down_right_bound_index] \
                           + result_right_window
            assert len(signal_window_list) == len(final_result)
            return final_result

        if up_left_bound_index >= down_right_bound_index:
            left_sub_window_list = signal_window_list[:down_left_bound_index + 1]
            right_sub_window_list = signal_window_list[up_right_bound_index:]
            mid_sub_window_list = signal_window_list[down_right_bound_index:up_left_bound_index + 1]
            result_left_window = TrendSeqGenerator.reduce_level2_signal_noise(left_sub_window_list, up_threshold,
                                                                              down_threshold)
            result_right_window = TrendSeqGenerator.reduce_level2_signal_noise(right_sub_window_list, up_threshold,
                                                                               down_threshold)
            result_mid_window = TrendSeqGenerator.reduce_level2_signal_noise(mid_sub_window_list, up_threshold,
                                                                             down_threshold)

            final_result = result_left_window + res_list[down_left_bound_index + 1: down_right_bound_index] \
                           + result_mid_window + res_list[up_left_bound_index + 1: up_right_bound_index] \
                           + result_right_window
            assert len(signal_window_list) == len(final_result)
            return final_result

        if up_left_bound_index < down_left_bound_index < up_right_bound_index:
            left_sub_window_list = signal_window_list[:up_left_bound_index + 1]
            right_sub_window_list = signal_window_list[down_right_bound_index:]
            result_left_window = TrendSeqGenerator.reduce_level2_signal_noise(left_sub_window_list, up_threshold,
                                                                              down_threshold)
            result_right_window = TrendSeqGenerator.reduce_level2_signal_noise(right_sub_window_list, up_threshold,
                                                                               down_threshold)

            final_result = result_left_window + res_list[
                                                up_left_bound_index + 1:down_right_bound_index] + result_right_window

            assert len(final_result) == len(signal_window_list)
            return final_result

        if down_left_bound_index < up_left_bound_index < down_right_bound_index:
            left_sub_window_list = signal_window_list[:down_left_bound_index + 1]
            right_sub_window_list = signal_window_list[up_right_bound_index:]
            result_left_window = TrendSeqGenerator.reduce_level2_signal_noise(left_sub_window_list, up_threshold,
                                                                              down_threshold)
            result_right_window = TrendSeqGenerator.reduce_level2_signal_noise(right_sub_window_list, up_threshold,
                                                                               down_threshold)

            final_result = result_left_window + res_list[
                                                down_left_bound_index + 1:up_right_bound_index] + result_right_window

            assert len(final_result) == len(signal_window_list)
            return final_result

        return res_list

    # level2_signal will be compressed to 1 day resolution
    # window_size and step_size is based on 1 hour
    # min_continuous_uptrend/min_continuous_downtrend is based on 5min resolution
    # trend_sequence generated is based on 1 hour resolution; lookback_window_size is based on 1 hour resolution
    @staticmethod
    def generate_trend_sequence(df: pandas.core.series.Series, trend_signal_col, signal_rectifying_trend_col,
                                min_continuous_uptrend, min_continuous_downtrend, lookback_window_size, date_col="date"):

        # get noise reduced signals
        noise_reduced_trend_signal_list = TrendSeqGenerator.reduce_level2_signal_noise(
            df[signal_rectifying_trend_col].values.tolist(), min_continuous_uptrend, min_continuous_downtrend)

        assert len(noise_reduced_trend_signal_list) == len(df)

        noise_reduced_trend_col = "noise_reduced_trend"
        df[noise_reduced_trend_col] = noise_reduced_trend_signal_list

        deduped_date_col = "tmp_date"
        df_deduped = TrendSeqGenerator.dedupe_df(df,
                                                 deduped_date_col,
                                                 date_col,
                                                 "%Y-%m-%d %H:%M:%S",
                                                 "%Y-%m-%d %H",
                                                 [trend_signal_col, signal_rectifying_trend_col,noise_reduced_trend_col])

        original_trend_signal_list = df_deduped[trend_signal_col].values.tolist()
        # original level2 is weighted by volume/volume_ema
        rectifying_trend_signal_list = df_deduped[signal_rectifying_trend_col].values.tolist()
        noise_reduced_trend_signal_list = df_deduped[noise_reduced_trend_col].values.tolist()

        trend_avg_list = [0] * (lookback_window_size - 1)
        weighted_signal_rectifying_trend_list = [0] * (lookback_window_size - 1)
        weighted_noise_reduced_trend_list = [0] * (lookback_window_size - 1)
        window_size = float(lookback_window_size)
        for i in range(lookback_window_size - 1, len(original_trend_signal_list)):

            trend_avg_list.append(sum(original_trend_signal_list[i - lookback_window_size + 1:i + 1]) / window_size)
            weighted_rectifying_trend_sum = sum([(rectifying_trend_signal_list[k]) * abs(original_trend_signal_list[k])
                                                for k in range(i - lookback_window_size + 1, i)])
            weighted_noise_reduced_trend_sum = sum([(noise_reduced_trend_signal_list[k]) * abs(original_trend_signal_list[k])
                                                    for k in range(i - lookback_window_size + 1, i)])
            weighted_signal_rectifying_trend_list.append(weighted_rectifying_trend_sum / window_size)
            weighted_noise_reduced_trend_list.append(weighted_noise_reduced_trend_sum/window_size)

        print(len(trend_avg_list))
        print(len(weighted_signal_rectifying_trend_list))
        print(len(df_deduped))
        assert len(trend_avg_list) == len(weighted_signal_rectifying_trend_list) == len(weighted_noise_reduced_trend_list)
        df_deduped["avg_trend"] = trend_avg_list
        df_deduped["noise_reduced_weighted_trend"] = weighted_noise_reduced_trend_list
        df_deduped["rectified_weighted_trend"] = weighted_signal_rectifying_trend_list

        return df_deduped

    @staticmethod
    def dedupe_df(df, normalized_new_col, existing_date_col, original_date_format, new_date_format, columns_to_keep):
        df[normalized_new_col] = pd.to_datetime(df[existing_date_col], format=original_date_format).dt.strftime(
            new_date_format)
        columns_to_keep_after_dedupe = [normalized_new_col] + columns_to_keep
        return df[columns_to_keep_after_dedupe].drop_duplicates(subset=normalized_new_col).rename(columns={normalized_new_col: existing_date_col})

    @staticmethod
    def find_first_negative_left(signal_window_list, pivot_index):
        for i in range(pivot_index - 1, -1, -1):
            if signal_window_list[i] < 0:
                return i
        return 0

    @staticmethod
    def find_first_negative_right(signal_window_list, pivot_index):
        for i in range(pivot_index, len(signal_window_list)):
            if signal_window_list[i] < 0:
                return i
        return len(signal_window_list)

    @staticmethod
    def find_first_positive_left(signal_window_list, pivot_index):
        for i in range(pivot_index - 1, -1, -1):
            if signal_window_list[i] > 0:
                return i
        return 0

    @staticmethod
    def find_first_positive_right(signal_window_list, pivot_index):
        for i in range(pivot_index, len(signal_window_list)):
            if signal_window_list[i] > 0:
                return i
        return len(signal_window_list)
