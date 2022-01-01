from ib_insync import *

# This class is responsible for making all the necessary proxy call to get
# whatever data is needed. All the calls are blocking call


class BlockingRequestsProxy:
    def __init__(self, ib_client: IB):
        self.ib_client = ib_client

    # get open order
    def get_open_orders(self):
        pass

    def get_current_positions(self):
        pass


