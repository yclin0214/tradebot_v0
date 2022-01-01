import math


# Input parameters are bid/ask configurations (optional); bid/ask spread; time
class BidAskManager:

    @staticmethod
    def get_ask_candidates_anchored_by_bid(bid, ask, base_factor, floor=0):
        # Todo: refactor to
        assert 1 < base_factor <= 2
        assert 0.01 <= bid <= ask
        res = []
        spread = ask - bid
        n = 1
        while spread/pow(base_factor, n) >= 0.01:
            next_ask = round(bid + spread/pow(base_factor, n), 2)
            res.append(next_ask)
            n = n + 1
        return BidAskManager.dedupe_sorted_ask_candidates(res, floor)

    @staticmethod
    def get_ask_candidates_anchored_by_ask(bid, ask, base_factor, floor=0):
        assert 1 < base_factor <= 2
        assert 0.01 <= bid <= ask
        res = []
        spread = ask - bid
        n = 1
        while spread/pow(base_factor, n) >= 0.01:
            next_ask = round(ask - spread/pow(base_factor, n), 2)
            res.append(next_ask)
            n = n + 1
        return BidAskManager.dedupe_sorted_ask_candidates(list(reversed(res)), floor)

    @staticmethod
    def dedupe_sorted_ask_candidates(input_list, floor):
        deduped_list = []
        for i in range(0, len(input_list)):
            if input_list[i] < floor:
                break
            if i > 0 and input_list[i] == input_list[i-1]:
                continue
            deduped_list.append(input_list[i])
        return deduped_list