import os

from PyQt5.QtWidgets import QDialog
from PyQt5 import uic

separator = os.path.sep

class AboutDialog(QDialog):
    def __init__(self):
        super().__init__(None)
        uic.loadUi(f"..{separator}GUI{separator}aboutDialog.ui", self)
