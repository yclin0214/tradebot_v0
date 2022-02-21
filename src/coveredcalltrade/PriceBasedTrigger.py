

class PriceBasedTrigger:
    def __init__(self, look_back_ctr, multiplier):
        self.look_back_ctr = look_back_ctr
        self.multiplier = multiplier

    def execute(self, price_list, current_index):
        if current_index < self.look_back_ctr:
            return False
        if price_list[current_index] >= self.multiplier * price_list[current_index - self.look_back_ctr]:
            return True
        return False


