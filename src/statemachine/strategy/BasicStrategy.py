from src.statemachine.strategy.TrendAnalyzer import *
from src.statemachine.strategy.Trend import *
from src.statemachine.strategy.TrendSeqGenerator import *
from src.statemachine.strategy.TrendWave import *
from src.statemachine.strategy.TrendSummary import *
import numpy as np


class BasicStrategy:

    UPTREND = "UPTREND"
    DOWNTREND = "DOWNTREND"
    INCREASING = "INCREASING"
    DECREASING = "DECREASING"
    UNCERTAIN = "UNCERTAIN"

    @staticmethod
    def reconcile_ema_and_sigma_trend_segment_results(sigma_trend_res, ema_trend_res):
        # in the case of strong uptrend with both indicators confirmed
        sigma_up_days = sigma_trend_res["up_days"]
        sigma_down_days = sigma_trend_res["down_days"]
        sigma_up_sum = sigma_trend_res["up_weighted_sum"]
        sigma_up_gradient = sigma_trend_res["up_gradient"]
        sigma_down_sum = sigma_trend_res["down_weighted_sum"]
        sigma_down_gradient = sigma_trend_res["down_gradient"]

        ema_up_days = ema_trend_res["up_days"]
        ema_down_days = ema_trend_res["down_days"]
        ema_up_sum = ema_trend_res["up_weighted_sum"]
        ema_up_gradient = ema_trend_res["up_gradient"]
        ema_down_sum = ema_trend_res["down_weighted_sum"]
        ema_down_gradient = ema_trend_res["down_gradient"]

        trend_indicator_map = {"trend": BasicStrategy.UNCERTAIN, "momentum": BasicStrategy.UNCERTAIN}

        if (sigma_up_days - sigma_down_days) > 0 and (ema_up_days - ema_down_days) > 0 and \
                (sigma_up_sum - abs(sigma_down_sum)) > 0 and (ema_up_sum - abs(ema_down_sum)) > 0:
            trend_indicator_map["trend"] = BasicStrategy.UPTREND
            if sigma_up_gradient[0] < 0 and ema_up_gradient[0] < 0:
                trend_indicator_map["momentum"] = BasicStrategy.DECREASING
                return trend_indicator_map
            if sigma_up_gradient[0] > 0 and ema_up_gradient[0] > 0:
                trend_indicator_map["momentum"] = BasicStrategy.INCREASING
                return trend_indicator_map
            # now two trend indicators have different signs of linear fit gradient
            if (len(sigma_down_gradient) == 0 or sigma_down_gradient[0] < 0) and (len(ema_down_gradient) == 0 or ema_down_gradient[0]) < 0:
                trend_indicator_map["momentum"] = BasicStrategy.DECREASING
                return trend_indicator_map
            if len(sigma_down_gradient) > 0 and sigma_down_gradient[0] > 0 and len(ema_down_gradient) > 0 and ema_down_gradient[0] > 0:
                trend_indicator_map["momentum"] = BasicStrategy.INCREASING
                return trend_indicator_map
            trend_indicator_map["momentum"] = BasicStrategy.UNCERTAIN
            return trend_indicator_map

        if (sigma_up_days - sigma_down_days) < 0 and (ema_up_days - ema_down_days) < 0 and \
                (sigma_up_sum - abs(sigma_down_sum)) < 0 and (ema_up_sum - abs(ema_down_sum)) < 0:
            trend_indicator_map["trend"] = BasicStrategy.DOWNTREND
            if sigma_down_gradient[0] < 0 and ema_down_gradient[0] < 0:
                trend_indicator_map["momentum"] = BasicStrategy.INCREASING
                return trend_indicator_map
            if sigma_down_gradient[0] > 0 and ema_down_gradient[0] > 0:
                trend_indicator_map["momentum"] = BasicStrategy.DECREASING
                return trend_indicator_map
            # now two trend indicators have different signs of linear fit gradient
            if (len(sigma_up_gradient) > 0 and sigma_up_gradient[0] > 0) and (len(ema_up_gradient) > 0 and ema_up_gradient[0] > 0):
                trend_indicator_map["momentum"] = BasicStrategy.DECREASING
                return trend_indicator_map
            if len(sigma_up_gradient) > 0 and sigma_up_gradient[0] < 0 and len(ema_up_gradient) > 0 and ema_up_gradient[0] < 0:
                trend_indicator_map["momentum"] = BasicStrategy.INCREASING
                return trend_indicator_map
            trend_indicator_map["momentum"] = BasicStrategy.UNCERTAIN
            return trend_indicator_map

        if (sigma_up_sum - abs(sigma_down_sum)) > abs(sigma_down_sum) and (ema_up_sum - abs(ema_down_sum)) > abs(ema_up_sum):
            trend_indicator_map["trend"] = BasicStrategy.UPTREND
            if sigma_up_gradient[0] > 0 and ema_up_gradient[0] > 0:
                trend_indicator_map["momentum"] = BasicStrategy.INCREASING
                return trend_indicator_map

        if (abs(sigma_down_sum) - sigma_up_sum) > sigma_up_sum and (abs(ema_down_sum) - ema_up_sum) > ema_up_sum:
            trend_indicator_map["trend"] = BasicStrategy.DOWNTREND
            if sigma_down_gradient[0] < 0 and ema_down_gradient[0] < 0:
                trend_indicator_map["momentum"] = BasicStrategy.INCREASING
                return trend_indicator_map
        return trend_indicator_map

    # if we get clear trend indicator from the reconcile_ema_and_sigma_trend_segment_results() function, we
    # can have customized strategy; if not, we will use polynomial/linear fitting to the past 1 month dataset, and use the
    # performance from the past 1 month and 2 weeks to find the tentative strike price
    @staticmethod
    def polynomial_prediction(price_list, days_from_today=20):
        assert len(price_list) >= 3
        x = [i for i in range(len(price_list))]
        z = np.polyfit(x, price_list, 2)
        fit_func = np.poly1d(z)
        x_prediction = x[-1] + days_from_today
        return fit_func(x_prediction)

    @staticmethod
    def linear_prediction(price_list, days_from_today=20):
        assert len(price_list) >= 3
        x = [i for i in range(len(price_list))]
        z = np.polyfit(x, price_list, 1)
        fit_func = np.poly1d(z)
        x_prediction = x[-1] + days_from_today
        return fit_func(x_prediction)

    @staticmethod
    def volume_weighted_avg(price_list, volume_list):
        volume_sum = sum(volume_list)
        assert len(price_list) == len(volume_list)
        if volume_sum == 0:
            return sum(price_list)
        return sum([price_list[i]*volume_list[i] for i in range(len(price_list))])/volume_sum

    # if we get an unclear trend, we want to find the last clear trend; missing signals after a strong signal is
    # detected also provides information. Return the trend summary dictionary, and the date
    @staticmethod
    def find_last_certain_trend_signal(df, cut_off_date_string):
        if len(df) < 15:
            return {}
        df_filtered = df[(df['date'] < cut_off_date_string)]
        _, sigma_trend_wave_tail = TrendAnalyzer.convert_weighted_trend_list_to_trendwaves(
            df_filtered["rectified_weighted_trend"].values.tolist(), df_filtered["date"].values.tolist())
        _, ema_trend_wave_tail = TrendAnalyzer.convert_weighted_trend_list_to_trendwaves(
            df_filtered["ema_diff"].values.tolist(), df_filtered["date"].values.tolist())

        sigma_positive_trend_list, sigma_negative_trend_list = TrendAnalyzer.analyze_occurrence_constraint_trend(
            sigma_trend_wave_tail, 50, 0.1)
        ema_positive_trend_list, ema_negative_trend_list = TrendAnalyzer.analyze_occurrence_constraint_trend(
            ema_trend_wave_tail, 50, 0.1)

        res_ema = TrendSummary.get_trend_insight_from_past_n_days(ema_positive_trend_list,
                                                                  ema_negative_trend_list)

        res_sigma = TrendSummary.get_trend_insight_from_past_n_days(sigma_positive_trend_list,
                                                                    sigma_negative_trend_list)

        trend_summary = BasicStrategy.reconcile_ema_and_sigma_trend_segment_results(res_sigma, res_ema)

        if trend_summary["trend"] == BasicStrategy.UNCERTAIN:
            date_string = TrendSummary.days_ago(cut_off_date_string, 1).strftime("%Y-%m-%d")
            return BasicStrategy.find_last_certain_trend_signal(df_filtered, date_string)

        trend_summary["date"] = cut_off_date_string
        return trend_summary


    @staticmethod
    def strategize(preprocessed_df, one_day_price_df, days_from_today=10):
        current_price_list = one_day_price_df["close"].values.tolist()
        current_volume_list = one_day_price_df["volume"].values.tolist()
        date_list = one_day_price_df['date'].values.tolist()

        if len(date_list) < 2:
            return 0

        weighted_price_avg = BasicStrategy.volume_weighted_avg(current_price_list[-days_from_today:],
                                                               current_volume_list[-days_from_today:])

        trend_summary = BasicStrategy.find_last_certain_trend_signal(preprocessed_df, date_list[-1])

        if len(trend_summary) == 0 or len(trend_summary.keys()) == 0:
            return 1.1 * weighted_price_avg

        if trend_summary["trend"] == BasicStrategy.UPTREND and trend_summary["momentum"] == BasicStrategy.INCREASING:
            return 1.2 * weighted_price_avg
        if trend_summary["trend"] == BasicStrategy.UPTREND:
            return 1.13 * weighted_price_avg
        if trend_summary["trend"] == BasicStrategy.DOWNTREND and trend_summary["momentum"] == BasicStrategy.INCREASING:
            return 0.9 * weighted_price_avg
        if trend_summary["trend"] == BasicStrategy.DOWNTREND:
            return weighted_price_avg
        return 1.1 * weighted_price_avg

    # two weeks prediction
    @staticmethod
    def no_trend_price_adaptive_strategy(one_day_price_df, days_from_today=10):
        current_price_list = one_day_price_df["close"].values.tolist()
        current_volume_list = one_day_price_df["volume"].values.tolist()
        date_list = one_day_price_df['date'].values.tolist()

    @staticmethod
    def strategize_2(preprocessed_df, one_day_price_df, days_from_today=10, mark_up_factor=0.05):
        current_price_list = one_day_price_df["close"].values.tolist()
        current_volume_list = one_day_price_df["volume"].values.tolist()
        date_list = one_day_price_df['date'].values.tolist()

        if len(one_day_price_df) <= 10:
            print("no enough data points for analysis")
            return 0

        weighted_price_avg = BasicStrategy.volume_weighted_avg(current_price_list[-days_from_today:],
                                                               current_volume_list[-days_from_today:])

        trend_summary = BasicStrategy.find_last_certain_trend_signal(preprocessed_df, date_list[-1])

        polynomial_price_prediction = BasicStrategy.polynomial_prediction(current_price_list[-days_from_today:], days_from_today)
        linear_price_prediction = BasicStrategy.linear_prediction(current_price_list[-days_from_today:], days_from_today)
        weighted_prediction_price = (weighted_price_avg + polynomial_price_prediction + linear_price_prediction)/3

        if len(trend_summary.keys()) == 0:
            print("no strong signal in the past; Use weighted price avg as a prediction")
            return (1 + mark_up_factor) * weighted_price_avg

        trend_end_date = trend_summary["date"]
        current_date = date_list[-1]
        days_diff = (TrendSummary.str_date_to_datetime(current_date) - TrendSummary.str_date_to_datetime(trend_end_date)).days
        price_at_the_last_trend_signal = current_price_list[-days_diff]

        sorted_price_list = sorted([price_at_the_last_trend_signal,
                                    weighted_price_avg * (1 + mark_up_factor),
                                    polynomial_price_prediction,
                                    linear_price_prediction,
                                    weighted_prediction_price])
        print("weighted_price_avg: " + str(weighted_price_avg) + " poly: " + str(polynomial_price_prediction) +
              " linear: " + str(linear_price_prediction) + " avg_prediction: " + str(weighted_prediction_price))

        if trend_summary["trend"] != BasicStrategy.UNCERTAIN:
            if days_diff <= days_from_today:
                print("found a clear trend signal in the past recent days")
                if trend_summary["trend"] == BasicStrategy.UPTREND and trend_summary["momentum"] == BasicStrategy.INCREASING:
                    # 1.15 * current_price < prediction_price < 1.3 * current_price
                    return max(min(1.3 * current_price_list[-1], sorted_price_list[-2]), 1.15 * current_price_list[-1])
                    # 1.1 * current_price < prediction_price < 1.2 * current_price
                elif trend_summary["trend"] == BasicStrategy.UPTREND:
                    return max(min(1.2 * current_price_list[-1], sorted_price_list[-2]), 1.1 * current_price_list[-1])
                    # increasing downtrend, 0.8 * current_price < prediction_price < 1.05 * current_price
                elif trend_summary["trend"] == BasicStrategy.DOWNTREND and trend_summary["momentum"] == BasicStrategy.INCREASING:
                    return min(max(0.8 * current_price_list[-1], sorted_price_list[1]), 1.05 * current_price_list[-1])
                    # uncertain downtrend, 0.9 * current_price < prediction_price < 1.1 * current_price
                elif trend_summary["trend"] == BasicStrategy.DOWNTREND:
                    return min(max(0.9 * current_price_list[-1], sorted_price_list[1]), 1.1 * current_price_list[-1])
            else:
                print("last clear trend signal is a while ago. We need to analyze the price action during the absence of the signal")
                if trend_summary["trend"] == UPTREND:
                    # could be signalling a trend reversal. so 0.9 * current_price < prediction_price < 1.15 * current_price
                    if current_price_list[-1] <= price_at_the_last_trend_signal or weighted_price_avg <= price_at_the_last_trend_signal:
                        return max(0.9 * current_price_list[-1], min(1.15 * current_price_list[-1], polynomial_price_prediction * (1 + mark_up_factor)))
                    else:
                        return max(current_price_list[-1], min(1.2 * current_price_list[-1], polynomial_price_prediction * (1 + mark_up_factor)))
                elif trend_summary["trend"] == DOWNTREND:
                    # could be signalling a trend reversal. so prediction_price  current_price < prediction_price < 1.2 * current_price
                    if current_price_list[-1] >= price_at_the_last_trend_signal or weighted_price_avg >= price_at_the_last_trend_signal:
                        return max(current_price_list[-1], min(1.2 * current_price_list[-1], polynomial_price_prediction * (1 + mark_up_factor)))
                    else:
                        return max(0.9 * current_price_list[-1], min(1.15 * current_price_list[-1], polynomial_price_prediction * (1 + mark_up_factor)))

        # prioritize polynomial price prediction as it can reveal some short term trend pattern
        if 0.8 * current_price_list[-1] <= polynomial_price_prediction <= 1.2 * current_price_list[-1]:
            return polynomial_price_prediction

        # if polynomial prediction is too far off from the current price level, we will just use the weighted average
        return (1 + mark_up_factor) * weighted_price_avg

    @staticmethod
    def self_correct_prediction(df):
        return

    @staticmethod
    def evaluate_strategy(df, prediction_col, shifted_prediction_col):

        return









