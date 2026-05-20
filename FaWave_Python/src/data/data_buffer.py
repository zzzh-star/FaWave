from collections import deque

class DataBuffer:
    def __init__(self, max_points=2000):
        self.max_points = max_points
        self.clear()

    def clear(self):
        self.time_data = deque(maxlen=self.max_points)
        self.index_data = deque(maxlen=self.max_points)
        self.ch1_data = deque(maxlen=self.max_points)
        self.ch2_data = deque(maxlen=self.max_points)
        self.ch3_data = deque(maxlen=self.max_points)
        self.ch4_data = deque(maxlen=self.max_points)

        self.fx_data = deque(maxlen=self.max_points)
        self.fy_data = deque(maxlen=self.max_points)
        self.fz_data = deque(maxlen=self.max_points)

    def add_point(self, rel_time, sample_index, ch1, ch2, ch3, ch4, fx=0.0, fy=0.0, fz=0.0):
        self.time_data.append(rel_time)
        self.index_data.append(sample_index)
        self.ch1_data.append(ch1)
        self.ch2_data.append(ch2)
        self.ch3_data.append(ch3)
        self.ch4_data.append(ch4)

        self.fx_data.append(fx)
        self.fy_data.append(fy)
        self.fz_data.append(fz)

    def get_data(self):
        return (
            list(self.time_data),
            list(self.index_data),
            list(self.ch1_data),
            list(self.ch2_data),
            list(self.ch3_data),
            list(self.ch4_data),
            list(self.fx_data),
            list(self.fy_data),
            list(self.fz_data),
        )
