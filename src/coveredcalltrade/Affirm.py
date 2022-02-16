from datetime import datetime
from TradeStrategy import TradeStrategy

# Approach 1: peak momentum delayed trigger -- once a stock momentum reaches the peak value, trigger the execution
# Approach 1: we need to figure out the optimal delay latency after reaching the peak momentum value

# Other aspects: we can set manual minimum value for the option strike price and minimum theta/delta value
class Affirm(TradeStrategy):
    def __init__(self, name="AFRM"):
        super().__init__(name)
        self.option_key_to_price_list_map = {}
        self.stock_10sec_aggregation_list = []  # [(volume_weighted_stock_price, total_volume, timestamp)..]

        self.max_momentum = 0
        self.max_momentum_index = -1
        self.momentum_list = [0]

    def sell_call_trigger_condition(self, stock_price, stock_volume, option_data, option_contract):
        current_time = datetime.now()
        if len(self.stock_10sec_aggregation_list) == 0:
            self.stock_10sec_aggregation_list.append((stock_price, stock_volume, current_time))
            return

        latest_aggregation_segment = self.stock_10sec_aggregation_list[-1]
        latest_aggregation_segment_start_time = latest_aggregation_segment[2]
        if (current_time - latest_aggregation_segment_start_time).seconds <= 5:
            updated_weighted_stock_price = (latest_aggregation_segment[1] * latest_aggregation_segment[0]
                                            + stock_price * stock_volume)/(stock_volume + latest_aggregation_segment[1])
            updated_total_volume = latest_aggregation_segment[1] + stock_volume
            latest_aggregation_segment_updated = (updated_weighted_stock_price, updated_total_volume, latest_aggregation_segment_start_time)
            self.stock_10sec_aggregation_list[-1] = latest_aggregation_segment_updated
        else:
            # create a new segment
            self.stock_10sec_aggregation_list.append((stock_price, stock_volume, current_time))

        self.update_max_momentum()

        return

    def buy_call_trigger_condition(self, stock_price, stock_volume, option_data, option_contract):
        return

    def update_max_momentum(self):
        if len(self.stock_10sec_aggregation_list) < 2:
            return
        latest_weighted_price = self.stock_10sec_aggregation_list[-1][0]
        latest_total_volume = self.stock_10sec_aggregation_list[-1][1]
        second_latest_weighted_price = self.stock_10sec_aggregation_list[-2][0]

        current_momentum = (latest_weighted_price - second_latest_weighted_price) * latest_total_volume

        # in the case of not creating a new segment, we don't append a new momentum to the list
        if len(self.momentum_list) == len(self.stock_10sec_aggregation_list):
            self.momentum_list[-1] = current_momentum
        else:
            self.momentum_list.append(current_momentum)

        if current_momentum > self.max_momentum:
            self.max_momentum_index = len(self.stock_10sec_aggregation_list) - 1
            self.max_momentum = current_momentum
        return

    # max momentum delayed strategy -- we don't pull the trigger at the max stock momentum, but several delayed segments
    # after that if the segments are all positive, but are winding down
    def momentum_based_trigger(self):
        if len(self.momentum_list) < 5:  # less than 25 secs datasets. No need to rush here
            return False

        max_momentum_index = self.max_momentum_index
        # if the max_momentum_index is discovered 30 secs ago and the rest of the segments are still positive,
        # we want to capture this momentum to open a covered call position
        all_positive = True
        # Todo: we need to do some experiment to find the variable here. Maybe with an offline 1-min dataset
        if 0 < max_momentum_index < len(self.momentum_list) - 5:
            for i in range(max_momentum_index, len(self.momentum_list)):
                if self.momentum_list[i] < 0:
                    all_positive = False
                    break
        return all_positive

    # This is the part where we can hardcode some values
    # Todo:
    def get_option_candidates_to_monitor(self):
        return



