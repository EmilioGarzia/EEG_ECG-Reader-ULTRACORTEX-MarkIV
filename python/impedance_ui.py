import os

from PyQt5 import uic, QtCore, QtGui
from PyQt5.QtWidgets import QWidget, QPushButton

from board import exg_channels
from data_processing import DataProcessing

separator = os.path.sep

# Thresholds for impedance checking
threshold_railed_warn = 750
threshold_railed = 2500


class ImpedanceUI(QWidget):
    def __init__(self, board, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(f"..{separator}GUI{separator}impedanceGUI.ui", self)

        self.data_processing = DataProcessing(board, False, 1)
        self.board = board
        self.checking_button = None
        self.checking_channel = None

        for ch in exg_channels:
            self.findChild(QPushButton, f"ch{ch}").clicked.connect(self.check_impedance)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(150)
        self.timer.timeout.connect(self.update_impedance_value)
        self.timer.start()

    def check_impedance(self):
        self.stop_impedance_checking()
        self.checking_button = self.sender()
        new_checking_channel = int(self.checking_button.objectName()[2:])
        if new_checking_channel != self.checking_channel:
            self.start_impedance_checking(new_checking_channel)
        else:
            self.checking_channel = None

    def stop_impedance_checking(self):
        self.data_processing.stop()
        if self.checking_channel is not None:
            self.board.toggle_impedance_checking(self.checking_channel, False)
            self.update_button("Test", "white")

    def start_impedance_checking(self, channel):
        self.board.toggle_impedance_checking(channel, True)
        self.checking_channel = channel
        self.data_processing.start()

    def update_impedance_value(self):
        if self.checking_channel is None:
            return

        impedance, _, _ = self.data_processing.forward()
        if impedance is None:
            return

        imp = impedance[self.checking_channel-1]
        kohms = int(imp/1000)
        if kohms < threshold_railed_warn:
            color = "lime"
        elif kohms < threshold_railed:
            color = "yellow"
        else:
            color = "red"
        self.update_button(str(kohms), color)

    def update_button(self, text, color):
        self.checking_button.setStyleSheet(f"color: {color};")
        self.checking_button.setText(text)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.stop_impedance_checking()
        self.timer.stop()
        event.accept()
