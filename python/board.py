import os

from brainflow.board_shim import BrainFlowInputParams, BoardShim, BoardIds
from brainflow.data_filter import DataFilter, FilterTypes, DetrendOperations, NoiseTypes, WindowOperations
from datetime import datetime
import time
import csv
import numpy as np

from graph import Function

# Supported types of boards
type_of_board = {
    "CYTON DAISY BOARD [16CH]": BoardIds.CYTON_DAISY_BOARD,
    "CYTON BOARD [8CH]": BoardIds.CYTON_BOARD,
    "CYTON DAISY WIFI BOARD [16CH]": BoardIds.CYTON_DAISY_WIFI_BOARD,
    "CYTON WIFI BOARD [8CH]": BoardIds.CYTON_WIFI_BOARD,
    "GANGLION BOARD": BoardIds.GANGLION_BOARD,
    "GANGLION WIFI BOARD": BoardIds.GANGLION_WIFI_BOARD
}


class Board:
    def __init__(self):
        self.board = None
        self.exg_channels = None
        self.sampling_rate = 125
        self.update_speed_ms = 50
        self.window_size = 4
        self.num_points = self.calculate_points_number()
        self.colors = [(128, 129, 130), (123, 74, 141), (57, 90, 161), (49, 113, 89),
                       (220, 174, 5), (254, 97, 55), (255, 56, 44), (162, 81, 48)]

        self.totalData = None
        self.writer = None
        self.real_time = True
        self.input_file = None
        self.reader = None

    def calculate_points_number(self):
        return self.window_size * self.sampling_rate

    def begin_capturing(self, board_type, port, output_folder=""):
        self.real_time = True
        global type_of_board
        params = BrainFlowInputParams()
        params.serial_port = port
        self.board = BoardShim(board_type, params)
        board_id = self.board.get_board_id()
        self.exg_channels = BoardShim.get_exg_channels(board_id)
        self.sampling_rate = BoardShim.get_sampling_rate(board_id)
        self.num_points = self.calculate_points_number()

        files = os.listdir(output_folder)
        if "metadata.csv" in files:
            filename = str(len(files))
        else:
            filename = str(len(files)+1)
        output_file = output_folder + filename + ".csv"
        file = open(output_file, 'a+')
        self.writer = csv.writer(file)  # Instantiates the csv parser
        self.writer.writerow([self.exg_channels[0], self.exg_channels[-1]])

        print("Preparo la sessione...")
        self.totalData = None
        self.board.prepare_session()
        print("Avvio la sessione...")
        self.board.start_stream()
        time.sleep(5)

    def playback(self, input_file_path):
        self.real_time = False
        self.input_file = open(input_file_path, 'r')
        self.reader = csv.reader(self.input_file)
        header = next(self.reader)
        self.exg_channels = range(int(header[0]), int(header[1])+1)
        self.totalData = None

    def resetPlayback(self):
        if not self.real_time:
            path = self.input_file.name
            self.input_file.close()
            self.playback(path)

    # Returns a tuple containing the following data in order: wave, fft
    # This function must be called inside a loop
    def read_data(self):
        if self.real_time:
            new_data = self.board.get_board_data(self.num_points)
            if self.totalData is None:
                self.totalData = list(np.zeros(shape=(self.num_points, len(new_data))))

            if len(new_data[0]) > 0:
                self.filter_data(new_data)
                transposed_new_data = np.transpose(new_data)
                self.save_data(transposed_new_data)
                self.totalData.extend(transposed_new_data)
        else:
            # Aggiunge i nuovi dati letti da file alla matrice
            try:
                row = next(self.reader)
                if self.totalData is None:
                    self.totalData = list(np.zeros(shape=(self.num_points, len(row))))
                self.totalData.append(np.array(row, dtype="float64"))
            except StopIteration:
                return None, None

        self.totalData = self.clip_data(self.totalData)
        data = np.transpose(self.totalData)
        return self.parse_data(data)

    def clip_data(self, data):
        data_size = len(data)
        if data_size > self.num_points:
            toRemove = data_size - self.num_points
            return data[toRemove:]
        return data

    def parse_data(self, data):
        wave = []
        fft = []
        for count, channel in enumerate(self.exg_channels):
            scd = np.array(data[channel])
            wave.append(Function(range(-len(scd), 0), scd.tolist()))
            # Calcola la trasformata di Fourier per ottenere le frequenze del segnale
            amp, freq = DataFilter.get_psd(scd, self.sampling_rate, WindowOperations.NO_WINDOW.value)
            fft.append(Function(freq, amp))
        return wave, fft

    # This function must be called inside a loop
    def save_data(self, data):
        for arr in data:
            self.writer.writerow(arr)

    def filter_data(self, data):
        for _, channel in enumerate(self.exg_channels):
            DataFilter.detrend(data[channel], DetrendOperations.CONSTANT.value)
            DataFilter.perform_bandpass(data[channel], self.sampling_rate, 3.0, 45.0, 2,
                                        FilterTypes.BUTTERWORTH.value, 0)
            DataFilter.perform_bandstop(data[channel], self.sampling_rate, 48.0, 52.0, 2,
                                        FilterTypes.BUTTERWORTH.value, 0)
            DataFilter.perform_bandstop(data[channel], self.sampling_rate, 58.0, 62.0, 2,
                                        FilterTypes.BUTTERWORTH.value, 0)
            # Rimozione del rumore ambientale
            DataFilter.remove_environmental_noise(data[channel], self.sampling_rate, NoiseTypes.FIFTY.value)

    def get_channel_color(self, ch):
        return self.colors[(ch - 1) % 8]
