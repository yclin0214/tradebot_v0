from transitions import Machine


class States:
    NO_POSITION = "NO_POSITION"
    LONG_SHARE_ONLY = "LONG_SHARE_ONLY"
    ONE_LONG_SHARE_ONE_SHORT_CALL = "ONE_LONG_SHARE_ONE_SHORT_CALL"
    ONE_LONG_SHARE_TWO_SHORT_CALL = "ONE_LONG_SHARE_TWO_SHORT_CALL"
    SHORT_PUT = "SHORT_PUT"


class TradeTransition:
    CLOSE_SHORT_CALL = "CLOSE_SHORT_CALL"
    OPEN_SHORT_CALL = "OPEN_SHORT_CALL"
    CLOSE_DOUBLE_SHORT_CALL = "CLOSE_DOUBLE_SHORT_CALL"
    OPEN_DOUBLE_SHORT_CALL = "OPEN_DOUBLE_SHORT_CALL"


class TradeStateMachine(Machine):
    def __init__(self, model, states, initial_state):
        Machine.__init__(self,
                         model=model,
                         states=states,
                         send_event=True,
                         initial=initial_state,
                         ignore_invalid_triggers=True)
        self.finalize_event = self.finalize
        return

    def finalize(self, event):
        print("finalized")
        return




