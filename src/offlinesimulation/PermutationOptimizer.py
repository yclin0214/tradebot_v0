class PermutationOptimizer:
    def __init__(self, input_list):
        self.permutation_list = [input_list]
        self.permutation_list_idx_to_error_sum = {}
        for idx in range(len(self.permutation_list)):
            self.permutation_list_idx_to_error_sum[idx] = 0

    def get_error(self, idx):
        return self.permutation_list_idx_to_error_sum[idx]

    def get_all_trigger_lists(self):
        return self.permutation_list

    def accumulate_error(self, idx, price_at_trigger, ideal_price):
        if len(self.permutation_list) == 0:
            return
        self.permutation_list_idx_to_error_sum[idx] += pow((price_at_trigger - ideal_price), 2)

    def get_list_with_least_error(self, n=1):
        if len(self.permutation_list) == 0:
            return []
        list_of_pair = []
        res_idx = []
        for idx in range(len(self.permutation_list)):
            list_of_pair.append((idx, self.permutation_list_idx_to_error_sum[idx]))

        sorted_list_of_pair = sorted(list_of_pair, key=lambda p: p[1])[:n]
        for itm in sorted_list_of_pair:
            res_idx.append(itm[0])

        return res_idx

    @staticmethod
    def randomize_trigger_list(trigger_list):
        from itertools import permutations
        list_of_all_trigger_lists = list(permutations(trigger_list))
        return list_of_all_trigger_lists
