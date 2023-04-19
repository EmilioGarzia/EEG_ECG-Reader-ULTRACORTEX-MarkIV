from PyQt5.QtWidgets import *
from PyQt5 import uic
from log_manager import separator


class AboutDialog(QDialog):
    def __init__(self):
        super().__init__(None)
        uic.loadUi("..{0}GUI{0}aboutDialog.ui".format(separator), self)
