from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QFileInfo

class FileBrowser(QFileDialog):
    def __init__(self):
        super().__init__()
        self.setGeometry(100,100, 300, 300)
        self.path = None
        self.filename = None

    def showFileBrowser(self): self.path, _ = self.getOpenFileName(self)
    def getPath(self): return self.path
    def getFilename(self):
        self.filename = QFileInfo(self.path).fileName()
        return self.filename