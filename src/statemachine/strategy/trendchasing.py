import pandas as pd

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


def generate_level2_signal(df: pd.Series, one_day_high_col, one_day_low_col, one_day_volume_col, volume_ema_col,
                           bb_high_col, bb_low_col, threshold, trend_signal_col):
    uptrend_signal_col = "uptrend_signal"
    downtrend_signal_col = "downtrend_signal"
    df[uptrend_signal_col] = df[one_day_high_col] - df[bb_low_col]
    df[downtrend_signal_col] = df[one_day_low_col] - df[bb_high_col]

    abs_diff = abs(df[uptrend_signal_col]) - abs(df[downtrend_signal_col])

    df[trend_signal_col] = 0
    df.loc[abs_diff > (df[one_day_high_col] / threshold), trend_signal_col] = df[one_day_volume_col] / df[
        volume_ema_col]
    df.loc[abs_diff < (df[one_day_high_col] / threshold), trend_signal_col] = -df[one_day_volume_col] / df[
        volume_ema_col]

    return df


def process_level2_signal(level2_signal_col: str, step_size: int, output_col: str):
    return


def generate_level3_signal(level2_output_col: str, step_size: int, output_col: str):
    return


UNCLEAR = 0.0
UPTREND = 1.0
DOWNTREND = -1.0
TRANSITION_TO_DOWNTREND = -0.5
TRANSITION_TO_UPTREND = 0.5


# Analyze only 1 window
def analyze_window(signal_window_list, up_threshold, down_threshold):
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
        up_left_bound_index = find_first_negative_left(signal_window_list, max_up_signal_index)
        up_right_bound_index = find_first_negative_right(signal_window_list, max_up_signal_index)

        meet_up_threshold = (up_right_bound_index - up_left_bound_index) >= up_threshold
        for i in range(up_left_bound_index + 1, up_right_bound_index):
            if meet_up_threshold:
                res_list[i] = UPTREND
            else:
                res_list[i] = TRANSITION_TO_UPTREND
    if min_down_signal < 0:
        down_left_bound_index = find_first_positive_left(signal_window_list, min_down_signal_index)
        down_right_bound_index = find_first_positive_right(signal_window_list, min_down_signal_index)

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
        result_left_window = analyze_window(left_sub_window_list, up_threshold, down_threshold)
        result_right_window = analyze_window(right_sub_window_list, up_threshold, down_threshold)
        result_mid_window = analyze_window(mid_sub_window_list, up_threshold, down_threshold)

        final_result = result_left_window + res_list[up_left_bound_index + 1: up_right_bound_index] \
                       + result_mid_window + res_list[down_left_bound_index + 1: down_right_bound_index] \
                       + result_right_window
        assert len(signal_window_list) == len(final_result)
        return final_result

    if up_left_bound_index >= down_right_bound_index:
        left_sub_window_list = signal_window_list[:down_left_bound_index + 1]
        right_sub_window_list = signal_window_list[up_right_bound_index:]
        mid_sub_window_list = signal_window_list[down_right_bound_index:up_left_bound_index + 1]
        result_left_window = analyze_window(left_sub_window_list, up_threshold, down_threshold)
        result_right_window = analyze_window(right_sub_window_list, up_threshold, down_threshold)
        result_mid_window = analyze_window(mid_sub_window_list, up_threshold, down_threshold)

        final_result = result_left_window + res_list[down_left_bound_index + 1: down_right_bound_index] \
                       + result_mid_window + res_list[up_left_bound_index + 1: up_right_bound_index] \
                       + result_right_window
        assert len(signal_window_list) == len(final_result)
        return final_result

    if up_left_bound_index < down_left_bound_index < up_right_bound_index:
        left_sub_window_list = signal_window_list[:up_left_bound_index + 1]
        right_sub_window_list = signal_window_list[down_right_bound_index:]
        result_left_window = analyze_window(left_sub_window_list, up_threshold, down_threshold)
        result_right_window = analyze_window(right_sub_window_list, up_threshold, down_threshold)

        final_result = result_left_window + res_list[up_left_bound_index+1:down_right_bound_index] + result_right_window

        assert len(final_result) == len(signal_window_list)
        return final_result

    if down_left_bound_index < up_left_bound_index < down_right_bound_index:
        left_sub_window_list = signal_window_list[:down_left_bound_index + 1]
        right_sub_window_list = signal_window_list[up_right_bound_index:]
        result_left_window = analyze_window(left_sub_window_list, up_threshold, down_threshold)
        result_right_window = analyze_window(right_sub_window_list, up_threshold, down_threshold)

        final_result = result_left_window + res_list[
                                            down_left_bound_index + 1:up_right_bound_index] + result_right_window

        assert len(final_result) == len(signal_window_list)
        return final_result

    return res_list


def find_first_negative_left(signal_window_list, pivot_index):
    for i in range(pivot_index-1, -1, -1):
        if signal_window_list[i] < 0:
            return i
    return 0


def find_first_negative_right(signal_window_list, pivot_index):
    for i in range(pivot_index, len(signal_window_list)):
        if signal_window_list[i] < 0:
            return i
    return len(signal_window_list)


def find_first_positive_left(signal_window_list, pivot_index):
    for i in range(pivot_index-1, -1, -1):
        if signal_window_list[i] > 0:
            return i
    return 0


def find_first_positive_right(signal_window_list, pivot_index):
    for i in range(pivot_index, len(signal_window_list)):
        if signal_window_list[i] > 0:
            return i
    return len(signal_window_list)
