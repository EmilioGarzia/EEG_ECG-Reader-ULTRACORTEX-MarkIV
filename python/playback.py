from log_manager import LogParser
import numpy as np


class PlaybackManager:
    def __init__(self, file_path):
        self.file_path = file_path
        self.parser = None
        self.board_id = None
        self.begin()

    def begin(self):
        self.parser = LogParser(self.file_path)
        info = self.parser.begin()
        self.board_id = int(info[0])

    def read_data(self, samples):
        return np.multiply(self.parser.read_data(samples), 24)

    def is_finished(self):
        return not self.parser.has_new_data

    def reset(self):
        self.parser.close()
        self.begin()
