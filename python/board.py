from brainflow.board_shim import BrainFlowInputParams, BoardShim, BoardIds
from brainflow.data_filter import DataFilter, FilterTypes, DetrendOperations, NoiseTypes, WindowOperations

from datetime import datetime
import time
import csv
import numpy as np

class Function:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class CytonDaisyBoard:
    def __init__(self, port):
        params = BrainFlowInputParams()
        params.serial_port = port
        self.board = BoardShim(BoardIds.CYTON_DAISY_BOARD, params)
        self.board_id = self.board.get_board_id()
        self.exg_channels = BoardShim.get_exg_channels(self.board_id)
        self.sampling_rate = BoardShim.get_sampling_rate(self.board_id)
        self.update_speed_ms = 50
        self.window_size = 4
        self.num_points = self.window_size * self.sampling_rate
        self.colors = [(128, 129, 130), (123, 74, 141), (57, 90, 161), (49, 113, 89),
                       (220, 174, 5), (254, 97, 55), (255, 56, 44), (162, 81, 48)]

        self.writer = None
        self.totalData = None
        self.real_time = True
        self.reader = None
        self.prevTime = None

    def connect(self, dataFile=None):
        self.totalData = np.zeros(shape=(self.num_points, 32)).tolist()
        if dataFile is None:
            self.real_time = True
            # Creates the file which will contain data produced during the next session
            filename = datetime.now().strftime("%m-%d-%Y_%H:%M:%S.csv")
            file = open(filename, 'a+')
            self.writer = csv.writer(file)  # Instantiates the csv parser

            print("Preparo la sessione...")
            self.board.prepare_session()
            print("Avvio la sessione...")
            self.board.start_stream()
            time.sleep(5)
        else:
            self.real_time = False
            file = open(dataFile, 'r')
            self.reader = csv.reader(file)
            next(self.reader)
            self.prevTime = time.time() * 1000
        return 0

    # Returns a tuple containing the following data in order: wave, fft
    # This function must be called inside a loop
    def read_data(self):
        if self.real_time:
            new_data = self.board.get_board_data(self.num_points)
            if len(new_data[0]) > 0:
                self.filter_data(new_data)
                transposed_new_data = np.transpose(new_data)
                self.save_data(transposed_new_data)
                self.totalData.extend(transposed_new_data)
        else:
            currTime = time.time() * 1000
            passedTime = currTime - self.prevTime
            self.prevTime = currTime
            passedSamples = int(passedTime * self.sampling_rate / 1000)

            # Aggiunge i nuovi dati letti da file alla matrice
            for _ in range(passedSamples):
                try:
                    self.totalData.append(np.array(next(self.reader), dtype="float64"))
                except Exception:
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
            DataFilter.perform_bandpass(data[channel], self.sampling_rate, 3.0, 45.0, 2, FilterTypes.BUTTERWORTH.value,
                                        0)
            DataFilter.perform_bandstop(data[channel], self.sampling_rate, 48.0, 52.0, 2, FilterTypes.BUTTERWORTH.value,
                                        0)
            DataFilter.perform_bandstop(data[channel], self.sampling_rate, 58.0, 62.0, 2, FilterTypes.BUTTERWORTH.value,
                                        0)
            # Rimozione del rumore ambientale
            DataFilter.remove_environmental_noise(data[channel], self.sampling_rate, NoiseTypes.FIFTY.value)

    def get_channel_color(self, ch):
        return self.colors[(ch - 1) % 8]
