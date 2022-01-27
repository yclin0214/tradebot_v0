# input: weighted_trend_list generated from TrendSeqGenerator, as well as datetime_list
# output is the analysis of the current trend, namely
# increasing uptrend/decreasing uptrend/increasing downtrend/decreasing downtrend
from src.statemachine.strategy.TrendWave import *
from src.statemachine.strategy.Trend import Trend, INCREASING_TREND, NEUTRAL_TREND, DECREASING_TREND

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
        if len(time_constraint_positive_trendwaves) <= 1 or len(time_constraint_negative_trendwaves) <= 1:
            return

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

            if TrendAnalyzer.days_diff(latest_down_trend.get_end_time(), current_down_trend.start_time()) >= trend_time_max_diff:
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


    @staticmethod
    def trend_inference(up_trend_list, down_trend_list):
        assert len(up_trend_list) > 0 or len(down_trend_list) > 0
        if len(down_trend_list) == 0:
            if up_trend_list[0].get_trend() == INCREASING_TREND:
                return INCREASING_UPTREND
            elif up_trend_list[0].get_trend() == DECREASING_TREND:
                return DECREASING_UPTREND
            else:
                # For now, no increasing_uptrend is judged as decreasing uptrend
                # Todo: we can optimize a step further by calling additional datapoints by calling analyze_occurrence_constraint_trend()
                return DECREASING_UPTREND
        if len(up_trend_list) == 0:
            if down_trend_list[0].get_trend() == INCREASING_TREND:
                return INCREASING_DOWNTREND
            elif down_trend_list[0].get_trend() == DECREASING_TREND:
                return DECREASING_DOWNTREND
            else:
                # Todo: calling to get additional datapoints by calling analyze_occurrence_constraint_trend()
                return DECREASING_DOWNTREND





