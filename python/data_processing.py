import math

import numpy as np
import time

from brainflow.board_shim import BoardShim, BrainFlowError
from brainflow.data_filter import DataFilter, DetrendOperations, FilterTypes, NoiseTypes, WindowOperations

from graph import Function
from playback import PlaybackManager
from board import base_impedance_ohms, drive_amps


class DataProcessing:
    def __init__(self):
        self.speed = 1
        self.window_size = 4
        self.data_source = None
        self.total_data = None
        self.sampling_rate = None
        self.num_points = None
        self.prev_time = None

    def start_session(self, data_source):
        self.data_source = data_source
        self.sampling_rate = BoardShim.get_sampling_rate(data_source.board_id)
        self.num_points = self.sampling_rate*self.window_size
        self.prev_time = None

    def reset(self):
        if self.data_source is not None and isinstance(self.data_source, PlaybackManager):
            self.data_source.reset()
            self.total_data = None
            self.start_session(self.data_source)

    def forward(self):
        if self.data_source is None:
            return None, None

        samples = self.get_unprocessed_samples()
        new_data = self.data_source.read_data(samples)
        if len(new_data) == 0:
            return None, None

        if self.total_data is None:
            self.total_data = list(np.zeros(shape=(self.num_points, len(new_data[0]))))
        self.total_data.extend(new_data)
        self.clip_data()

        # Process data and return obtained functions
        impedance = []
        wave = []
        fft = []
        data = np.transpose(self.total_data)
        exg_channels = BoardShim.get_exg_channels(self.data_source.board_id)
        for i, channel in enumerate(exg_channels):
            channel_data = np.array(data[channel])
            impedance.append(calculate_impedance(channel_data))
            self.filter_channel(channel_data)
            wave.append(Function(np.linspace(-self.window_size, 0, self.num_points), channel_data))
            amp, freq = self.psd(channel_data)
            fft.append(Function(freq, amp))
        return impedance, wave, fft

    def filter_channel(self, channel_data):
        DataFilter.detrend(channel_data, DetrendOperations.CONSTANT.value)
        DataFilter.perform_bandpass(channel_data, self.sampling_rate, 3.0, 45.0, 2, FilterTypes.BUTTERWORTH.value, 0)
        DataFilter.perform_bandstop(channel_data, self.sampling_rate, 48.0, 52.0, 2, FilterTypes.BUTTERWORTH.value, 0)
        DataFilter.perform_bandstop(channel_data, self.sampling_rate, 58.0, 62.0, 2, FilterTypes.BUTTERWORTH.value, 0)
        # DataFilter.perform_bandpass(filtered_data, sampling_rate, 27.5, 45.0, 4, FilterTypes.BUTTERWORTH.value, 0)
        # Environmental noise cancellation
        DataFilter.remove_environmental_noise(channel_data, self.sampling_rate, NoiseTypes.FIFTY_AND_SIXTY.value)

    # Calculates Power Spectrum Density
    def psd(self, channel_data):
        nfft = DataFilter.get_nearest_power_of_two(self.sampling_rate)
        overlap = int(0.75*nfft)
        improvedData = channel_data[-nfft-1:-1]
        improvedData = np.subtract(improvedData, np.average(improvedData))
        return DataFilter.get_psd_welch(improvedData, nfft, overlap, self.sampling_rate, WindowOperations.HAMMING.value)

    def clip_data(self):
        data_length = len(self.total_data)
        if data_length > self.num_points:
            slice_size = data_length-self.num_points
            self.total_data = self.total_data[slice_size:]

    def get_unprocessed_samples(self):
        if self.prev_time is None:
            self.prev_time = get_time()
            return 0

        curr_time = get_time()
        passed_time = curr_time-self.prev_time
        self.prev_time = curr_time
        time_per_sample = 1000/(self.sampling_rate*self.speed)
        return int(passed_time/time_per_sample)

    def get_exg_channels(self):
        try:
            return BoardShim.get_exg_channels(self.data_source.board_id)
        except BrainFlowError or AttributeError:
            return range(1, 17)

    def get_ecg_channels(self):
        return range(9, 12)


def calculate_impedance(channel_data):
    impedance = (math.sqrt(2)*DataFilter.calc_stddev(channel_data)*1.0E-6)/drive_amps
    impedance -= base_impedance_ohms
    if impedance < 0:
        impedance = 0
    return impedance


def get_time():
    return time.time()*1000
