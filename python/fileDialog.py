from PyQt5.QtWidgets import QFileDialog

class FileBrowser(QFileDialog):
    def __init__(self):
        super().__init__()
        self.setGeometry(100,100, 300, 300)
        self.path = None

    def showFileBrowser(self):
        self.path, _ = self.getOpenFileName(self)

    def getPath(self): return self.path