import time
import numpy as np

from brainflow.board_shim import BrainFlowInputParams, BoardShim, BrainFlowError
from log_manager import DataLogger

# Global variables
base_impedance_ohms = 2200
drive_amps = 6.0e-9
colors = [(128, 129, 130), (123, 74, 141), (57, 90, 161), (49, 113, 89),
          (220, 174, 5), (254, 97, 55), (255, 56, 44), (162, 81, 48)]
channel_ids = [f'{ch}' for ch in (range(1, 10), 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I')]


class Board:
    def __init__(self, board_type, port, output_folder):
        # Initialize board object
        params = BrainFlowInputParams()
        params.serial_port = port
        self.board = BoardShim(board_type, params)
        self.board_id = self.board.get_board_id()
        self.imp_checking_channel = None

        # Initialize data logger
        self.logger = DataLogger(output_folder)

        # Start streaming session
        print("Preparo la sessione...")
        self.board.prepare_session()
        print("Avvio la sessione...")
        self.board.start_stream()
        time.sleep(5)

    def read_data(self, samples=1):
        try:
            return np.transpose(np.multiply(self.board.get_board_data(samples), 24))
        except BrainFlowError:
            print(samples)
            return np.array([])

    def toggle_impedance_checking(self, channel):
        if self.imp_checking_channel is None or channel is None:
            return

        n = '1'
        if self.imp_checking_channel == channel:
            n = '0'
        else:
            self.toggle_impedance_checking(self.imp_checking_channel)
        self.board.config_board(f"z{channel_ids[channel]}0{n}Z")
        # TODO: Manage command execution fail

    def is_finished(self):
        return False

    @classmethod
    def get_channel_color(cls, ch):
        return colors[(ch - 1) % 8]
