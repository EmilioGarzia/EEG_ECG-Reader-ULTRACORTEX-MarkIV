import math
import time

from brainflow.data_filter import DataFilter, FilterTypes, NoiseTypes, WindowOperations

from graph import Function
from board import *

extra_window = 2
overlap_percentage = 0.75


class DataProcessing:
    def __init__(self, data_source, gain=default_gain):
        self.data_source = data_source
        self.gain = gain
        self.speed = 1
        self.window_size = 4
        self.total_data = None
        self.sampling_rate = None
        self.num_points = None
        self.total_points = None
        self.unprocessed_time = None
        self.prev_time = None

    def start(self):
        if isinstance(self.data_source, Board):
            self.data_source.start_stream()
        else:
            self.data_source.begin()
        self.sampling_rate = BoardShim.get_sampling_rate(self.data_source.board_id)
        self.num_points = self.sampling_rate*self.window_size
        self.total_points = self.num_points+extra_window*self.sampling_rate
        self.unprocessed_time = None
        self.prev_time = None

    def stop(self):
        if isinstance(self.data_source, Board):
            self.data_source.stop_stream()
        else:
            self.data_source.reset()
        self.total_data = None

    def forward(self):
        if self.data_source is None:
            return None, None, None

        samples = self.get_unprocessed_samples()
        if samples == 0:
            return None, None, None

        new_data = self.data_source.read_data(samples, self.gain)
        if len(new_data) == 0:
            return None, None, None

        if self.total_data is None:
            self.total_data = list(np.zeros(shape=(self.total_points, len(new_data[0]))))
        self.total_data.extend(new_data)
        self.clip_data()

        # Process data and return obtained functions
        impedance = []
        wave = []
        fft = []
        data = np.transpose(self.total_data)
        offset = self.sampling_rate*extra_window
        for i, channel in enumerate(exg_channels):
            channel_data = np.array(data[channel])
            self.filter_channel(channel_data)
            channel_data = channel_data[offset-1:-1]
            impedance.append(calculate_impedance(channel_data[-self.sampling_rate-1:-1]))
            wave.append(Function(np.linspace(-self.window_size, 0, self.num_points), channel_data))
            amp, freq = self.psd(channel_data)
            fft.append(Function(freq, amp))
        return impedance, wave, fft

    def filter_channel(self, channel_data):
        """
        DataFilter.detrend(channel_data, DetrendOperations.CONSTANT.value)
        DataFilter.perform_bandpass(channel_data, self.sampling_rate, 3.0, 45.0, 2, FilterTypes.BUTTERWORTH.value, 0)
        DataFilter.perform_bandstop(channel_data, self.sampling_rate, 48.0, 52.0, 2, FilterTypes.BUTTERWORTH.value, 0)
        DataFilter.perform_bandstop(channel_data, self.sampling_rate, 58.0, 62.0, 2, FilterTypes.BUTTERWORTH.value, 0)
        """
        DataFilter.perform_bandpass(channel_data, self.sampling_rate, 27.5, 45.0, 4, FilterTypes.BUTTERWORTH.value, 0)
        # Environmental noise cancellation
        DataFilter.remove_environmental_noise(channel_data, self.sampling_rate, NoiseTypes.FIFTY_AND_SIXTY.value)

    # Calculates Power Spectrum Density
    def psd(self, channel_data):
        nfft = DataFilter.get_nearest_power_of_two(self.sampling_rate)
        overlap = int(overlap_percentage*nfft)
        improvedData = channel_data[-nfft-1:-1]
        improvedData = np.subtract(improvedData, np.average(improvedData))
        return DataFilter.get_psd_welch(improvedData, nfft, overlap, self.sampling_rate, WindowOperations.HAMMING.value)

    def clip_data(self):
        data_length = len(self.total_data)
        if data_length > self.total_points:
            slice_size = data_length-self.total_points
            self.total_data = self.total_data[slice_size:]

    def get_unprocessed_samples(self):
        if self.prev_time is None:
            self.unprocessed_time = 0
            self.prev_time = get_time()
            return 0

        curr_time = get_time()
        passed_time = curr_time-self.prev_time
        self.unprocessed_time += passed_time
        self.prev_time = curr_time
        time_per_sample = 1000/(self.sampling_rate*self.speed)
        samples = int(self.unprocessed_time/time_per_sample)
        self.unprocessed_time -= samples*time_per_sample
        return samples


def calculate_impedance(channel_data):
    stddev = DataFilter.calc_stddev(channel_data)
    impedance = (math.sqrt(2)*stddev*1.0e-6)/drive_amps
    impedance -= base_impedance_ohms
    if impedance < 0:
        impedance = 0
    return impedance


def calculate_stddev(channel_data):
    avg = np.mean(channel_data)
    data = np.subtract(channel_data, avg)
    data = np.power(data, 2)
    val = np.sum(data)/len(data)
    return math.sqrt(val)


def get_time():
    return time.time()*1000
