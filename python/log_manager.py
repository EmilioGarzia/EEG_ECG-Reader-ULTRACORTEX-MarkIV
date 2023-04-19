import csv
import platform
import os
from datetime import datetime

from brainflow.board_shim import BoardShim
import numpy as np

separator = "\\" if platform.system() == "Windows" else "/"  # file system separator


class DataLogger:
    def __init__(self, output_folder, create_folder=True):
        self.output_folder = self.fix_separators(output_folder)
        if create_folder:
            self.output_folder += datetime.now().strftime("%m-%d-%Y_%H:%M:%S") + separator
            os.makedirs(self.output_folder, exist_ok=True)

        # Create file writer
        files = os.listdir(output_folder)
        self.record_num = len(files)
        if "metadata.csv" not in files:
            self.record_num += 1
        self.writer = None

    @classmethod
    def fix_separators(cls, path):
        to_fix = "\\" if separator == "/" else "\\"
        path.replace(to_fix, separator)
        if not path.endswith(separator):
            path += separator
        return path

    def save_metadata(self, metadata):
        file = open(self.output_folder + "metadata.csv", 'w')
        writer = csv.writer(file)
        writer.writerow(["Name", "Surname", "Description"])
        writer.writerow(metadata)
        file.close()

    def create_new_record(self, board):
        # Create writer
        output_file_name = self.output_folder + str(self.record_num) + ".csv"
        self.writer = csv.writer(output_file_name)
        self.record_num += 1

        exg_channels = BoardShim.get_exg_channels(board.board_id)
        accel_channels = BoardShim.get_accel_channels(board.board_id)
        analog_channels = BoardShim.get_analog_channels(board.board_id)

        # Write board information
        self.writer.writerow([board.board_id])

        # Write column headers
        headers = ["Packet Num"]
        headers.extend([f"EXG Channel {ch}" for ch in exg_channels])
        headers.extend([f"Accel Channel {ch}" for ch in accel_channels])
        headers.extend(["Other"]*7)
        headers.extend([f"Analog Channel {ch}" for ch in analog_channels])
        headers.extend(["Timestamp", "Other", "Timestamp (formatted)"])
        self.writer.writerow(headers)

    def write_data(self, data):
        transposed_data = np.transpose(data)
        for row in transposed_data:
            self.writer.writerow(row)


class LogParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.file = open(self.file_path, 'r')
        self.reader = csv.reader(self.file)
        self.has_new_data = False

    def begin(self):
        info = next(self.reader)
        next(self.reader)
        self.has_new_data = True
        return info

    def load_metadata(self):
        folder = os.path.dirname(self.file_path)
        files = os.listdir(folder)
        if "metadata.csv" in files:
            file = open(folder + separator + "metadata.csv", 'r')
            reader = csv.reader(file)
            next(reader)
            info = next(reader)
            file.close()
            return info
        return None

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
            print(data)

    def close(self):
        self.file.close()
