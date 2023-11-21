import os

from PyQt5.QtWidgets import QDialog
from PyQt5 import uic


class AboutDialog(QDialog):
    def __init__(self):
        super().__init__(None)
        uic.loadUi(os.path.join("GUI", "aboutDialog.ui"), self)
