from src.coveredcalltrade.PriceBasedTrigger import PriceBasedTrigger
from src.coveredcalltrade.MomentumWeightedTrigger import MomentumWeightedTrigger, M1, M2


class CompositeTrigger:
    def __init__(self, trigger_list):
        self.triggers = trigger_list

    def add_trigger(self, new_trigger):
        self.triggers.append(new_trigger)
        return

    def execute(self, price_list, cur_index, m1, prev_m1_max, m2, prev_m2_max):
        for trigger in self.triggers:
            if isinstance(trigger, PriceBasedTrigger):
                if trigger.execute(price_list, cur_index) is False:
                    return False
            elif isinstance(trigger, MomentumWeightedTrigger):
                if trigger.get_type() == M1:
                    if trigger.execute(m1, prev_m1_max) is False:
                        return False
                elif trigger.get_type() == M2:
                    if trigger.execute(m2, prev_m2_max) is False:
                        return False
                else:
                    raise Exception("Invalid momentum trigger")
            else:
                raise Exception("Invalid trigger")
        return True
