import os
import sys

from PyQt5 import uic, QtCore, QtGui
from PyQt5.QtWidgets import *
import serial.tools.list_ports
from brainflow import BoardIds

from board import exg_channels, ecg_channels, Board
from brainflow.board_shim import BrainFlowError
from graph import Resizer, Graph, decibel_scale
from data_processing import DataProcessing
from playback import PlaybackManager
from impedance_ui import ImpedanceUI
from alert_dialog import AlertDialog
import aboutDialog
import fileDialog

separator = os.path.sep

# global var
serial_port_connected = dict()  # all serial port connected
type_of_board = {  # Supported types of boards
    "CYTON DAISY BOARD [16CH]": BoardIds.CYTON_DAISY_BOARD,
    "CYTON BOARD [8CH]": BoardIds.CYTON_BOARD,
    "CYTON DAISY WIFI BOARD [16CH]": BoardIds.CYTON_DAISY_WIFI_BOARD,
    "CYTON WIFI BOARD [8CH]": BoardIds.CYTON_WIFI_BOARD,
    "GANGLION BOARD": BoardIds.GANGLION_BOARD,
    "GANGLION WIFI BOARD": BoardIds.GANGLION_WIFI_BOARD
}


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        # Main GUI loading
        print(os.getcwd())
        uic.loadUi(f"..{separator}GUI{separator}gui.ui", self)
        self.playIcon = QtGui.QIcon(f"..{separator}SVG{separator}playButton.svg")
        self.pauseIcon = QtGui.QIcon(f"..{separator}SVG{separator}pauseButton.svg")
        self.playButton.setIcon(self.playIcon)
        self.outputDirectory.setText(os.path.expanduser("~"))
        self.fileManager = fileDialog.FileBrowser()

        # Additional windows loading
        self.aboutWindow = aboutDialog.AboutDialog()
        self.imp_ui = None
        self.darkTheme = None

        self.data_processing = None
        self.timer = None
        self.singleWaves = None

        self.waveWidget = Graph()
        self.waveWidget.setLabels("Time", "s", "Amplitude", "V")
        self.waveContainer.addWidget(self.waveWidget)

        self.fftWidget = Graph()
        self.fftWidget.setLabels("Frequency", "Hz", "Amplitude", "dB")
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

    # Methods for Serial Port List
    def refreshSerialPort(self):
        self.serialPortInput.clear()
        global serial_port_connected
        ports = serial.tools.list_ports.comports()
        for port, description, _ in sorted(ports):
            serial_port_connected.update({description: port})
            self.serialPortInput.addItem(description)

    # Play the plot
    def playPause(self):
        if self.timer is None or not self.timer.isActive():
            self.playButton.setIcon(self.pauseIcon)
            self.stopButton.setEnabled(True)
            self.calculateUpdateSpeed()
            self.data_processing.start()
            self.startLoop()
        else:
            self.playButton.setIcon(self.playIcon)
            self.stopLoop()

    def stop(self):
        self.stopLoop()
        self.data_processing.stop()
        self.clearGraphs()
        self.playButton.setEnabled(True)
        self.playButton.setIcon(self.playIcon)
        self.stopButton.setEnabled(False)

    def clearGraphs(self):
        self.waveWidget.clearGraph()
        self.fftWidget.clearGraph()
        self.ecgWidget.clearGraph()
        if self.singleWaves is not None:
            for wave in self.singleWaves:
                wave.clearGraph()

    def calculateUpdateSpeed(self):
        self.data_processing.speed = self.speedControl.value() / 4

    # Function that updates plot data
    def update(self):
        data_source = self.data_processing.data_source
        if data_source.is_finished():
            self.stopLoop()
            self.playButton.setIcon(self.playIcon)
            self.playButton.setEnabled(False)
            return

        _, wave, fft = self.data_processing.forward()
        if wave is None or fft is None:
            return

        if self.eeg_ecg_mode.isChecked():
            eeg_wave, ecg_wave = self.splitWaves(wave)
            eeg_fft, _ = self.splitWaves(fft)
            self.waveWidget.refresh(eeg_wave)
            self.fftWidget.refresh(eeg_fft, scale_fn=decibel_scale)
            self.ecgWidget.refresh(ecg_wave)
        else:
            self.waveWidget.refresh(wave)
            self.fftWidget.refresh(fft, scale_fn=decibel_scale)

        for i, w in enumerate(wave):
            self.singleWaves[i].refresh([w])

    @classmethod
    def splitWaves(cls, waves):
        eeg_waves = []
        ecg_waves = []
        for i, wave in enumerate(waves):
            if i + 1 in ecg_channels:
                ecg_waves.append(wave)
            else:
                eeg_waves.append(wave)
        return eeg_waves, ecg_waves

    # some methods of MainWindow
    def showFileManager(self):
        self.fileManager.showFileBrowser()
        if len(self.fileManager.getFilename()) > 0:
            self.initSession()

    def initSession(self):
        self.closeSession()
        if self.liveRadioBtn.isChecked():
            output_folder = self.outputDirectory.text()
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
            board_type = type_of_board.get(self.inputBoard.currentText())
            port = serial_port_connected.get(self.serialPortInput.currentText())
            try:
                data_source = Board(board_type, port, output_folder)

                patientName = self.patientName.text()
                patientSurname = self.patientSurname.text()
                patientDescription = self.patientDescription.toPlainText()
                if patientName != "" or patientSurname != "" or patientDescription != "":
                    data_source.logger.save_metadata([patientName, patientSurname, patientDescription])

                self.data_processing = DataProcessing(data_source)
                self.imp_ui = ImpedanceUI(data_source)
                self.impCheckBtn.setEnabled(True)
            except BrainFlowError:
                self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
                AlertDialog("Error!", "Board connection failed!" +
                            " Make sure you have selected a valid serial port" +
                            " and the board is on.", self).exec()
                return
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        else:
            input_path = self.fileManager.getPath()
            if input_path == "":
                return

            data_source = PlaybackManager(input_path)
            if data_source.board_id == -1:
                AlertDialog("Error!", "Input file is not valid!" +
                            " Make sure you have selected a file generated" +
                            " during a previous live stream session.", self).exec()
                return

            self.openedFileLabel.setText(self.fileManager.getFilename())
            metadata = data_source.parser.load_metadata()
            if metadata is not None:
                self.patientName.setText(metadata[0])
                self.patientSurname.setText(metadata[1])
                self.patientDescription.setPlainText(metadata[2])

            self.data_processing = DataProcessing(data_source)
            self.speedControl.setEnabled(True)

        # EEG/ECG Single Waves Instructions
        if self.singleWaves is None:
            resizer = Resizer()
            self.singleWaves = []
            for ch in exg_channels:
                graph = Graph(resizer)
                graph.showAxes(True, size=(0, 0))
                graph.setXRange(-self.data_processing.window_size, 0)
                self.initGraph(graph, [ch])
                self.singleWaves.append(graph)
                if self.eeg_ecg_mode.isChecked() and ch in ecg_channels:
                    self.findChild(QHBoxLayout, "singleECG{}".format(ch)).addWidget(graph)
                else:
                    self.findChild(QHBoxLayout, "singleCH{}".format(ch)).addWidget(graph)

        # Wave Plot Instructions
        self.initGraph(self.waveWidget, exg_channels)
        self.waveWidget.setXRange(-self.data_processing.window_size, 0)

        # FFT Plot Instructions
        self.initGraph(self.fftWidget, exg_channels)
        self.fftWidget.setXRange(0, 60)

        # ECG Plot Instructions
        self.initGraph(self.ecgWidget, ecg_channels)
        self.ecgWidget.setXRange(-self.data_processing.window_size, 0)

        self.showSessionWidgets()
        self.playButton.setIcon(self.playIcon)
        self.playButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.mainViewGroup.setEnabled(True)
        self.ecgPlotCheckBox.setEnabled(False)

        if self.eeg_ecg_mode.isChecked():
            self.showECGPlots()

        if not self.ecgPlotCheckBox.isChecked():
            self.ecg_channels.hide()
            self.ecgMainContainer.hide()

        if self.darkTheme:
            self.darkMode()
        else:
            self.lightMode()
        self.show_hide_toolbar()

    def closeSession(self):
        self.stopLoop()
        if self.data_processing is not None:
            self.data_processing.close()
        self.patientName.setText("")
        self.patientSurname.setText("")
        self.patientDescription.setPlainText("")
        self.speedControl.setEnabled(False)
        self.openedFileLabel.setText("<empty>")
        self.waveWidget.reset()
        self.fftWidget.reset()
        self.ecgWidget.reset()
        if self.singleWaves is not None:
            for i, wave in enumerate(self.singleWaves):
                self.findChild(QHBoxLayout, "singleCH{}".format(i + 1)).removeWidget(wave)
            self.singleWaves = None
        self.hideSessionWidgets()

    def openOutputDirManager(self):
        outDir = QFileDialog.getExistingDirectory(self, "Select Directory", options=QFileDialog.ShowDirsOnly)
        self.outputDirectory.setText(outDir)

    def showAbout(self):
        self.aboutWindow.show()

    @classmethod
    def initGraph(cls, graph, channel_range):
        for i in channel_range:
            color = Board.get_channel_color(i)
            graph.addPlot(color)

    # Methods for theme
    def fontMaximize(self):
        self.setStyleSheet(self.styleSheet() + "*{ font-size: 20px; }")

    def fontMinimize(self):
        self.setStyleSheet(self.styleSheet() + "*{ font-size: 13px; }")

    def lightMode(self):
        with open(f"..{separator}css{separator}styleLight.css", "r") as css:
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
            self.darkTheme = False

    def darkMode(self):
        with open(f"..{separator}css{separator}styleDark.css", "r") as css:
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
            self.darkTheme = True

    def toggleChannel(self, checked):
        ch = int(self.sender().text())

        if isinstance(self.data_processing.data_source, Board):
            self.data_processing.data_source.toggle_channel(ch, checked)

        if checked:
            self.singleWaves[ch - 1].showPlot()
            if self.eeg_ecg_mode.isChecked() and ch in ecg_channels:
                self.ecgWidget.showPlot(ch - 8)
            else:
                self.waveWidget.showPlot(ch)
                self.fftWidget.showPlot(ch)
        else:
            self.singleWaves[ch - 1].hidePlot()
            if self.eeg_ecg_mode.isChecked() and ch in ecg_channels:
                self.ecgWidget.hidePlot(ch - 8)
            else:
                self.waveWidget.hidePlot(ch)
                self.fftWidget.hidePlot(ch)

    def toggleAllChannels(self, checked):
        self.checkChannels(exg_channels, "CH{}check", checked)
        self.checkChannels(ecg_channels, "ECGCH{}check", checked)

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

    def show_impedance_detector(self):
        self.stop()
        self.imp_ui.show()

    def on_off_ecg(self, checked):
        if checked:
            self.ecgPlotCheckBox.setEnabled(True)
            self.ecgPlotCheckBox.setChecked(True)
            self.showECGPlots()
            for ch in ecg_channels:
                self.findChild(QWidget, "singleCH{}_2".format(ch)).hide()
                if self.singleWaves is not None:
                    self.findChild(QHBoxLayout, "singleCH{}".format(ch)).removeWidget(self.singleWaves[ch - 1])
                    self.findChild(QHBoxLayout, "singleECG{}".format(ch)).addWidget(self.singleWaves[ch - 1])
        else:
            self.ecgPlotCheckBox.setEnabled(False)
            self.ecgPlotCheckBox.setChecked(False)
            self.hideECGPlots()
            for ch in ecg_channels:
                self.findChild(QWidget, "singleCH{}_2".format(ch)).show()
                if self.singleWaves is not None:
                    self.findChild(QHBoxLayout, "singleECG{}".format(ch)).removeWidget(self.singleWaves[ch - 1])
                    self.findChild(QHBoxLayout, "singleCH{}".format(ch)).addWidget(self.singleWaves[ch - 1])

    def hideECGPlots(self):
        for i, ch in enumerate(ecg_channels):
            if self.findChild(QCheckBox, f"CH{ch}check").isChecked():
                self.waveWidget.showPlot(ch)
                self.fftWidget.showPlot(ch)
            self.ecgWidget.hidePlot(i+1)

    def showECGPlots(self):
        for i, ch in enumerate(ecg_channels):
            self.waveWidget.hidePlot(ch)
            self.fftWidget.hidePlot(ch)
            if self.findChild(QCheckBox, f"ECGCH{ch}check").isChecked():
                self.ecgWidget.showPlot(i+1)
            else:
                self.ecgWidget.hidePlot(i+1)

    # Methods for loop
    def startLoop(self):
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000//60)
        self.timer.timeout.connect(self.update)
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
