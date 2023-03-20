import sys
import pyqtgraph as pg
from board import *
from PyQt5 import *
from PyQt5.QtWidgets import *
import board
from Graph import *
import platform
import aboutDialog
import fileDialog

#global var
board = None
waveWidget = None
fftWidget = None
separator = "\\" if platform.system() == "Windows" else "/"  #file system separator

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        #GUI loader
        uic.loadUi("..{0}GUI{0}gui.ui".format(separator), self)
        #File browser object
        self.fileManager = fileDialog.FileBrowser()
        
        #About window dialog
        self.aboutWindow = aboutDialog.AboutDialog()

        #Wave Plot Instruction
        global waveWidget
        waveWidget = Graph()
        waveWidget.setXRange(-board.num_points, 0)
        waveWidget.setYRange(-20000, 20000)
        init_series(waveWidget)
        self.addWavePlot(waveWidget)
        
        # FFT Plot Instruction
        global fftWidget
        fftWidget = Graph()
        fftWidget.setXRange(0, 60)
        fftWidget.setYRange(0, 10000)
        init_series(fftWidget)
        self.addFTTPlot(fftWidget)
        
        #start GUI in dark mode
        self.darkMode()

    def start(self):
        global board
        board.connect(self.fileManager.getPath())
        self.startLoop(update, 1000//board.sampling_rate)

    #some methods of MainWindow
    def showFileManager(self): 
        self.fileManager.showFileBrowser()
        self.openedFileLabel.setText(self.fileManager.getFilename())

    def showAbout(self): self.aboutWindow.show()
    def addWavePlot(self, widget): self.waveContainer.addWidget(widget)
    def addFTTPlot(self, widget): self.fftContainer.addWidget(widget)
    
    #Methods for theme
    def lightMode(self):
        with open("..{0}css{0}styleLight.css".format(separator), "r") as css:
            global waveWidget
            global fftWidget
            myCSS = css.read()
            self.setStyleSheet(myCSS)
            waveWidget.lightTheme()
            fftWidget.lightTheme()
        
    def darkMode(self):
        with open("..{0}css{0}styleDark.css".format(separator), "r") as css:
            global waveWidget
            global fftWidget
            myCSS = css.read()
            self.setStyleSheet(myCSS)
            waveWidget.darkTheme()
            fftWidget.darkTheme()

    #Methods for Show/Hide plot
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

    #Methods for loop
    def startLoop(self, loop, delay):
            self.timer = QtCore.QTimer()
            self.timer.setInterval(delay)
            self.timer.timeout.connect(loop)
            self.timer.start()

    def stopLoop(self): self.timer.stop()


# ****************************************** - - - Main block - - - *****************************************#
def main():
    #Connect GUI to Cyton board
    global board
    board = CytonDaisyBoard("/dev/ttuUSB0")
    
    #main application
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


#Functions that update plot data
def update():
    wave, fft = board.read_data()
    if wave is not None:
        waveWidget.refresh(wave)
    if fft is not None:
        fftWidget.refresh(fft)

def init_series(graph):
    for i in range(len(board.exg_channels)):
        color = board.get_channel_color(i+1)
        graph.addPlot(color)

#Start Process
if __name__ == "__main__":
    main()