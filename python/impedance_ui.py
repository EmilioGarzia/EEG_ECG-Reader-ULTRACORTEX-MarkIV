from PyQt5 import uic
from PyQt5.QtWidgets import *
from log_manager import separator


class ImpedanceUI(QWidget):
    def __init__(self, board, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.board = board
        uic.loadUi("..{0}GUI{0}impedanceGUI.ui".format(separator), self)

    def check_impedance(self):
        channel = int(self.sender().objectName())-1
        self.board.toggle_impedance_checking(channel)
