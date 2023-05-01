import threading

import numpy as np

from brainflow.board_shim import BrainFlowInputParams, BoardShim, BrainFlowError
from log_manager import DataLogger
from data_source import DataSource

# Global variables
base_impedance_ohms = 2200
drive_amps = 6.0e-9
default_gain = 24
colors = [(128, 129, 130), (123, 74, 141), (57, 90, 161), (49, 113, 89),
          (220, 174, 5), (254, 97, 55), (255, 56, 44), (162, 81, 48)]

channel_ids = ['1', '2', '3', '4', '5', '6', '7', '8', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I']
turn_off_commands = ['1', '2', '3', '4', '5', '6', '7', '8', 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i']
turn_on_commands = ['!', '@', '#', '$', '%', '^', '&', '*', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I']

exg_channels = range(1, 17)
ecg_channels = range(9, 12)


class Board(DataSource):
    def __init__(self, board_type, port, output_folder):
        super().__init__()

        # Initialize board object
        params = BrainFlowInputParams()
        params.serial_port = port
        self.board = BoardShim(board_type, params)
        self.board_id = self.board.get_board_id()
        self.logger = DataLogger(output_folder)

        # Start streaming session
        try:
            print("Preparo la sessione...")
            self.board.prepare_session()
        except BrainFlowError:
            raise

    def start(self, save_logs=True):
        if not self.streaming:
            print("Starting stream...")
            self.board.start_stream()
            if save_logs:
                self.logger.create_new_record(self, exg_channels)
            super().start()

    def stop(self):
        if self.streaming:
            print("Stopping stream...")
            self.board.stop_stream()
            self.logger.close()
            super().stop()

    def read_data(self, samples=1):
        try:
            data = np.transpose(self.board.get_board_data(samples))
            self.logger.write_data(data)
            return data
        except BrainFlowError:
            return np.array([])

    def toggle_impedance_checking(self, channel, active):
        if channel is None:
            return

        n = 1 if active else 0
        full_command = f"x{channel_ids[channel-1]}0{(1-n)*6}0{n}00X"
        full_command += f"z{channel_ids[channel-1]}0{n}Z"
        self.send_command(full_command)

    def toggle_channel(self, channel, active):
        if active:
            command = turn_on_commands[channel-1]
        else:
            command = turn_off_commands[channel-1]

        thread = threading.Thread(target=self.send_command, args=(command,))
        thread.start()

    def send_command(self, command):
        try:
            self.board.config_board(command)
            print(f"Sent command: {command}")
        except BrainFlowError:
            print(f"Sending command {command} failed!")
        except UnicodeDecodeError:
            pass

    def is_finished(self):
        return False

    @classmethod
    def get_channel_color(cls, ch):
        return colors[(ch - 1) % 8]
