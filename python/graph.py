import numpy as np
from pyqtgraph import *


class Function:
    def __init__(self, x=None, y=None):
        if x is None:
            x = []
        if y is None:
            y = []
        self.x = x
        self.y = y


class Graph(PlotWidget):
    def __init__(self):
        super().__init__()
        self.plots = []

        self.showGrid(x=True, y=True)
        self.lightTheme()

    def setLabels(self, x_label, x_units, y_label, y_units):
        self.setLabel("left", y_label, y_units)
        self.setLabel("bottom", x_label, x_units)

    def lightTheme(self):
        self.setBackground("white")

    def darkTheme(self):
        self.setBackground("black")

    def hidePlot(self, index=1):
        if index <= len(self.plots):
            self.removeItem(self.plots[index - 1])

    def showPlot(self, index=1):
        if index <= len(self.plots):
            self.addItem(self.plots[index - 1])

    def addPlot(self, color):
        pen = mkPen(color=color)
        graph = self.plot([], [], pen=pen)
        self.plots.append(graph)
        return graph

    def clear(self):
        super().clear()
        self.plots.clear()

    def refresh(self, data, scale=1):
        for i, graph in enumerate(self.plots):
            if i == len(data):
                data.append(Function())
            graph.setData(data[i].x, np.multiply(data[i].y, scale))
