from datetime import datetime, date, timedelta
from ib_insync import *
from src.coveredcalltrade.AbstractStrategy import AbstractStrategy
from src.coveredcalltrade.trigger.CompositeTrigger import CompositeTrigger

from src.coveredcalltrade.trigger.PriceBasedTrigger import *
from src.coveredcalltrade.trigger.MomentumWeightedTrigger import *


# This class just provides the strategy. It doesn't know the state of the transaction status
class Affirm(AbstractStrategy):
    def __init__(self, ib_client: IB, name="AFRM", trade_interval=30):
        super().__init__(name)
        self.ib_client = ib_client
        self.price_list_1min = []
        self.volume_list_1min = []

        self.last_updated_timestamp = None
        self.max_m1_momentum = 0
        self.max_m2_momentum = 0

        # Todo: to add the trigger list creation function
        self.trigger_list = Affirm.generate_composite_trigger_list_for_call_selling()
        self.composite_trigger = CompositeTrigger(self.trigger_list)

        self.trade_interval = trade_interval

    def update_price_and_volume(self):
        current_time = datetime.now()
        if self.last_updated_timestamp is None:
            self.req_1min_stock_data()
            if len(self.price_list_1min) > 0:
                self.last_updated_timestamp = current_time
        elif (current_time - self.last_updated_timestamp).seconds >= self.trade_interval:  # refresh the datasets every 30 secs
            self.req_1min_stock_data()

        return

    def req_1min_stock_data(self):
        stock_contract = Stock(self.symbol, "SMART", currency="USD")
        bars = self.ib_client.reqHistoricalData(stock_contract,
                                                endDateTime="",
                                                durationStr="1 D",
                                                barSizeSetting="1 min",
                                                whatToShow="TRADE",
                                                useRTH=True,
                                                timeout=5000)
        current_df = util.df(bars)
        self.price_list_1min = current_df["close"].values.tolist()
        self.volume_list_1min = current_df["volume"].values.tolist()
        return

    def req_1sec_option_data(self, option_contract):
        bars = self.ib_client.reqHistoricalData(option_contract,
                                                endDateTime='',
                                                durationStr='60 S',
                                                barSizeSetting='1 secs',
                                                whatToShow='TRADES',
                                                useRTH=True,
                                                timeout=1000)
        option_df = util.df(bars)
        return option_df["close"].values.tolist()

    def should_trigger_call_selling(self):
        if len(self.price_list_1min) < 2:
            return False
        current_m1 = (self.price_list_1min[-1] - self.price_list_1min[-2]) * self.volume_list_1min[-1]
        current_m2 = (self.price_list_1min[-1] - self.price_list_1min[-2]) * self.volume_list_1min[-1] / self.volume_list_1min[-2]

        should_trigger = self.composite_trigger.execute(
            self.price_list_1min,
            len(self.price_list_1min) - 1,
            current_m1,
            self.max_m1_momentum,
            current_m2,
            self.max_m2_momentum)

        self.max_m1_momentum = max(current_m1, self.max_m1_momentum)
        self.max_m2_momentum = max(current_m2, self.max_m2_momentum)
        return should_trigger

    def should_trigger_call_closing(self, option_contract: Option):
        option_values_last60sec = self.req_1sec_option_data(option_contract)
        if option_values_last60sec is None or len(option_values_last60sec) < 1:
            return False
        closing_price = option_values_last60sec[-1]
        expiration_date = datetime.strptime(option_contract.lastTradeDateOrContractMonth, "%Y%m%d")
        days = (expiration_date - datetime.now()).days
        if closing_price/days < 0.02:
            return True
        return False

    def select_call_option_to_sell(self):
        all_call_contracts = self.get_call_candidates()
        qualified_contract_list = []  # [(contract, price), (), ..()]
        for call_contract in all_call_contracts:
            price_list = self.req_1sec_option_data(call_contract)
            if len(price_list) > 0:
                theta = self.minimum_selling_condition(call_contract, price_list[-1])
                if theta > 0.1:  # safeguard at 0.1 theta; 0.1 USD decay per day
                    qualified_contract_list.append((call_contract, theta))

        if len(qualified_contract_list) == 0:
            return

        sorted_list_of_pair = sorted(qualified_contract_list, key=lambda x: x[1])
        return sorted_list_of_pair[-1][0]

    def get_call_candidates(self):
        initial_strike_price = [50, 55, 60, 65]
        expiration_date_candidates = Affirm.get_next_n_fridays(4)
        assert len(expiration_date_candidates) == 4
        dte_candidate_list = expiration_date_candidates[-2:]
        adjusted_strike_price = [max(init_price, self.price_list_1min[-1] * 1.15) for init_price in
                                 initial_strike_price]

        contract_to_monitor = []
        for strike_price in adjusted_strike_price:
            for expiration_date in dte_candidate_list:
                contract_to_monitor.append(
                    Option(symbol=self.symbol,
                           lastTradeDateOrContractMonth=expiration_date,
                           strike=strike_price,
                           right='C',
                           exchange="SMART",
                           currency="USD")
                )
        return contract_to_monitor

    def minimum_selling_condition(self, input_option: Option, latest_price):
        MINIMUM_THETA = 0.2
        expiration_date = datetime.strptime(input_option.lastTradeDateOrContractMonth, "%Y%m%d")
        dte = (datetime.now() - expiration_date).days
        if latest_price / dte >= MINIMUM_THETA:  # at least 0.2 theta ($1 decay per week)
            return latest_price / dte
        return -1

    # hardcoded strategy; tuned through offline experiment
    @staticmethod
    def generate_composite_trigger_list_for_call_selling():
        composite_trigger_list = []
        price_trigger_list = []
        pt_list = [(1, [1.08, 1.07, 1.06]),
                   (2, [1.08, 1.07, 1.06]),
                   (3, [1.1, 1.09, 1.08, 1.07]),
                   (4, [1.09, 1.08, 1.075]),
                   (5, [1.1, 1.09, 1.08])]

        for i in range(len(pt_list)):
            pair = pt_list[i]
            lb_ctr = pair[0]
            multiplier_list = pair[1]
            for k in range(len(multiplier_list)):
                price_trigger_list.append([PriceBasedTrigger(lb_ctr, multiplier_list[k])])
                composite_trigger_list.append(CompositeTrigger([PriceBasedTrigger(lb_ctr, multiplier_list[k])]))

        # Mixed:
        pt_list_for_combo = [(1, [1.05, 1.04]),
                             (2, [1.06, 1.05, 1.04]),
                             (3, [1.06, 1.05, 1.04]),
                             (4, [1.06, 1.05, 1.04]),
                             (5, [1.06, 1.05, 1.04]),
                             (1, [1.03]), (2, [1.04]), (3, [1.04]), (4, [1.03]), (5, [1.03])
                             ]
        m1_list_for_combo = [2, 1.9, 1.8, 1.7, 1.6, 1.5, 1.4, 1.3, 1.2]
        m2_list_for_combo = [2, 1.9, 1.8, 1.7, 1.6, 1.5, 1.4, 1.3, 1.2]

        price_trigger_combo_list = []
        m1_trigger__combo_list = []
        m2_trigger_combo_list = []

        for i in range(len(pt_list_for_combo)):
            pair = pt_list_for_combo[i]
            lb_ctr = pair[0]
            multiplier_list = pair[1]
            for k in range(len(multiplier_list)):
                price_trigger_combo_list.append(PriceBasedTrigger(lb_ctr, multiplier_list[k]))

        for k in m1_list_for_combo:
            m1_trigger__combo_list.append(MomentumWeightedTrigger(k))

        for q in m2_list_for_combo:
            m2_trigger_combo_list.append(MomentumWeightedTrigger(q, M2))

        mixed_list = []

        for pt_combo in price_trigger_combo_list:
            for m2_combo in m2_trigger_combo_list:
                mixed_list.append([pt_combo, m2_combo])
            for m1_combo in m1_trigger__combo_list:
                mixed_list.append([pt_combo, m1_combo])

        for mixed in mixed_list:
            composite_trigger_list.append(CompositeTrigger(mixed))

        return composite_trigger_list

    @staticmethod
    def get_next_n_fridays(n):
        res_list = []
        d = date.today()
        while len(res_list) < n:
            while d.weekday() != 4:
                d += timedelta(1)
            res_list.append(d.strftime("%Y%m%d"))
            d += timedelta(1)
        return res_list
