import time
import numpy as np

from brainflow.board_shim import BrainFlowInputParams, BoardShim, BrainFlowError
from log_manager import DataLogger

# Global variables
base_impedance_ohms = 2200
drive_amps = 6.0e-9
colors = [(128, 129, 130), (123, 74, 141), (57, 90, 161), (49, 113, 89),
          (220, 174, 5), (254, 97, 55), (255, 56, 44), (162, 81, 48)]


class Board:
    def __init__(self, board_type, port, output_folder):
        # Initialize board object
        params = BrainFlowInputParams()
        params.serial_port = port
        self.board = BoardShim(board_type, params)
        self.board_id = self.board.get_board_id()

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
            return np.transpose(np.multiply(self.board.get_current_board_data(samples), 24))
        except BrainFlowError:
            print(samples)
            return np.array([])

    def is_finished(self):
        return False

    @classmethod
    def get_channel_color(cls, ch):
        return colors[(ch - 1) % 8]
