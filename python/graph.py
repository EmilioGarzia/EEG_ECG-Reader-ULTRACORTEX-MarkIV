import pyqtgraph as pg


class Graph(pg.PlotWidget):
    def __init__(self):
        super().__init__()
        self.plots = []

        self.showGrid(x=True, y=True)
        self.setLabel("left", "µV")
        self.setLabel("bottom", "Time")

        self.lightTheme()

    def lightTheme(self): self.setBackground("white")
    def darkTheme(self): self.setBackground("black")
    def hidePlot(self, index): self.removeItem(self.plots[index - 1])
    def showPlot(self, index): self.addItem(self.plots[index - 1])

    def addPlot(self, color):
        pen = pg.mkPen(color=color)
        plot = self.plot([], [], pen=pen)
        self.plots.append(plot)
        return plot

    def refresh(self, data):
        for i in range(len(self.plots)):
            self.plots[i].setData(data[i].x, data[i].y)
