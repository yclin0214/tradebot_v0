from src.validation import TradeActivityValidation
from src.data import ActiveTrade
from src.requests import BlockingRequestsProxy

from ib_insync import *


class TradeActivityManager:
    def __init__(self, active_trade_validator: TradeActivityValidation,
                 blk_req_proxy: BlockingRequestsProxy, open_trade_map=None):
        if open_trade_map is None:
            open_trade_map = {}
        self.open_trade_map = open_trade_map  # ticker -> trade_id
        self.active_trade_validator = active_trade_validator
        self.blk_req_proxy = blk_req_proxy

    # Todo: decide how to read the open trades and initialize the open_trade_map
    def load_open_trades(self):
        pass

    # Todo: logic to update the open_trade_map
    # Only persist into db when it's submitted or cancelled
    # For all the other states (pre-submit, etc), we just need to make sure the local hash_map is updated
    def check_order_update_status(self, trade: Trade):
        pass

    def get_open_trade(self, ticker_to_get: str):
        if ticker_to_get not in self.open_trade_map:
            return []
        return self.open_trade_map[ticker_to_get]

    # Todo: decide whether or not to sync with db
    def add_open_trade(self, open_trade: ActiveTrade):
        ticker_to_add = open_trade.get_ticker_name()
        if ticker_to_add not in self.open_trade_map:
            self.open_trade_map[ticker_to_add] = []
        self.open_trade_map[ticker_to_add].append(open_trade)
        return

    # Todo: implement logic to call IB and refresh the open order status

    def remove_open_trade(self, ticker_to_update: str, trade_to_remove: ActiveTrade):
        pass

    def reconcile_open_trades(self, ticker_to_reconcile: str):
        # todo: throw exception if there's no match
        # upon receiving the exception, the ib_insync client need to restart
        open_trades_list = self.active_trade_validator.reconcile_open_trades()

        pass

    def open_trade_payload_validation(self, open_trade: ActiveTrade):
        pass

    def decorate_new_open_trade(self, prev_trade: ActiveTrade, cur_trade: ActiveTrade):

        cur_trade.set_prev_bid(prev_trade.get_prev_bid())
        cur_trade.set_prev_ask(prev_trade.get)
        cur_trade.set_prev_share_price(prev_trade.get_cur_share_price())
        cur_trade.set_prev_offer(prev_trade.get_cur_offer())

        cur_trade.set_prev_offer_timestamp()
        cur_trade.set_prev_bid_change_timestamp()
        cur_trade.set_prev_ask_change_timestamp()

        return cur_trade
