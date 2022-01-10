import CoveredCallAbstractModel


class BasicCoveredCallModel(CoveredCallAbstractModel):

    # Todo: to implement the strategy here
    def should_close_short_call(self, event):
        print(event)
        return True

    # Todo: to implement the strategy here
    def should_open_short_call(self, event):
        print(event)
        return True

    def should_open_double_short_calls(self, event):
        return False

    def should_close_double_short_calls(self, event):
        return False