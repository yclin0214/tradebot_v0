from dataclasses import dataclass
import ContractType
import PositionType
import datetime


@dataclass
class ActiveTrade:
    ticker_name: str
    order_id: str
    contract_type: ContractType
    position_type: PositionType
    prev_share_price: float
    cur_share_price: float
    prev_bid: float
    prev_ask: float
    prev_offer: float
    prev_offer_timestamp: datetime.date
    cur_offer: float
    cur_offer_list: list
    prev_bid_change_timestamp: datetime.datetime
    prev_ask_change_timestamp: datetime.datetime
    cur_offer_timestamp: datetime.datetime

    def set_prev_offer(self, prev_offer):
        self.prev_offer = prev_offer
        return

    def set_prev_offer_timestamp(self, prev_offer_timestamp):
        self.prev_offer_timestamp = prev_offer_timestamp
        return

    def set_prev_bid(self, prev_bid):
        self.prev_bid = prev_bid
        return

    def set_prev_ask(self, prev_ask):
        self.prev_ask = prev_ask
        return

    def set_prev_share_price(self, prev_share_price):
        self.prev_share_price = prev_share_price
        return

    def set_prev_bid_change_timestamp(self, prev_bid_change_timestamp):
        self.prev_bid_change_timestamp = prev_bid_change_timestamp
        return

    def set_prev_ask_change_timestamp(self, prev_ask_change_timestamp):
        self.prev_ask_change_timestamp = prev_ask_change_timestamp
        return

    def get_ticker_name(self):
        return self.ticker_name

    def get_order_id(self):
        return self.order_id

    def get_contract_type(self):
        return self.contract_type

    def get_position_type(self):
        return self.position_type

    def get_prev_share_price(self):
        return self.prev_share_price

    def get_cur_share_price(self):
        return self.cur_share_price

    def get_prev_bid(self):
        return self.prev_bid

    def get_prev_ask(self):
        return self.prev_ask

    def get_prev_offer(self):
        return self.prev_offer

    def get_cur_offer(self):
        return self.cur_offer

    def get_cur_offer_list(self):
        return self.cur_offer_list

    def get_prev_bid_change_timestamp(self):
        return self.prev_bid_change_timestamp

    def get_prev_ask_change_timestamp(self):
        return self.prev_ask_change_timestamp

    def get_prev_offer_timestamp(self):
        return self.prev_offer_timestamp

    def get_cur_offer_timestamp(self):
        return self.cur_offer_timestamp
