from PyQt5.QtWidgets import *
from PyQt5 import uic

class AboutDialog(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("..\\GUI\\aboutDialog.ui", self)