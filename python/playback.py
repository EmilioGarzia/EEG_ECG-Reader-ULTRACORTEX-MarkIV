from log_manager import LogParser
from data_source import DataSource


class PlaybackManager(DataSource):
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.parser = LogParser(self.file_path)
        self.board_id = None

    def start(self):
        if not self.streaming:
            info = self.parser.begin()
            self.board_id = int(info[0])
            super().start()

    def stop(self):
        if self.streaming:
            super().stop()
            self.parser.close()

    def read_data(self, samples=1):
        return self.parser.read_data(samples)

    def is_finished(self):
        return not self.parser.has_new_data
