import numpy as np
from pyqtgraph import PlotWidget, mkPen


def decibel_scale(x):
    return 10*np.log10(x)

def linear_scale(x, scale=1):
    return np.multiply(x, scale)


class Function:
    def __init__(self, x=None, y=None):
        if x is None:
            x = []
        if y is None:
            y = []
        self.x = x
        self.y = y


class Graph(PlotWidget):
    def __init__(self, resizer=None):
        super().__init__()
        self.plots = []
        self.resizer = Resizer() if resizer is None else resizer

        self.showGrid(x=True, y=True)
        self.setDefaultPadding(0)
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
        plot = self.plot([], [], pen=pen)
        self.plots.append(plot)
        return plot

    def reset(self):
        self.clear()
        self.plots.clear()

    def clearGraph(self):
        self.refresh([])
        self.resizer.reset()

    def refresh(self, data, scale_fn=linear_scale, **kwargs):
        for i, plot in enumerate(self.plots):
            if i < len(data):
                y = scale_fn(data[i].y, **kwargs)
                self.resizer.update(self, y)
                plot.setData(data[i].x, y)
            else:
                plot.setData([], [])


class Resizer:
    def __init__(self):
        self.min = float("inf")
        self.max = float("-inf")

    def reset(self):
        self.min = float("inf")
        self.max = float("-inf")

    def update(self, graph, data):
        self.min = min(self.min, np.min(data))
        self.max = max(self.max, np.max(data))
        graph.setYRange(self.min, self.max)