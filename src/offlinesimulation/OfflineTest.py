from typing import List

from src.coveredcalltrade.trigger.CompositeTrigger import CompositeTrigger
from src.offlinesimulation.ErrorAnalyzer import ErrorAnalyzer


def decorate_momentum_column(df):
    momentum_list = [0]
    volume_list = df["volume"].values.tolist()
    price_list = df["close"].values.tolist()
    for i in range(1, len(price_list)):
        momentum_list.append(volume_list[i] * (price_list[i] - price_list[i - 1]))
    df["momentum"] = momentum_list

    momentum_list_2 = [0]
    for i in range(1, len(price_list)):
        factor = 1
        if volume_list[i] != 0 and volume_list[i - 1] != 0:
            factor = volume_list[i] / volume_list[i - 1]
        momentum_list_2.append(factor * (price_list[i] - price_list[i - 1]))
    df["momentum_2"] = momentum_list_2
    return df


def find_max_momentum_date(df, momentum_col):
    max_val = max(df[momentum_col])
    date_list = df["date"].values.tolist()
    mo_list = df[momentum_col].values.tolist()
    # print(max_val)
    idx = -1
    for i in range(len(date_list)):
        if max_val == mo_list[i]:
            idx = i
            break
    return date_list[idx], idx


def find_max_option_price(df, option_col):
    max_val = max(df[option_col])
    date_list = df["date"].values.tolist()
    option_list = df[option_col].values.tolist()
    idx = -1
    for i in range(len(option_list)):
        if max_val == option_list[i]:
            idx = i
            break
    return date_list[idx], idx


def find_min_option_price(df, option_col):
    min_val = min(df[option_col])
    date_list = df["date"].values.tolist()
    option_list = df[option_col].values.tolist()
    idx = -1
    for i in range(len(option_list)):
        if min_val == option_list[i]:
            idx = i
            break
    return date_list[idx], idx


def find_first_max_value_during_the_day(df, option_col, m1, m2, trigger_list: List[CompositeTrigger]):
    m1_list = df[m1].values.tolist()
    m2_list = df[m2].values.tolist()
    price_list = df[option_col].values.tolist()

    m1_max = 0
    m2_max = 0

    for i in range(0, len(m1_list)):
        prev_m1_max = m1_max
        prev_m2_max = m2_max
        m1_max = max(m1_max, m1_list[i])
        m2_max = max(m2_max, m2_list[i])

        for trigger in trigger_list:
            if trigger.execute(price_list, i, m1_list[i], prev_m1_max, m2_list[i], prev_m2_max):
                return price_list[i], i
    return -1, -1


# input_trigger_lists = List[List[CompositeTrigger]], so we can compare multiple different configurations
# df: n days' dataframe with 1min resolution -- stock dataset joined by option dataset
def get_error_analyzer_for_trigger_list(df, option_col_name, input_trigger_lists, is_call_option=True):
    error_analyzer = ErrorAnalyzer(input_trigger_lists)

    all_trigger_lists = error_analyzer.get_all_trigger_lists()

    for list_idx in range(len(all_trigger_lists)):
        trigger_list = all_trigger_lists[list_idx]
        # 390min = 6.5hr -> trading hour in a normal business day
        for i in range(0, len(df) - 390, 390):
            cur_df = df[i:i + 390]

            option_price_list = cur_df[option_col_name].values.tolist()

            _, idx0 = find_max_option_price(cur_df, option_col_name)

            min_date, idx01 = find_min_option_price(cur_df, option_col_name)

            trigger_price, idx1 = find_first_max_value_during_the_day(
                cur_df, option_col_name, "momentum", "momentum_2", trigger_list)

            max_option_price = option_price_list[idx0]
            min_option_price = option_price_list[idx01]

            if is_call_option:
                print("trigger price " + str(trigger_price) + " max price of the day: " + str(max_option_price))
                error_analyzer.accumulate_error(list_idx, trigger_price, max_option_price)
            else:
                error_analyzer.accumulate_error(list_idx, trigger_price, min_option_price)
    return error_analyzer


def start_experiment(raw_df, option_col_name, input_trigger_list, is_call_option=True):
    df_with_momentum = decorate_momentum_column(raw_df)
    error_analyzer = get_error_analyzer_for_trigger_list(df_with_momentum, option_col_name, input_trigger_list, is_call_option)
    return error_analyzer
