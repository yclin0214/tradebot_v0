# input: weighted_trend_list generated from TrendSeqGenerator, as well as datetime_list
# output is the analysis of the current trend, namely
# increasing uptrend/decreasing uptrend/increasing downtrend/decreasing downtrend
from src.statemachine.strategy.TrendWave import *
from src.statemachine.strategy.Trend import Trend, INCREASING_TREND, NEUTRAL_TREND, DECREASING_TREND
import numpy as np

INCREASING_UPTREND = "INCREASING_UPTREND"
DECREASING_UPTREND = "DECREASING_UPTREND"
INCREASING_DOWNTREND = "INCREASING_DOWNTREND"
DECREASING_DOWNTREND = "DECREASING_DOWNTREND"
NEED_ADDITIONAL_FLAG = "NEED_ADDITIONAL_FLAG"


class TrendAnalyzer:

    # return the head and the tail of the linked list
    @staticmethod
    def convert_weighted_trend_list_to_trendwaves(weighted_trend_list, datetime_list):
        assert len(weighted_trend_list) == len(datetime_list)
        assert len(weighted_trend_list) > 0
        idx = 0
        trend_wave_earliest = TrendWave(weighted_trend_list[idx], datetime_list[idx], None, weighted_trend_list[idx] > 0)
        trend_wave = trend_wave_earliest
        while idx < len(weighted_trend_list):
            trend_wave.update_trend_wave(weighted_trend_list[idx], datetime_list[idx])
            if trend_wave.is_current_trend_wave_completed():
                new_trend_wave = TrendWave(weighted_trend_list[idx], datetime_list[idx], trend_wave,
                                           weighted_trend_list[idx] > 0)
                trend_wave.set_next_node(new_trend_wave)
                trend_wave = new_trend_wave
            idx += 1
        return trend_wave_earliest, trend_wave

    # for back testing, this can take any node in the linked list, and test from there
    @staticmethod
    def get_sign_aligned_trend_waves(tail_trend: TrendWave):
        negative_trend_wave = []
        positive_trend_wave = []
        while tail_trend.get_prev_node() is not None:
            if tail_trend.get_sign():
                positive_trend_wave.append(tail_trend)
            else:
                negative_trend_wave.append(tail_trend)
            tail_trend = tail_trend.get_prev_node()

        if tail_trend.get_sign():
            positive_trend_wave.append(tail_trend)
        else:
            negative_trend_wave.append(tail_trend)

        return positive_trend_wave, negative_trend_wave

    # days_ago = actual days divided by trend_wave resolution (1/2/3/4... days)
    @staticmethod
    def analyze_time_constraint_trend(tail_trend: TrendWave, max_trend_duration: int, max_trend_gap: int,
                                      min_trend_amplitude: float):
        positive_trend_wave, negative_trend_wave = TrendAnalyzer.get_sign_aligned_trend_waves(tail_trend)
        # first item in the array -> latest trend wave
        latest_positive_trend_list = []
        latest_negative_trend_list = []

        if len(positive_trend_wave) > 0:
            latest_positive_trend_list.append(positive_trend_wave[0])

        if len(negative_trend_wave) > 0:
            latest_negative_trend_list.append(negative_trend_wave[0])

        for i in range(1, len(positive_trend_wave)):
            # consecutive trend wave gap constraint; latest_positive_trend_list[-1] is AFTER the earlier trend wave
            # so we subtract its start_time from the previous trend wave's end time
            if TrendAnalyzer.days_diff(latest_positive_trend_list[-1].get_start_time(), positive_trend_wave[i].get_end_time()) > max_trend_gap:
                break
            # look back window constraint - latest trend wave to earliest trend wave time constraint
            # For example, we are not interested in knowing the trend from 120 days ago as it doesn't help with analysis
            if TrendAnalyzer.days_diff(latest_positive_trend_list[0].get_end_time(), positive_trend_wave[i].get_end_time()) > max_trend_duration:
                break
            # Basically to filter the noise
            if positive_trend_wave[i].get_max_amplitude() >= min_trend_amplitude:
                latest_positive_trend_list.append(positive_trend_wave[i])

        for j in range(1, len(negative_trend_wave)):
            # consecutive trend constraint
            if TrendAnalyzer.days_diff(latest_negative_trend_list[-1].get_start_time(), negative_trend_wave[j].get_end_time()) > max_trend_gap:
                break
            if TrendAnalyzer.days_diff(latest_negative_trend_list[0].get_end_time(), negative_trend_wave[j].get_end_time()) > max_trend_duration:
                break
            if abs(negative_trend_wave[j].get_max_amplitude()) >= min_trend_amplitude:
                latest_negative_trend_list.append(negative_trend_wave[j])

        return latest_positive_trend_list, latest_negative_trend_list

    @staticmethod
    def analyze_occurrence_constraint_trend(tail_trend: TrendWave, max_count: int, minimum_trend_amplitude: float):
        positive_trend_wave, negative_trend_wave = TrendAnalyzer.get_sign_aligned_trend_waves(tail_trend)
        # first item in the array -> latest trend wave
        latest_positive_trend_list = []
        latest_negative_trend_list = []
        if len(positive_trend_wave) > 0:
            latest_positive_trend_list.append(positive_trend_wave[0])

        if len(negative_trend_wave) > 0:
            latest_negative_trend_list.append(negative_trend_wave[0])

        for i in range(1, len(positive_trend_wave)):
            # consecutive trend wave constraint
            if len(latest_positive_trend_list) >= max_count:
                break
            if positive_trend_wave[i].get_max_amplitude() >= minimum_trend_amplitude:
                latest_positive_trend_list.append(positive_trend_wave[i])

        for j in range(1, len(negative_trend_wave)):
            # consecutive trend constraint
            if len(latest_negative_trend_list) >= max_count:
                break
            if abs(negative_trend_wave[j].get_max_amplitude()) >= minimum_trend_amplitude:
                latest_negative_trend_list.append(negative_trend_wave[j])

        return latest_positive_trend_list, latest_negative_trend_list

    @staticmethod
    def classify_current_trend(time_constraint_positive_trendwaves,
                               time_constraint_negative_trendwaves,
                               adjacent_amplitude_diff_factor,
                               trend_time_max_diff):
        if len(time_constraint_positive_trendwaves) < 1 or len(time_constraint_negative_trendwaves) < 1:
            return [], []

        up_trend_list = [Trend(time_constraint_positive_trendwaves[0].get_max_amplitude(),
                               time_constraint_positive_trendwaves[0].get_start_time(),
                               time_constraint_positive_trendwaves[0].get_end_time())]

        down_trend_list = [Trend(time_constraint_negative_trendwaves[0].get_max_amplitude(),
                                 time_constraint_negative_trendwaves[0].get_start_time(),
                                 time_constraint_negative_trendwaves[0].get_end_time())]

        up_trendwaves_idx = down_trendwaves_idx = 1

        while up_trendwaves_idx < len(time_constraint_positive_trendwaves):
            # [DECREASING, INCREASING] or [INCREASING, DECREASING], more than 2 states are not too useful
            if len(up_trend_list) > 2:
                break
            current_up_trend = up_trend_list[-1]
            latest_up_trend = up_trend_list[0]
            if TrendAnalyzer.days_diff(latest_up_trend.get_end_time(), current_up_trend.get_start_time()) >= trend_time_max_diff:
                break
            prev_trend_wave = time_constraint_positive_trendwaves[up_trendwaves_idx]
            prev_trend_wave_amplitude = prev_trend_wave.get_max_amplitude()

            # all positive
            sorted_amplitude = sorted(current_up_trend.get_amplitude_list())

            for amp in sorted_amplitude:
                assert amp > 0

            # max of the 2 smallest amplitudes
            increasing_uptrend_diff = sum(sorted_amplitude[:2]) / len(sorted_amplitude[:2]) - prev_trend_wave_amplitude
            # min of 2 largest amplitudes
            decreasing_uptrend_diff = sum(sorted_amplitude[-2:]) / len(
                sorted_amplitude[-2:]) - prev_trend_wave_amplitude

            up_trend_list = TrendAnalyzer.process_trend(current_up_trend,
                                                        up_trend_list,
                                                        increasing_uptrend_diff,
                                                        decreasing_uptrend_diff,
                                                        adjacent_amplitude_diff_factor * prev_trend_wave_amplitude,
                                                        prev_trend_wave)
            up_trendwaves_idx += 1

            # trend unclear case

        while down_trendwaves_idx < len(time_constraint_negative_trendwaves):
            if len(down_trend_list) > 2:
                break
            current_down_trend = down_trend_list[-1]
            latest_down_trend = down_trend_list[0]

            if TrendAnalyzer.days_diff(latest_down_trend.get_end_time(), current_down_trend.get_end_time()) >= trend_time_max_diff:
                break

            prev_trend_wave = time_constraint_negative_trendwaves[down_trendwaves_idx]
            prev_trend_wave_amplitude = prev_trend_wave.get_max_amplitude()

            sorted_amplitude = sorted(current_down_trend.get_amplitude_list())

            for amp in sorted_amplitude:
                assert amp < 0

            # sorted_amplitude contains all negative values
            increasing_downtrend_diff = abs(sum(sorted_amplitude[-2:]) / len(sorted_amplitude[-2:])) - abs(
                prev_trend_wave_amplitude)
            decreasing_downtrend_diff = abs(sum(sorted_amplitude[:2]) / len(sorted_amplitude[:2])) - abs(
                prev_trend_wave_amplitude)

            down_trend_list = TrendAnalyzer.process_trend(current_down_trend,
                                                          down_trend_list,
                                                          increasing_downtrend_diff,
                                                          decreasing_downtrend_diff,
                                                          adjacent_amplitude_diff_factor * abs(
                                                              prev_trend_wave_amplitude),
                                                          prev_trend_wave)
            down_trendwaves_idx += 1

        return up_trend_list, down_trend_list

    @staticmethod
    def process_trend(current_trend: Trend, trend_list, increasing_diff, decreasing_diff, adjacent_amplitude_min_diff,
                      prev_trend_wave):
        prev_trend_wave_start_time = prev_trend_wave.get_start_time()
        prev_trend_wave_end_time = prev_trend_wave.get_end_time()
        prev_trend_wave_amplitude = prev_trend_wave.get_max_amplitude()

        if increasing_diff >= adjacent_amplitude_min_diff:
            if current_trend.get_trend() == INCREASING_TREND or current_trend.get_trend() == NEUTRAL_TREND:
                # no change, update the timestamp and the start_amplitude and the amplitude_list
                current_trend.set_start_time(prev_trend_wave_start_time)
                current_trend.set_start_amplitude(prev_trend_wave_amplitude)
                current_trend.add_to_amplitude_list(prev_trend_wave_amplitude)
                current_trend.set_trend(INCREASING_TREND)
            else:  # previous Trend is a downtrend, so we start a new trend here
                next_trend = Trend(prev_trend_wave_amplitude,
                                   prev_trend_wave_start_time,
                                   prev_trend_wave_end_time,
                                   INCREASING_TREND)
                trend_list.append(next_trend)
        # no change to the trend; could trend state is the same, so no extra trend is appended to the list
        elif abs(increasing_diff) < adjacent_amplitude_min_diff \
                or abs(decreasing_diff) < adjacent_amplitude_min_diff:
            current_trend.add_to_amplitude_list(prev_trend_wave_amplitude)
            current_trend.set_start_amplitude(prev_trend_wave_amplitude)
            current_trend.set_start_time(prev_trend_wave_start_time)
        # this means we prioritize on identifying the increasing uptrend
        elif decreasing_diff <= -adjacent_amplitude_min_diff:
            if current_trend.get_trend() == DECREASING_TREND or current_trend.get_trend() == NEUTRAL_TREND:
                # no change, update the timestamp and the start_amplitude and the amplitude_list
                current_trend.set_start_time(prev_trend_wave_start_time)
                current_trend.set_start_amplitude(prev_trend_wave_amplitude)
                current_trend.add_to_amplitude_list(prev_trend_wave_amplitude)
                current_trend.set_trend(DECREASING_TREND)
            else:  # previous trend is a uptrend, so we start a new trend here
                next_trend = Trend(prev_trend_wave_amplitude,
                                   prev_trend_wave_start_time,
                                   prev_trend_wave_end_time,
                                   DECREASING_TREND)
                trend_list.append(next_trend)
        return trend_list

    # YYYY-MM-DD HH-MM-SS or YYYY-MM-DD HH; either way we are only interested in YYYY-MM-DD
    @staticmethod
    def days_diff(later_date, earlier_date):
        from datetime import datetime
        date1 = later_date.split(" ")[0]
        date2 = earlier_date.split(" ")[0]
        return (datetime.strptime(date1, "%Y-%m-%d") - datetime.strptime(date2, "%Y-%m-%d")).days

    # Todo: this is a test/simulation
    # trendwave_list start with the latest trendwave
    @staticmethod
    def get_trend_segments(up_trendwave_list, down_trendwave_list, n=3):
        up_trendwave_amplitude_list = [tw.get_max_amplitude() for tw in up_trendwave_list]
        down_trendwave_amplitude_list = [tw.get_max_amplitude() for tw in down_trendwave_list]

        up_trendwave_pivots = TrendAnalyzer.find_pivots(up_trendwave_amplitude_list, n)
        down_trendwave_pivots = TrendAnalyzer.find_pivots(down_trendwave_amplitude_list, n)

        up_trendwave_segments = []
        down_trendwave_segments = []

        for i in range(len(up_trendwave_pivots)):
            if i == 0:
                up_trendwave_segments.append(up_trendwave_list[:up_trendwave_pivots[i]+1])
            else:
                up_trendwave_segments.append(up_trendwave_list[up_trendwave_pivots[i-1]+1: up_trendwave_pivots[i]+1])

        for j in range(len(down_trendwave_pivots)):
            if j == 0:
                down_trendwave_segments.append(down_trendwave_list[:down_trendwave_pivots[j]+1])
            else:
                down_trendwave_segments.append(down_trendwave_list[down_trendwave_pivots[j-1]+1: down_trendwave_pivots[j]+1])

        if len(up_trendwave_segments) == 0:
            up_trendwave_segments = [up_trendwave_list]
        if len(down_trendwave_segments) == 0:
            down_trendwave_segments = [down_trendwave_list]

        return up_trendwave_segments, down_trendwave_segments

    @staticmethod
    def find_pivots(trendwave_amplitude_list, n):
        if len(trendwave_amplitude_list) < 3:
            return []
        last_idx = len(trendwave_amplitude_list) - 1
        idx = 1
        result_list = []
        while len(result_list) < n and idx < last_idx:
            if TrendAnalyzer.is_a_pivot(trendwave_amplitude_list, idx):
                result_list.append(idx)
            idx += 1
        return result_list

    @staticmethod
    def is_a_pivot(input_list, pivot_index, diff_factor=0.4, local_max_min=0.8, local_min_max=1.2):
        if len(input_list[pivot_index:]) < 2:
            return False
        if len(input_list[:pivot_index+1]) < 2:
            return False
        # local max
        prev = abs(input_list[pivot_index-1])
        cur = abs(input_list[pivot_index])
        nex = abs(input_list[pivot_index+1])
        if prev < cur and cur > nex:
            if (cur - prev) >= cur * diff_factor:
                return cur > local_min_max
            if (cur - nex) >= cur * diff_factor:
                return cur > local_min_max
        # local min
        elif prev > cur and cur < nex:
            if (prev - cur) >= prev * diff_factor:
                return cur < local_max_min
            if (nex - cur) >= nex * diff_factor:
                return cur < local_max_min
        return False

    # this gives us a basic idea of whether the trend is increasing or decreasing
    @staticmethod
    def linear_fit_trend_segment(segment):
        # we need to reverse to have the sequence from the earliest time in the list
        y = [tw.get_max_amplitude() for tw in segment][::-1]
        x = [i for i in range(len(segment))]

        if len(segment) == 0:
            return 0
        if len(y) < 2:
            return y[0]

        return np.polyfit(x, y, 1)[0]

    @staticmethod
    def get_sorted_date_from_segment(segment):
        if len(segment) == 0:
            return []
        return [(tw.get_start_time(), tw.get_end_time()) for tw in segment][::-1]





