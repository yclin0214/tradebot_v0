from ib_insync import *


class AccountPositionManager:

    def __init__(self, ib_client: IB):
        self.account_position_map = {}  # ticker -> position_type -> count
        self.ib_client = ib_client
        return

    # Todo: Important -- might need to think about the synchronization mechanism
    def request_current_account_position(self):
        positions = self.ib_client.positions()
        for position_entry in positions:
            position_contract = position_entry.contract
            position_count = position_entry.position
            position_ticker = position_contract.symbol
            if position_ticker not in self.account_position_map:
                self.account_position_map[position_ticker] = []
            self.account_position_map[position_ticker].append((position_contract, position_count))
        return

    def get_ticker_position(self, ticker_symbol: str):
        if ticker_symbol in self.account_position_map:
            return self.account_position_map[ticker_symbol]
        return []

    def get_net_position_for_ticker(self, ticker_symbol: str):
        if ticker_symbol not in self.account_position_map:
            return 0
        if len(self.account_position_map[ticker_symbol]) == 0:
            return 0
        contract_list = self.account_position_map[ticker_symbol]
        net_position = 0
        # positive -> long shares/short put; negative -> short shares/short call
        for contract_position_pair in contract_list:
            # Todo: check the length of the pair. Make sure it's 2
            contract_for_position = contract_position_pair[0]
            position_count = contract_position_pair[1]
            if isinstance(contract_for_position, Stock):
                net_position += position_count
            elif isinstance(contract_for_position, Option):
                if contract_for_position.right == 'C':
                    net_position += float(contract_for_position.multiplier) * position_count
                elif contract_for_position.right == 'P':
                    net_position -= float(contract_for_position.multiplier) * position_count
        return net_position

    def get_stock_only_position_for_ticker(self, ticker_symbol: str):
        if ticker_symbol not in self.account_position_map:
            return 0
        if len(self.account_position_map[ticker_symbol]) == 0:
            return 0

        contract_list = self.account_position_map[ticker_symbol]
        net_position = 0
        for contract_position_pair in contract_list:
            # Todo: check the length of the pair. Make sure it's 2
            contract_for_position = contract_position_pair[0]
            position_count = contract_position_pair[1]
            if isinstance(contract_for_position, Stock):
                net_position += position_count
        return net_position

    def get_put_only_position_for_ticker(self, ticker_symbol: str):
        if ticker_symbol not in self.account_position_map:
            return 0
        if len(self.account_position_map[ticker_symbol]) == 0:
            return 0

        contract_list = self.account_position_map[ticker_symbol]
        net_position = 0
        for contract_position_pair in contract_list:
            # Todo: check the length of the pair. Make sure it's 2
            contract_for_position = contract_position_pair[0]
            position_count = contract_position_pair[1]
            if isinstance(contract_for_position, Option):
                if contract_for_position.right == 'P':
                    net_position -= float(contract_for_position.multiplier) * position_count
        return net_position

    def get_call_only_position_for_ticker(self, ticker_symbol: str):
        if ticker_symbol not in self.account_position_map:
            return 0
        if len(self.account_position_map[ticker_symbol]) == 0:
            return 0

        contract_list = self.account_position_map[ticker_symbol]
        net_position = 0
        for contract_position_pair in contract_list:
            # Todo: check the length of the pair. Make sure it's 2
            contract_for_position = contract_position_pair[0]
            position_count = contract_position_pair[1]
            if isinstance(contract_for_position, Option):
                if contract_for_position.right == 'C':
                    net_position += float(contract_for_position.multiplier) * position_count
        return net_position
