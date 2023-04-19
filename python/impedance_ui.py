from PyQt5 import uic, QtCore
from PyQt5.QtWidgets import *
from log_manager import separator


class ImpedanceUI(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("..{0}GUI{0}impedanceGUI.ui".format(separator), self)
