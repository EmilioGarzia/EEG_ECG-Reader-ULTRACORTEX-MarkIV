import sys

from PyQt5 import uic, QtCore

from board import *
from PyQt5.QtWidgets import *
from graph import *
import platform
import aboutDialog
import fileDialog

# global var
separator = "\\" if platform.system() == "Windows" else "/"  # file system separator


class MainWindow(QMainWindow):
    def __init__(self, board, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.timer = QtCore.QTimer()
        self.board = board

        # GUI loader
        uic.loadUi("..{0}GUI{0}gui.ui".format(separator), self)
        # File browser object
        self.fileManager = fileDialog.FileBrowser()

        # About window dialog
        self.aboutWindow = aboutDialog.AboutDialog()

        # Wave Plot Instruction
        self.waveWidget = Graph((-board.num_points, 0), (-20000, 20000))
        self.addGraph(self.waveWidget, self.waveContainer)

        # FFT Plot Instruction
        self.fftWidget = Graph((0, 60), (0, 10000))
        self.addGraph(self.fftWidget, self.fftContainer)

        # start GUI in dark mode
        self.darkMode()

    def start(self, ):
        self.board.connect(self.fileManager.getPath())
        self.startLoop(self.update, 1000 // self.board.sampling_rate)

    # Functions that update plot data
    def update(self):
        wave, fft = self.board.read_data()
        if wave is not None:
            self.waveWidget.refresh(wave)
        if fft is not None:
            self.fftWidget.refresh(fft)

    # some methods of MainWindow
    def showFileManager(self):
        self.fileManager.showFileBrowser()
        self.openedFileLabel.setText(self.fileManager.getFilename())

    def showAbout(self):
        self.aboutWindow.show()

    def addGraph(self, graph, container):
        for i in range(len(self.board.exg_channels)):
            color = self.board.get_channel_color(i + 1)
            graph.addPlot(color)
        container.addWidget(graph)

    # Methods for theme
    def lightMode(self):
        with open("..{0}css{0}styleLight.css".format(separator), "r") as css:
            myCSS = css.read()
            self.setStyleSheet(myCSS)
            self.waveWidget.lightTheme()
            self.fftWidget.lightTheme()

    def darkMode(self):
        with open("..{0}css{0}styleDark.css".format(separator), "r") as css:
            myCSS = css.read()
            self.setStyleSheet(myCSS)
            self.waveWidget.darkTheme()
            self.fftWidget.darkTheme()

    def toggledChannel(self, state):
        x = int(self.sender().text())
        if state == 2:
            self.waveWidget.showPlot(x)
            self.fftWidget.showPlot(x)
        else:
            self.waveWidget.hidePlot(x)
            self.fftWidget.hidePlot(x)

    def checkBoxSetter(self, status):
        self.CH1check.setChecked(status)
        self.CH2check.setChecked(status)
        self.CH3check.setChecked(status)
        self.CH4check.setChecked(status)
        self.CH5check.setChecked(status)
        self.CH6check.setChecked(status)
        self.CH7check.setChecked(status)
        self.CH8check.setChecked(status)
        self.CH9check.setChecked(status)
        self.CH10check.setChecked(status)
        self.CH11check.setChecked(status)
        self.CH12check.setChecked(status)
        self.CH13check.setChecked(status)
        self.CH14check.setChecked(status)
        self.CH15check.setChecked(status)
        self.CH16check.setChecked(status)

    def selectAllChannel(self, state):
        if state == 2:
            for x in self.board.exg_channels:
                self.waveWidget.showPlot(x)
                self.fftWidget.showPlot(x)
                self.checkBoxSetter(True)
        else:
            for x in self.board.exg_channels:
                self.waveWidget.hidePlot(x)
                self.fftWidget.hidePlot(x)
                self.checkBoxSetter(False)

    # Methods for Show/Hide plot
    def show_hide_wave(self, state):
        if state == 2:
            self.waveMainContainer.show()
            self.groupBox_2.show()
        else:
            self.waveMainContainer.hide()
            if not self.fftPlotCheckBox.isChecked():
                self.groupBox_2.hide()

    def show_hide_fft(self, state):
        if state == 2:
            self.fftMainContainer.show()
            self.groupBox_2.show()
        else:
            self.fftMainContainer.hide()
            if not self.wavePlotCheckBox.isChecked():
                self.groupBox_2.hide()

    # Methods for loop
    def startLoop(self, loop, delay):
        self.timer.setInterval(delay)
        self.timer.timeout.connect(loop)
        self.timer.start()

    def stopLoop(self):
        self.timer.stop()


# ****************************************** - - - Main block - - - *****************************************#
def main():
    # Connect GUI to Cyton board
    board = CytonDaisyBoard("/dev/ttyUSB0")

    # main application
    app = QApplication(sys.argv)
    window = MainWindow(board)
    window.show()
    sys.exit(app.exec_())


# Start Process
if __name__ == "__main__":
    main()
