

class TrendWave:
    def __init__(self, start_value, start_time, prev, is_positive=True):
        self.max_amplitude = start_value
        self.tail_amplitude = start_value
        self.start_time = start_time
        self.end_time = start_time
        self.is_positive = is_positive
        self.is_completed = False
        self.prev_trend_wave = prev
        self.next_trend_wave = None

    def update_trend_wave(self, current_value, current_time):
        if self.is_positive:
            # case 1: go up - continue the trend wave while updating the max_amplitude
            if current_value >= self.max_amplitude:
                self.max_amplitude = current_value
                self.tail_amplitude = current_value
                self.end_time = current_time
            # case 2: less positive but uptick again - finish the current positive trend wave to start a new one
            elif self.tail_amplitude < current_value < self.max_amplitude:
                self.is_completed = True
            # case 3: keep going down, but is still non-negative, continue to update the trend wave
            elif 0 <= current_value <= self.tail_amplitude:
                self.end_time = current_time
                self.tail_amplitude = current_value
            else:
                # current_value < 0
                self.is_completed = True
        else:
            # keep going lower - continue the trend wave while updating the max_amplitude
            if current_value <= self.max_amplitude:
                self.max_amplitude = current_value
                self.tail_amplitude = current_value
                self.end_time = current_time
            # less negative but downtick again - finish the current negative trend wave to start a new one
            elif self.max_amplitude < current_value < self.tail_amplitude:
                self.is_completed = True

            elif self.tail_amplitude <= current_value <= 0:
                self.end_time = current_time
                self.tail_amplitude = current_value
            else:
                # current value > 0
                self.is_completed = True

    def is_current_trend_wave_completed(self):
        return self.is_completed

    def get_max_amplitude(self):
        return self.max_amplitude

    def get_sign(self):
        return self.is_positive

    def get_start_time(self):
        return self.start_time

    def get_end_time(self):
        return self.end_time

    def set_prev_node(self, prev):
        self.prev_trend_wave = prev

    def get_prev_node(self):
        return self.prev_trend_wave

    def set_next_node(self, next_trend_wave):
        self.next_trend_wave = next_trend_wave

    def get_next_node(self):
        return self.next_trend_wave






