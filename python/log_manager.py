import csv
import os
import numpy as np
from datetime import datetime

from brainflow.board_shim import BoardShim


class DataLogger:
    def __init__(self, output_path, create_folder=True):
        self.output_path = output_path
        self.output_folder = None
        self.record_num = 0
        self.output_file = None
        self.writer = None

        if create_folder:
            self.output_folder = os.path.join(self.output_path, datetime.now().strftime("%m-%d-%Y_%H-%M-%S"))
            os.makedirs(self.output_folder, exist_ok=True)

    def save_metadata(self, metadata):
        file = open(self.output_folder + "metadata.csv", 'w')
        writer = csv.writer(file)
        writer.writerow(["Name", "Surname", "Description"])
        writer.writerow(metadata)
        file.close()

    def create_new_record(self, board, exg_channels):
        # Create writer
        files = os.listdir(self.output_folder)
        self.record_num = len(files)
        if "metadata.csv" not in files:
            self.record_num += 1

        output_file_name = os.path.join(self.output_folder, str(self.record_num) + ".csv")
        self.output_file = open(output_file_name, 'w')
        self.writer = csv.writer(self.output_file)
        self.record_num += 1

        accel_channels = BoardShim.get_accel_channels(board.board_id)
        analog_channels = BoardShim.get_analog_channels(board.board_id)

        # Write board information
        self.writer.writerow([int(board.board_id)])

        # Write column headers
        headers = ["Packet Num"]
        headers.extend([f"EXG Channel {ch}" for ch in exg_channels])
        headers.extend([f"Accel Channel {ch}" for ch in accel_channels])
        headers.extend(["Other"]*7)
        headers.extend([f"Analog Channel {ch}" for ch in analog_channels])
        headers.extend(["Timestamp", "Other"])
        self.writer.writerow(headers)

    def write_data(self, data):
        if self.writer is not None:
            for row in data:
                if len(row) > 0:
                    self.writer.writerow(row)

    def close(self):
        if self.output_file is not None:
            self.output_file.close()
            self.output_file = None
            self.writer = None


class LogParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.board_id = self.begin()

    def load_metadata(self):
        folder = os.path.dirname(self.file_path)
        files = os.listdir(folder)
        if "metadata.csv" in files:
            file = open(os.path.join(folder, "metadata.csv"), 'r')
            reader = csv.reader(file)
            next(reader)
            info = next(reader)
            file.close()
            return info
        return None

    def begin(self):
        self.file = open(self.file_path, 'r')
        self.reader = csv.reader(self.file)
        info = next(self.reader)
        next(self.reader)
        try:
            self.has_new_data = True
            return int(info[0])
        except ValueError:
            self.has_new_data = False
            return -1

    def read_data(self, num_rows=1):
        data = []
        for i in range(num_rows):
            try:
                data.append(np.array(next(self.reader), dtype="float64"))
            except StopIteration:
                self.has_new_data = False
                break

        try:
            return np.array(data)
        except ValueError:
            print("Samples array has an invalid size!")

    def close(self):
        self.file.close()