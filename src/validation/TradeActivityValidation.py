# Validate fully hedge status - 1 long share can be at most mapped to 1 short call
# Validate the order status - open, filled, partially filled; order status should be subject to fully hedge validation
# Margin status: todo maximum usable margin
from ib_insync import *


class TradeActivityValidation:
    def __init__(self, ib_client: IB):
        self.ib = ib_client

    def get_num_of_call_options_to_sell(self, ticker):
        # pending or filled order
        total_shares_count = 0
        pending_call_options_count = 0
        filled_call_options_count = 0

        if self.is_open_trade_state_stabilized() is False:
            return 0
        open_trades = self.reconcile_open_trades()
        current_positions = self.ib.positions()
        # always check for the pending order first. It's safer to over-count rather than under-count for short positions
        for openTrade in open_trades:
            if isinstance(openTrade.contract, Option) and openTrade.contract.symbol == ticker:
                order_action = openTrade.order.action
                open_short_position = openTrade.orderStatus.remaining
                if order_action == 'SELL':
                    print("It's SHORT CALLS")
                    pending_call_options_count -= open_short_position
                    print("open short positions: %s" % pending_call_options_count)
        for position in current_positions:
            current_contract = position.contract
            if isinstance(current_contract, Stock) and current_contract.symbol == ticker:
                total_shares_count += position.position
                print("current share position: %s" % total_shares_count)
            elif isinstance(current_contract, Option) and current_contract.symbol == ticker:
                filled_call_options_count += position.position
                print("filled option positions: %s" % filled_call_options_count)

        return round(total_shares_count/100) + filled_call_options_count + pending_call_options_count

    # IB api has delay in achieving order state consistency
    # An order is often submitted but is not shown through the openTrades() api after some delay
    # In that case, reqAllOpenOrders() will return more entries compared to openTrades(), and we have to wait
    def is_open_trade_state_stabilized(self):
        open_trades = self.ib.openTrades()
        all_open_orders = self.ib.reqAllOpenOrders()
        if len(open_trades) < len(all_open_orders):
            return False
        return True

    # If an order is cancelled through an IB app, the openTrades() state may not be consistent.
    # In this case, we perform the pruning
    def reconcile_open_trades(self):
        open_trades = self.ib.openTrades()
        all_open_orders = self.ib.reqAllOpenOrders()
        if len(open_trades) > len(all_open_orders):
            reference_perm_ids = [open_order.permId for open_order in all_open_orders]
            reconciled_open_trades = [trade for trade in open_trades if trade.order.permId in reference_perm_ids]
            return reconciled_open_trades
        return open_trades
