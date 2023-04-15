from PyQt5 import uic, QtCore, QtGui
from board import *
from PyQt5.QtWidgets import *
from graph import *
import platform
import aboutDialog
import fileDialog
import serial.tools.list_ports
from datetime import datetime

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
        self.waveWidget.setLabels("Time", "s", "Amplitude", "V")
        self.waveContainer.addWidget(self.waveWidget)

        self.fftWidget = Graph()
        self.fftWidget.setLabels("Frequency", "Hz", "Amplitude", "V")
        self.fftContainer.addWidget(self.fftWidget)

        self.ecgWidget = Graph()
        self.ecgWidget.setLabels("Time", "s", "Amplitude", "V")
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
        self.playButton.setEnabled(True)
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
        return int(self.board.update_speed_ms * speed)

    # Function that updates plot data
    def update(self):
        wave, fft = self.board.read_data()
        if wave is None or fft is None:
            self.stopLoop()
            self.playButton.setIcon(self.playIcon)
            self.playButton.setEnabled(False)
            return

        if self.eeg_ecg_mode.isChecked():
            eeg_wave, ecg_wave = self.splitWaves(wave)
            eeg_fft, _ = self.splitWaves(fft)
            self.waveWidget.refresh(eeg_wave, 1 / 1.0E6)
            self.fftWidget.refresh(eeg_fft, 1 / 1.0E6)
            self.ecgWidget.refresh(ecg_wave, 1 / 1.0E3)
        else:
            self.waveWidget.refresh(wave, 1 / 1.0E6)
            self.fftWidget.refresh(fft, 1 / 1.0E6)

        for i, w in enumerate(wave):
            if self.eeg_ecg_mode.isChecked() and i + 1 in self.board.ecg_channels:
                scale = 1 / 1.0E3
            else:
                scale = 1 / 1.0E6
            self.singleWaves[i].refresh([w], scale)

    def splitWaves(self, waves):
        eeg_waves = []
        ecg_waves = []
        for i, wave in enumerate(waves):
            if i + 1 in self.board.ecg_channels:
                ecg_waves.append(wave)
            else:
                eeg_waves.append(wave)
        return eeg_waves, ecg_waves

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
            if input_path == "":
                return

            self.loadMetadata(os.path.dirname(input_path))
            try:
                self.board.playback(input_path)
            except ValueError:
                return

        # EEG/ECG Single Waves Instructions
        if self.singleWaves is None:
            self.singleWaves = []
            for ch in self.board.exg_channels:
                graph = Graph()
                graph.showAxes(True, size=(0, 0))
                graph.setXRange(-self.board.window_size, 0)
                graph.setYRange(-0.05, 0.05)
                self.initGraph(graph, [ch])
                self.singleWaves.append(graph)
                if self.eeg_ecg_mode.isChecked() and ch in self.board.ecg_channels:
                    self.findChild(QHBoxLayout, "singleECG{}".format(ch)).addWidget(graph)
                else:
                    self.findChild(QHBoxLayout, "singleCH{}".format(ch)).addWidget(graph)

        # Wave Plot Instructions
        self.initGraph(self.waveWidget, self.board.exg_channels)
        self.waveWidget.setXRange(-self.board.window_size, 0)
        self.waveWidget.setYRange(-0.05, 0.05)

        # FFT Plot Instructions
        self.initGraph(self.fftWidget, self.board.exg_channels)
        self.fftWidget.setXRange(0, 60)
        self.fftWidget.setYRange(0, 1)

        # ECG Plot Instructions
        self.initGraph(self.ecgWidget, self.board.ecg_channels)
        self.ecgWidget.setXRange(-self.board.window_size, 0)
        self.ecgWidget.setYRange(-0.05, 0.05)

        self.showSessionWidgets()
        self.playButton.setIcon(self.playIcon)
        self.playButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.mainViewGroup.setEnabled(True)

        if self.eeg_ecg_mode.isChecked():
            self.showECGPlots()
        else:
            self.ecgPlotCheckBox.setChecked(False)
            self.ecgPlotCheckBox.setEnabled(False)

        if not self.ecgPlotCheckBox.isChecked():
            self.ecg_channels.hide()
            self.ecgMainContainer.hide()

        if self.darkMode:
            self.darkMode()
        else:
            self.lightMode()

    def closeSession(self):
        self.stopLoop()
        self.waveWidget.clearGraph()
        self.fftWidget.clearGraph()
        self.ecgWidget.clearGraph()
        if self.singleWaves is not None:
            for i, wave in enumerate(self.singleWaves):
                self.findChild(QHBoxLayout, "singleCH{}".format(i + 1)).removeWidget(wave)
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

    def initGraph(self, graph, channel_range):
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
            self.singleWaves[ch - 1].showPlot()
            if self.eeg_ecg_mode.isChecked() and ch in self.board.ecg_channels:
                self.ecgWidget.showPlot(ch - 8)
            else:
                self.waveWidget.showPlot(ch)
                self.fftWidget.showPlot(ch)
        else:
            self.singleWaves[ch - 1].hidePlot()
            if self.eeg_ecg_mode.isChecked() and ch in self.board.ecg_channels:
                self.ecgWidget.hidePlot(ch - 8)
            else:
                self.waveWidget.hidePlot(ch)
                self.fftWidget.hidePlot(ch)

    def toggleAllChannels(self, checked):
        self.checkChannels(self.board.exg_channels, "CH{}check", checked)
        self.checkChannels(self.board.ecg_channels, "ECGCH{}check", checked)

    def checkChannels(self, channel_range, name_format, checked):
        for ch in channel_range:
            checkbox = self.findChild(QCheckBox, name_format.format(ch))
            if checkbox.isChecked() != checked:
                checkbox.setChecked(checked)

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

            self.mini_controls_layout.addWidget(self.playButton)
            self.mini_controls_layout.addWidget(self.stopButton)
            self.mini_controls_layout.addWidget(self.speedControl)
        else:
            self.controlsGroup.show()
            self.liveControlGroup.show()
            self.mainViewGroup.show()
            self.patientGroup.show()
            self.playbackGroup.show()

            self.controlButtonsLayout.addWidget(self.playButton)
            self.controlButtonsLayout.addWidget(self.stopButton)
            self.speedControlLayout.addWidget(self.speedControl)

    def on_off_ecg(self, state):
        if state == 2:
            self.ecgPlotCheckBox.setEnabled(True)
            self.ecgPlotCheckBox.setChecked(True)
            self.showECGPlots()
            for ch in self.board.ecg_channels:
                self.findChild(QWidget, "singleCH{}_2".format(ch)).hide()
                if self.singleWaves is not None:
                    self.findChild(QHBoxLayout, "singleCH{}".format(ch)).removeWidget(self.singleWaves[ch - 1])
                    self.findChild(QHBoxLayout, "singleECG{}".format(ch)).addWidget(self.singleWaves[ch - 1])
        else:
            self.ecgPlotCheckBox.setEnabled(False)
            self.ecgPlotCheckBox.setChecked(False)
            self.hideECGPlots()
            for ch in self.board.ecg_channels:
                self.findChild(QWidget, "singleCH{}_2".format(ch)).show()
                if self.singleWaves is not None:
                    self.findChild(QHBoxLayout, "singleECG{}".format(ch)).removeWidget(self.singleWaves[ch - 1])
                    self.findChild(QHBoxLayout, "singleCH{}".format(ch)).addWidget(self.singleWaves[ch - 1])

    def hideECGPlots(self):
        for ch in self.board.ecg_channels:
            self.waveWidget.showPlot(ch)
            self.fftWidget.showPlot(ch)
            self.ecgWidget.hidePlot(ch)

    def showECGPlots(self):
        for ch in self.board.ecg_channels:
            self.waveWidget.hidePlot(ch)
            self.fftWidget.hidePlot(ch)
            self.ecgWidget.showPlot(ch)

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
