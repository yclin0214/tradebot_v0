from TradeStateMachine import *


class StrategySimulation:
    def __init__(self, strategy_model, state_machine: TradeStateMachine,
                 report_generator, datasets):
        self.strategy_model = strategy_model
        self.state_machine = state_machine
        self.datasets = datasets
        self.report_generator = report_generator

    def run(self):
        pass

    def generate_report(self):
        pass
