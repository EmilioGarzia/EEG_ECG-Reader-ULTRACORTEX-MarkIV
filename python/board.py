import numpy as np

from brainflow.board_shim import BrainFlowInputParams, BoardShim, BrainFlowError
from log_manager import DataLogger

# Global variables
base_impedance_ohms = 2200
drive_amps = 6.0e-9
default_gain = 24
colors = [(128, 129, 130), (123, 74, 141), (57, 90, 161), (49, 113, 89),
          (220, 174, 5), (254, 97, 55), (255, 56, 44), (162, 81, 48)]
channel_ids = [f'{ch}' for ch in range(1, 9)]
channel_ids.extend(['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I'])

exg_channels = range(1, 17)
ecg_channels = range(9, 12)


class Board:
    def __init__(self, board_type, port, output_folder):
        # Initialize board object
        params = BrainFlowInputParams()
        params.serial_port = port
        self.board = BoardShim(board_type, params)
        self.board_id = self.board.get_board_id()
        self.streaming = False

        # Initialize data logger
        self.logger = DataLogger(output_folder)

        # Start streaming session
        try:
            print("Preparo la sessione...")
            self.board.prepare_session()
        except BrainFlowError:
            raise

    def start_stream(self):
        if not self.streaming:
            print("Avvio lo stream...")
            self.board.start_stream()
            self.logger.create_new_record(self, exg_channels)
            self.streaming = True

    def stop_stream(self):
        if self.streaming:
            print("Fermo lo stream...")
            self.board.stop_stream()
            self.logger.close()
            self.streaming = False

    def read_data(self, samples=1, gain=default_gain):
        try:
            data = np.transpose(np.multiply(self.board.get_board_data(samples), gain))
            self.logger.write_data(data)
            return data
        except BrainFlowError:
            return np.array([])

    def toggle_impedance_checking(self, channel, active):
        if channel is None:
            return

        n = '1' if active else '0'
        full_command = f"x{channel_ids[channel-1]}000{n}00X"
        full_command += f"z{channel_ids[channel-1]}0{n}Z"
        try:
            self.board.config_board(full_command)
            print(f"Il comando {full_command} è stato inviato con successo!")
        except BrainFlowError:
            print(f"Non è stato possibile inviare il comando: {full_command}!")
        except UnicodeDecodeError:
            print("Problema!")

    def is_finished(self):
        return False

    @classmethod
    def get_channel_color(cls, ch):
        return colors[(ch - 1) % 8]
