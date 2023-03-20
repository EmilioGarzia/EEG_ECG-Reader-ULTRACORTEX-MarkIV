from PyQt5.QtWidgets import *
from PyQt5 import uic
import platform

separator = "\\" if platform.system() == "Windows" else "/"


class AboutDialog(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("..{0}GUI{0}aboutDialog.ui".format(separator), self)
