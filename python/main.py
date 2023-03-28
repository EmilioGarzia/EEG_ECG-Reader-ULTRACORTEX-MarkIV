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

        # GUI loader
        uic.loadUi("..{0}GUI{0}gui.ui".format(separator), self)
        self.playIcon = QtGui.QIcon("..{0}SVG{0}playButton.svg".format(separator))
        self.pauseIcon = QtGui.QIcon("..{0}SVG{0}pauseButton.svg".format(separator))
        self.playButton.setIcon(self.playIcon)
        self.outputDirectory.setText(os.path.expanduser("~"))
        # File browser object
        self.fileManager = fileDialog.FileBrowser()
        # About window dialog
        self.aboutWindow = aboutDialog.AboutDialog()
        self.timer = None
        self.singleWaves = None

        self.board = Board()
        self.selected_board_type = None
        self.selected_port = None

        self.waveWidget = Graph()
        self.waveWidget.setLabels("Time (s)", "Amplitude (µV)")
        self.waveContainer.addWidget(self.waveWidget)

        self.fftWidget = Graph()
        self.fftWidget.setLabels("Frequency (Hz)", "Amplitude (µV)")
        self.fftContainer.addWidget(self.fftWidget)

        self.ecgWidget = Graph()
        self.ecgContainer.addWidget(self.ecgWidget)

        # start GUI in dark mode and Initialize Widgets
        self.hideSessionWidgets()
        self.darkMode()
        self.initBoardType()

    def hideSessionWidgets(self):
        self.waveMainContainer.hide()
        self.fftMainContainer.hide()
        self.ecgMainContainer.hide()
        self.allChannelCheck.hide()
        self.eeg_channels.hide()
        self.ecg_channels.hide()
        self.widget.show()

    def showSessionWidgets(self):
        self.waveMainContainer.show()
        self.fftMainContainer.show()
        self.ecgMainContainer.show()
        self.allChannelCheck.show()
        self.eeg_channels.show()
        self.ecg_channels.show()
        self.widget.hide()

    def activatePlaybackMode(self):
        self.liveControlGroup.setEnabled(False)
        self.playbackGroup.setEnabled(True)
        self.patientGroup.setEnabled(False)

    def activateLiveMode(self):
        self.liveControlGroup.setEnabled(True)
        self.playbackGroup.setEnabled(False)
        self.patientGroup.setEnabled(True)

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

    # Play the plot
    def playPause(self):
        if self.timer is None or not self.timer.isActive():
            self.playButton.setIcon(self.pauseIcon)
            self.stopButton.setEnabled(True)

            delay = self.calculateDelay(self.speedControl.value())
            self.startLoop(self.update, delay)
        else:
            self.playButton.setIcon(self.playIcon)
            self.stopLoop()

    def stop(self):
        self.stopLoop()
        if self.playbackRadioBtn.isChecked():
            self.board.resetPlayback()
        self.clearGraphs()
        self.playButton.setIcon(self.playIcon)
        self.stopButton.setEnabled(False)

    def clearGraphs(self):
        self.waveWidget.refresh([])
        self.fftWidget.refresh([])
        self.ecgWidget.refresh([])
        if self.singleWaves is not None:
            for wave in self.singleWaves:
                wave.refresh([])

    def changeSpeed(self, value):
        self.timer.setInterval(self.calculateDelay(value))

    def calculateDelay(self, sliderValue):
        speed = 5 - sliderValue
        return int(1000 / self.board.sampling_rate * speed)

    # Functions that update plot data
    def update(self):
        wave, fft = self.board.read_data()
        if wave is not None and fft is not None:
            self.waveWidget.refresh(wave)
            self.fftWidget.refresh(fft)
            for i, graph in enumerate(self.singleWaves):
                graph.refresh([wave[i]])
        else:
            self.stopLoop()

    # some methods of MainWindow
    def showFileManager(self):
        self.fileManager.showFileBrowser()
        if len(self.fileManager.getFilename()) > 0:
            self.openedFileLabel.setText(self.fileManager.getFilename())
            self.closeSession()
            self.initSession()

    def initSession(self):
        if self.liveRadioBtn.isChecked():
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
            output_path = ""
            if not len(self.outputDirectory.text()) == 0:
                output_path = self.outputDirectory.text()
                output_path = output_path.replace("/", separator)
                if not output_path.endswith(separator):
                    output_path += separator

            output_path += datetime.now().strftime("%m-%d-%Y_%H:%M:%S") + separator
            os.makedirs(output_path, exist_ok=True)
            self.createMetadataFile(output_path)

            self.board.begin_capturing(self.selected_board_type, self.selected_port, output_path)
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        else:
            input_path = self.fileManager.getPath()
            self.loadMetadata(os.path.dirname(input_path))

            if input_path == "":
                input_path = None
            self.board.playback(input_path)

        # EEG/ECG Single Waves Instructions
        if self.singleWaves is None:
            self.singleWaves = []
            for ch in self.board.exg_channels:
                graph = Graph()
                graph.showAxes(True, size=(0, 0))
                graph.setXRange(-self.board.num_points, 0)
                graph.setYRange(-20000, 20000)
                self.initGraph(graph, [ch])
                self.singleWaves.append(graph)
                if self.eeg_ecg_mode.isChecked() and 9 <= ch <= 11:
                    self.findChild(QHBoxLayout, "singleECG{}".format(ch)).addWidget(graph)
                else:
                    self.findChild(QHBoxLayout, "singleCH{}".format(ch)).addWidget(graph)

        # Wave Plot Instructions
        self.initGraph(self.waveWidget)
        self.waveWidget.setXRange(-self.board.num_points, 0)
        self.waveWidget.setYRange(-20000, 20000)

        # FFT Plot Instructions
        self.initGraph(self.fftWidget)
        self.fftWidget.setXRange(0, 60)
        self.fftWidget.setYRange(0, 10000)

        # ECG Plot Instructions
        self.initGraph(self.ecgWidget, range(9, 11))
        self.ecgWidget.setLabels("Time (s)", "Amplitude (mV)")

        self.showSessionWidgets()
        self.playButton.setEnabled(True)
        self.mainViewGroup.setEnabled(True)
        if not self.ecgPlotCheckBox.isChecked():
            self.ecg_channels.hide()
            self.ecgMainContainer.hide()

        if self.darkMode:
            self.darkMode()
        else:
            self.lightMode()

    def closeSession(self):
        self.stopLoop()
        self.waveWidget.clear()
        self.fftWidget.clear()
        self.ecgWidget.clear()
        if self.singleWaves is not None:
            for i, wave in enumerate(self.singleWaves):
                self.findChild(QHBoxLayout, "singleCH{}".format(i+1)).removeWidget(wave)
            self.singleWaves = None

    def createMetadataFile(self, output_path):
        name = self.patientName.text()
        surname = self.patientSurname.text()
        description = self.patientDescription.toPlainText()
        if len(name) > 0 or len(surname) > 0 or len(description) > 0:
            metadata = open(output_path + "metadata.csv", "w")
            writer = csv.writer(metadata)
            writer.writerow(["Name", "Surname", "Description"])
            writer.writerow([name, surname, description])

    def loadMetadata(self, input_file_dir):
        files = os.listdir(input_file_dir)
        if "metadata.csv" in files:
            metadata = open(input_file_dir + separator + "metadata.csv", 'r')
            reader = csv.reader(metadata)
            next(reader)
            data = next(reader)
            self.patientName.setText(data[0])
            self.patientSurname.setText(data[1])
            self.patientDescription.setPlainText(data[2])

    def openOutputDirManager(self):
        outDir = QFileDialog.getExistingDirectory(self, "Select Directory", options=QFileDialog.ShowDirsOnly)
        self.outputDirectory.setText(outDir)

    def showAbout(self):
        self.aboutWindow.show()

    def initGraph(self, graph, channel_range=None):
        if channel_range is None:
            channel_range = self.board.exg_channels
        for i in channel_range:
            color = self.board.get_channel_color(i)
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
            if self.singleWaves is not None:
                for graph in self.singleWaves:
                    graph.lightTheme()
            if self.waveWidget is not None:
                self.waveWidget.lightTheme()
            if self.fftWidget is not None:
                self.fftWidget.lightTheme()
            if self.ecgWidget is not None:
                self.ecgWidget.lightTheme()

    def darkMode(self):
        with open("..{0}css{0}styleDark.css".format(separator), "r") as css:
            myCSS = css.read()
            self.setStyleSheet(myCSS)
            if self.singleWaves is not None:
                for graph in self.singleWaves:
                    graph.darkTheme()
            if self.waveWidget is not None:
                self.waveWidget.darkTheme()
            if self.fftWidget is not None:
                self.fftWidget.darkTheme()
            if self.ecgWidget is not None:
                self.ecgWidget.darkTheme()

    def toggleChannel(self, checked):
        ch = int(self.sender().text())
        if checked:
            self.singleWaves[ch-1].showPlot()
            self.waveWidget.showPlot(ch)
            self.fftWidget.showPlot(ch)
        else:
            self.singleWaves[ch-1].hidePlot()
            self.waveWidget.hidePlot(ch)
            self.fftWidget.hidePlot(ch)

    def toggleAllChannels(self, checked):
        for ch in self.board.exg_channels:
            self.findChild(QCheckBox, "CH{}check".format(ch)).setChecked(checked)
        self.ECGCH9check.setChecked(checked)
        self.ECGCH10check.setChecked(checked)
        self.ECGCH11check.setChecked(checked)

    # Methods for Show/Hide plot
    def show_hide_wave(self, state):
        if state == 2:
            self.waveMainContainer.show()
            self.showSidebar()
        else:
            self.waveMainContainer.hide()
            if not self.fftPlotCheckBox.isChecked() and not self.ecgPlotCheckBox.isChecked():
                self.hideSessionWidgets()

    def show_hide_fft(self, state):
        if state == 2:
            self.fftMainContainer.show()
            self.showSidebar()
        else:
            self.fftMainContainer.hide()
            if not self.wavePlotCheckBox.isChecked() and not self.ecgPlotCheckBox.isChecked():
                self.hideSessionWidgets()

    def show_hide_ecg(self, state):
        if not self.mainViewGroup.isEnabled():
            return

        if state == 2:
            self.ecgMainContainer.show()
            self.showSidebar()
        else:
            self.ecgMainContainer.hide()
            self.ecg_channels.hide()
            if not self.wavePlotCheckBox.isChecked() and not self.fftPlotCheckBox.isChecked():
                self.hideSessionWidgets()

    def showSidebar(self):
        self.allChannelCheck.show()
        self.eeg_channels.show()
        if self.ecgPlotCheckBox.isChecked():
            self.ecg_channels.show()

    def show_hide_toolbar(self):
        if self.controlsGroup.isVisible():
            self.controlsGroup.hide()
            self.liveControlGroup.hide()
            self.mainViewGroup.hide()
            self.patientGroup.hide()
            self.playbackGroup.hide()
        else:
            self.controlsGroup.show()
            self.liveControlGroup.show()
            self.mainViewGroup.show()
            self.patientGroup.show()
            self.playbackGroup.show()

    def on_off_ecg(self, state):
        if state == 2:
            self.ecgPlotCheckBox.setEnabled(True)
            self.ecgPlotCheckBox.setChecked(True)
            for ch in range(9, 12):
                self.findChild(QWidget, "singleCH{}_2".format(ch)).hide()
                if self.singleWaves is not None:
                    self.findChild(QHBoxLayout, "singleCH{}".format(ch)).removeWidget(self.singleWaves[ch-1])
                    self.findChild(QHBoxLayout, "singleECG{}".format(ch)).addWidget(self.singleWaves[ch-1])
        else:
            self.ecgPlotCheckBox.setEnabled(False)
            self.ecgPlotCheckBox.setChecked(False)
            for ch in range(9, 12):
                self.findChild(QWidget, "singleCH{}_2".format(ch)).show()
                if self.singleWaves is not None:
                    self.findChild(QHBoxLayout, "singleECG{}".format(ch)).removeWidget(self.singleWaves[ch-1])
                    self.findChild(QHBoxLayout, "singleCH{}".format(ch)).addWidget(self.singleWaves[ch-1])

    # Methods for loop
    def startLoop(self, loop, delay):
        self.timer = QtCore.QTimer()
        self.timer.setInterval(delay)
        self.timer.timeout.connect(loop)
        self.timer.start()

    def stopLoop(self):
        if self.timer is not None:
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
