



class StrategyLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def convert_file_into_params_map(self, file_path):
        if file_path is None or len(file_path) == 0:
            return {}
        # Todo: this will return {
        #  afrm: [{EMA20: xxx, EMA50: xxx, contract_type: stock/option,
        #  position_intent: long/short, quantity: xxx, min_delta: xxx, min_theta: xxx,
        #  max_delta: xxx, max_theta: xxx, priority: xxx}, ..., {...}], pd: [...], ...}
        return {}
