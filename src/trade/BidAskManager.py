import datetime


# Input parameters are bid/ask configurations (optional); bid/ask spread; time
class BidAskManager(object):

    @staticmethod
    def linear_bid_ask_trigger(bid_ask_list: list, cur_bid_ask_price: float,
                               cur_bid_timestamp: datetime.datetime, spread_multiplier=200):
        bid_ask_candidate_list_size = len(bid_ask_list)
        if bid_ask_candidate_list_size <= 1:
            return False

        cur_idx = bid_ask_list.find(cur_bid_ask_price)
        if cur_idx < bid_ask_candidate_list_size - 1:
            # spread = 0.01 -> 2 sec interval; spread = 0.1 -> 20 sec interval; spread = 0.3 -> 60 sec
            time_diff = spread_multiplier * abs(bid_ask_list[cur_idx + 1] - bid_ask_list[cur_idx])
            cur_time = datetime.datetime.now()
            if (cur_time - cur_bid_timestamp).total_seconds() >= time_diff:
                return True
        return False

    @staticmethod
    def get_ask_candidates_anchored_by_bid(bid, ask, base_factor, floor=0):
        # Todo: refactor to use exceptions instead of asserts
        assert 1 < base_factor <= 2
        assert 0.01 <= bid <= ask
        res = []
        spread = ask - bid
        n = 1
        while spread / pow(base_factor, n) >= 0.01:
            next_ask = round(bid + spread / pow(base_factor, n), 2)
            res.append(next_ask)
            n = n + 1
        return BidAskManager.dedupe_sorted_ask_candidates(res, floor)

    @staticmethod
    def get_ask_candidates_anchored_by_ask(bid, ask, base_factor, floor=0):
        # Todo: refactor to use exceptions instead of asserts
        assert 1 < base_factor <= 2
        assert 0.01 <= bid <= ask
        res = []
        spread = ask - bid
        n = 1
        while spread / pow(base_factor, n) >= 0.01:
            next_ask = round(ask - spread / pow(base_factor, n), 2)
            res.append(next_ask)
            n = n + 1
        return BidAskManager.dedupe_sorted_ask_candidates(list(reversed(res)), floor)

    @staticmethod
    def dedupe_sorted_ask_candidates(input_list, floor):
        deduped_list = []
        for i in range(0, len(input_list)):
            if input_list[i] < floor:
                break
            if i > 0 and input_list[i] == input_list[i - 1]:
                continue
            deduped_list.append(input_list[i])
        return deduped_list
