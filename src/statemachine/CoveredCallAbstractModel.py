from abc import ABC, abstractmethod
from TradeStateMachine import *


# This class is to be overwritten by child class for the conditional transition functions
class CoveredCallAbstractModel(ABC):
    def __init__(self, parameter_config):
        self.parameter_config = parameter_config
        self._register_state_machine_callback()

    # Todo: register all the necessary callbacks and initialization to the state machine
    def _register_state_machine_callback(self):
        self.state_machine = TradeStateMachine(model=self,
                                               states=[States.LONG_SHARE_ONLY,
                                                       States.ONE_LONG_SHARE_ONE_SHORT_CALL,
                                                       States.ONE_LONG_SHARE_TWO_SHORT_CALL],
                                               initial_state=States.LONG_SHARE_ONLY)
        # add state transitions logic
        self.state_machine.add_transition(trigger=TradeTransition.OPEN_SHORT_CALL,
                                          source=States.LONG_SHARE_ONLY,
                                          dest=States.ONE_LONG_SHARE_ONE_SHORT_CALL,
                                          conditions="should_open_short_call")

        self.state_machine.add_transition(trigger=TradeTransition.CLOSE_SHORT_CALL,
                                          source=States.ONE_LONG_SHARE_ONE_SHORT_CALL,
                                          dest=States.LONG_SHARE_ONLY,
                                          conditions="should_close_short_call")

        self.state_machine.add_transition(trigger=TradeTransition.OPEN_DOUBLE_SHORT_CALL,
                                          source=States.ONE_LONG_SHARE_ONE_SHORT_CALL,
                                          dest=States.ONE_LONG_SHARE_TWO_SHORT_CALL,
                                          conditions="should_open_double_short_calls")

        self.state_machine.add_transition(trigger=TradeTransition.CLOSE_DOUBLE_SHORT_CALL,
                                          source=States.ONE_LONG_SHARE_TWO_SHORT_CALL,
                                          dest=States.ONE_LONG_SHARE_ONE_SHORT_CALL,
                                          conditions="should_close_double_short_calls")

        return

    def dispatch(self, trigger):
        self.state_machine.dispatch(trigger)
        return

    @abstractmethod
    def should_close_short_call(self, event):
        pass

    @abstractmethod
    def should_open_short_call(self, event):
        pass

    @abstractmethod
    def should_open_double_short_calls(self, event):
        pass

    @abstractmethod
    def should_close_double_short_calls(self, event):
        pass
