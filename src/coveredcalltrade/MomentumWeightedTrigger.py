

M1 = "M1"
M2 = "M2"


class MomentumWeightedTrigger:
    def __init__(self, multiplier, momentum_type=M1):
        self.multiplier = multiplier
        self.momentum_type = momentum_type

    def get_type(self):
        return self.momentum_type

    def execute(self, current_momentum, prev_max_momentum):
        if current_momentum >= self.multiplier * prev_max_momentum:
            return True
        return False
