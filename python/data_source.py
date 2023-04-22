class DataSource:
    def __init__(self):
        self.streaming = False

    def start(self):
        self.streaming = True

    def stop(self):
        self.streaming = False

    def read_data(self, samples=1):
        pass

    def is_streaming(self):
        return self.streaming

    def is_finished(self):
        pass
