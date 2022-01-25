NEUTRAL_TREND = 0
INCREASING_TREND = 1
DECREASING_TREND = -1


class Trend:
    def __init__(self, end_amplitude, start_time, end_time, trend=NEUTRAL_TREND):
        self.start_amplitude = end_amplitude
        self.amplitude_list = [end_amplitude]
        self.end_amplitude = end_amplitude
        self.start_time = start_time
        self.end_time = end_time
        self.trend = trend

    def get_amplitude_list(self):
        return self.amplitude_list

    def add_to_amplitude_list(self, amplitude):
        return self.amplitude_list.append(amplitude)

    def get_start_amplitude(self):
        return self.start_amplitude

    def get_end_amplitude(self):
        return self.end_amplitude

    def get_start_time(self):
        return self.start_time

    def get_end_time(self):
        return self.end_time

    def get_trend(self):
        return self.trend

    def set_start_amplitude(self, amplitude):
        self.start_amplitude = amplitude

    def set_end_amplitude(self, amplitude):
        self.end_amplitude = amplitude

    def set_end_time(self, time):
        self.end_time = time

    def set_start_time(self, time):
        self.start_time = time

    def set_trend(self, trend):
        self.trend = trend
