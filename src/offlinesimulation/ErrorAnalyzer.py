class ErrorAnalyzer:
    def __init__(self, input_lists):
        self.input_lists = input_lists
        self.input_list_idx_to_error_sum = {}
        for idx in range(len(self.input_lists)):
            self.input_list_idx_to_error_sum[idx] = 0

    def get_error(self, idx):
        return self.input_list_idx_to_error_sum[idx]

    def get_all_trigger_lists(self):
        return self.input_lists

    def accumulate_error(self, idx, price_at_trigger, ideal_price):
        if len(self.input_lists) == 0:
            return
        self.input_list_idx_to_error_sum[idx] += pow((price_at_trigger - ideal_price), 2)

    def get_list_with_least_error(self, n=1):
        if len(self.input_lists) == 0:
            return []
        list_of_pair = []
        res_idx = []
        for idx in range(len(self.input_lists)):
            list_of_pair.append((idx, self.input_list_idx_to_error_sum[idx]))

        sorted_list_of_pair = sorted(list_of_pair, key=lambda p: p[1])[:n]
        for itm in sorted_list_of_pair:
            res_idx.append(itm[0])

        return res_idx
