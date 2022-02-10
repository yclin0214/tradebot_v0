from src.statemachine.strategy.TrendAnalyzer import *
from src.statemachine.strategy.TrendWave import *
from src.statemachine.strategy.Trend import *
from src.statemachine.strategy.TrendSeqGenerator import *


INCREASING_UPTREND = "INCREASING_UPTREND"
DECREASING_UPTREND = "DECREASING_UPTREND"
INCREASING_DOWNTREND = "INCREASING_DOWNTREND"
DECREASING_DOWNTREND = "DECREASING_DOWNTREND"


class TrendSummary:

    @staticmethod
    def get_trend_insight_from_past_n_days(up_trendwave_list, down_trendwave_list, days_ago=30):
        up_trendwave_segments, down_trendwave_segments = \
            TrendAnalyzer.get_trend_segments(up_trendwave_list, down_trendwave_list)

        up_trendseg_idx = 0
        down_trendseg_idx = 0
        up_trend_params = TrendSummary.get_trend_segment_params(up_trendwave_segments[up_trendseg_idx])
        down_trend_params = TrendSummary.get_trend_segment_params(down_trendwave_segments[down_trendseg_idx])

        up_dates = up_trend_params["date_list"]
        down_dates = down_trend_params["date_list"]

        up_trend_more_recent = False
        if len(up_dates) > 0 and len(down_dates) > 0:
            up_trend_more_recent = TrendAnalyzer.days_diff(up_dates[-1][1], down_dates[-1][1]) > 0
        if len(down_dates) == 0:
            up_trend_more_recent = True

        if up_trend_more_recent:
            latest_date = up_dates[-1][1]
        else:
            latest_date = down_dates[-1][1]

        comparison_start_date = TrendSummary.days_ago(latest_date, days_ago)

        eligible_up_segments = []
        eligible_down_segments = []

        down_days = 0
        up_days = 0

        for seg in up_trendwave_segments:
            if TrendSummary.is_segment_eligible_for_analysis(comparison_start_date, seg):
                eligible_up_segments.append(TrendSummary.trim_trend_segments_based_on_start_date(comparison_start_date, seg))
                date_pair_list = TrendSummary.get_trend_segment_params(seg)["date_list"]
                up_days += TrendSummary.days_after_start_date(comparison_start_date, date_pair_list)

        for seg in down_trendwave_segments:
            if TrendSummary.is_segment_eligible_for_analysis(comparison_start_date, seg):
                eligible_down_segments.append(TrendSummary.trim_trend_segments_based_on_start_date(comparison_start_date, seg))
                date_pair_list = TrendSummary.get_trend_segment_params(seg)["date_list"]
                down_days += TrendSummary.days_after_start_date(comparison_start_date, date_pair_list)

        res = {"down_days": down_days, "up_days": up_days, "up_weighted_sum": 0.0, "down_weighted_sum": 0.0}

        up_gradient = []
        down_gradient = []
        for seg in eligible_up_segments:
            if len(seg) == 0:
                continue
            up_gradient.append(TrendSummary.get_trend_segment_params(seg)["linear_gradient"])
            res["up_weighted_sum"] += TrendSummary.get_trend_segment_params(seg)["weighted_sum"]
        for seg in eligible_down_segments:
            if len(seg) == 0:
                continue
            down_gradient.append(TrendSummary.get_trend_segment_params(seg)["linear_gradient"])
            res["down_weighted_sum"] += TrendSummary.get_trend_segment_params(seg)["weighted_sum"]

        res["up_gradient"] = up_gradient
        res["down_gradient"] = down_gradient
        return res

    @staticmethod
    def trim_trend_segments_based_on_start_date(comparison_start_date, segment):
        trimmed_segment = []
        for tw in segment:
            # accept the trend start date at most 5 days earlier to the comparison date
            if TrendSummary.days_after_start_date(comparison_start_date, [(tw.get_start_time(), tw.get_end_time())]) >= 1:
                trimmed_segment.append(tw)
        return trimmed_segment

    @staticmethod
    def is_segment_eligible_for_analysis(comparison_start_date, segment):
        date_list = TrendSummary.get_trend_segment_params(segment)["date_list"]
        return TrendSummary.days_after_start_date(comparison_start_date, date_list) > 0

    # trend_segment: subset of the entire trendwave list, divided by the local max/min point
    @staticmethod
    def get_trend_segment_params(trend_segment):
        params_map = {"date_list": TrendAnalyzer.get_sorted_date_from_segment(trend_segment),
                      "linear_gradient": TrendAnalyzer.linear_fit_trend_segment(trend_segment)}
        weighted_sum = 0
        for tw in trend_segment:
            weighted_sum += tw.get_max_amplitude() * TrendAnalyzer.days_diff(tw.get_end_time(), tw.get_start_time())

        params_map["weighted_sum"] = weighted_sum

        return params_map


    @staticmethod
    def days_ago(end_date, n_days_ago=20):
        import datetime
        date1 = end_date.split(" ")[0]
        delta = datetime.timedelta(days=n_days_ago)
        return datetime.datetime.strptime(date1, "%Y-%m-%d") - delta

    @staticmethod
    def str_date_to_datetime(date_str):
        from datetime import datetime
        date1 = date_str.split(" ")[0]
        return datetime.strptime(date1, "%Y-%m-%d")

    @staticmethod
    def days_after_start_date(comparison_start_date, date_pair_list):
        days = 0
        for i in range(len(date_pair_list) - 1, -1, -1):
            end_date = TrendSummary.str_date_to_datetime(date_pair_list[i][1])
            start_date = TrendSummary.str_date_to_datetime(date_pair_list[i][0])
            if (end_date - comparison_start_date).days <= 0:
                return days
            if (start_date - comparison_start_date).days >= 0:
                days += (end_date - start_date).days
            else:
                days += (end_date - comparison_start_date).days
                return days
        return days
