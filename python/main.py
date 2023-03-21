import sys
from PyQt5 import uic, QtCore, QtGui
from board import *
from PyQt5.QtWidgets import *
from graph import *
import platform
import aboutDialog
import fileDialog
import serial.tools.list_ports

# global var
separator = "\\" if platform.system() == "Windows" else "/"  # file system separator
serial_port_connected = dict()  # all serial port connected


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.timer = QtCore.QTimer()

        # GUI loader
        uic.loadUi("..{0}GUI{0}gui.ui".format(separator), self)
        # File browser object
        self.fileManager = fileDialog.FileBrowser()
        # About window dialog
        self.aboutWindow = aboutDialog.AboutDialog()

        self.board = Board()
        self.selected_board_type = None
        self.selected_port = None

        # Wave Plot Instruction
        self.waveWidget = Graph()
        self.waveContainer.addWidget(self.waveWidget)

        # FFT Plot Instruction
        self.fftWidget = Graph()
        self.fftContainer.addWidget(self.fftWidget)

        # start GUI in dark mode and Initialize Widgets
        self.darkMode()
        self.initBoardType()

    # Methods for Board Type Input
    def initBoardType(self):
        global type_of_board
        for t in type_of_board.keys():
            self.inputBoard.addItem(t)

    def changeBoardType(self):
        self.selected_board_type = type_of_board.get(self.inputBoard.currentText())

    # Methods for Serial Port List
    def refreshSerialPort(self):
        self.serialPortInput.clear()
        global serial_port_connected
        ports = serial.tools.list_ports.comports()
        for port, description, _ in sorted(ports):
            serial_port_connected.update({description: port})
            self.serialPortInput.addItem(description)

    def connectToSerialPort(self):
        global serial_port_connected
        self.selected_port = serial_port_connected.get(self.serialPortInput.currentText())

    # ---------------------------------------------------------------------------------------------------------

    # Play the plot
    def start(self):
        if self.selected_port is not None and self.selected_board_type is not None:
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
            output_path = self.outputDirectory.text() + separator
            self.board.begin_capturing(self.selected_board_type, self.selected_port, output_path)
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        else:
            input_path = self.fileManager.getPath()
            if input_path == "":
                input_path = None
            self.board.playback(input_path)

        self.initGraph(self.waveWidget)
        self.waveWidget.setXRange(-self.board.num_points, 0)
        self.waveWidget.setYRange(-20000, 20000)

        self.initGraph(self.fftWidget)
        self.fftWidget.setXRange(0, 60)
        self.fftWidget.setYRange(0, 10000)

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

    def openOutputDirManager(self):
        outDir = QFileDialog.getExistingDirectory(self, "Select Directory", options=QFileDialog.ShowDirsOnly)
        self.outputDirectory.setText(outDir)

    def showAbout(self):
        self.aboutWindow.show()

    def initGraph(self, graph):
        for i in range(len(self.board.exg_channels)):
            color = self.board.get_channel_color(i + 1)
            graph.addPlot(color)

    # Methods for theme
    def fontMaximize(self):
        self.setStyleSheet(self.styleSheet() + "*{ font-size: 20px; }")

    def fontMinimize(self):
        self.setStyleSheet(self.styleSheet() + "*{ font-size: 13px; }")

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
    # main application
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


# Start Process
if __name__ == "__main__":
    main()
