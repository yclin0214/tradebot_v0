class TradeStateOutOfSyncException(Exception):
    def __init__(self, message=""):
        super().__init__(message)
        print("Error message: %s" % message)
