# -*- coding: utf-8 -*-
#
# Based on code from Luke Campagnola, author of amazing pyqtgraph library

from PyQt4 import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
from picoscope import ps6000


def setupScope():
    ps = ps6000.PS6000()

    # Example of simple capture
    res = ps.setSamplingFrequency(500E6, 4096)
    sampleRate = res[0]
    print("Sampling @ %f MHz, %d samples" % (res[0] / 1E6, res[1]))
    ps.setChannel("A", "AC", 50E-3)
    return [ps, sampleRate]


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.plotLayout = pg.GraphicsLayoutWidget()
        self.setCentralWidget(self.plotLayout)

        self.plot = self.plotLayout.addPlot(row=0, col=0)
        # self.avgPlot = self.plotLayout.addPlot(row=1, col=0)
        self.specPlot = self.plotLayout.addPlot(
            row=1, col=0, labels={'bottom': ('Frequency', 'Hz')})
        self.specPlot.setYRange(0, 0.2)

        self.wave = ScrollingPlot()
        self.plot.addItem(self.wave)

        self.triggerY = pg.InfiniteLine(angle=0, movable=True)
        self.triggerX = pg.InfiniteLine(movable=True)
        self.plot.addItem(self.triggerX)
        self.plot.addItem(self.triggerY)

        self.plot.setXRange(-1000, 1000)
        self.plot.setYRange(-0.05, 0.05)

        self.resize(800, 800)
        self.show()

        [self.scope, self.rate] = setupScope()
        self.scopeRunning = False

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)

        self.trigAvg = np.zeros(5000)
        self.lastValue = None
        self.lastData = None
        self.persistent = []
        self.lastUpdate = None

    def update(self):
        now = pg.ptime.time()
        if self.lastUpdate is None:
            self.lastUpdate = now
            dt = 0.0
        else:
            dt = now - self.lastUpdate
            self.lastUpdate = now

        # read data from sound device
        if self.scopeRunning is False:
            self.scope.runBlock()
            self.scopeRunning = True

        if self.scope.isReady():
            data = self.scope.getDataV(0, 4096)
            self.scopeRunning = False
        else:
            data = []

        if self.scopeRunning is False:
            self.scope.runBlock()

        # if self.lastData is not None:
        #     data.append([self.lastData[-1]])

        """
        while True:
            chunk = np.fromstring(self.pcm.read()[1], dtype=np.int16) / 2.0**15
            if len(chunk) == 0 and sum(map(len, data)) > 1024:
                break
            data.append(chunk)
        """

        if len(data) > 0:
            # data = np.concatenate(data)
            self.wave.append(data)

            # If there is a trigger available, shift wave plot to align
            # and add a persistent trace
            ty = self.triggerY.value()
            tx = self.triggerX.value()

            # if self.lastData is None:
            #     trigData = data
            # else:
            #     trigData = np.concatenate([self.lastData[:-15], data])
            tind = np.argwhere((data[:-15] < ty) * (data[15:] >= ty))
            if len(tind) > 0:
                tind = tind[min(2, tind.shape[0] - 1), 0] + 15
                self.wave.setPos(data.shape[0] - tind + tx, 0)

                # update persistent
                if len(self.wave.plots) > 1:
                    for i in [1, 2]:
                        d = self.wave.plots[-i].yData
                        p = pg.PlotDataItem(d)
                        self.persistent.append(p)
                        self.plot.addItem(p)
                        p.setPos(self.wave.plots[-i].pos() + self.wave.pos())

            else:
                self.wave.setPos(data.shape[0], 0)

            # update spectrum
            spec = np.abs(np.fft.fft(data[-1024:])[:512])
            x = np.linspace(0, self.rate / 2., len(spec))
            self.specPlot.plot(x, spec, clear=True)
            self.lastData = data

        while len(self.persistent) > 30:  # limit # of persistent plots
            p = self.persistent.pop(0)
            self.plot.removeItem(p)
        for p in self.persistent[:]:
            p.setOpacity(p.opacity() * (0.03**dt))
            if p.opacity() < 0.01:
                self.persistent.remove(p)
                self.plot.removeItem(p)

    def keyPressEvent(self, ev):
        if ev.text() == ' ':
            if self.timer.isActive():
                self.timer.stop()
            else:
                self.timer.start()
        else:
            print(ev.key())


class ScrollingPlot(QtGui.QGraphicsItem):
    """Simple appendable plot.

    New data is appended to the right and shifts existing data leftward."""
    def __init__(self):
        QtGui.QGraphicsItem.__init__(self)
        self.setFlag(self.ItemHasNoContents)

        self.plots = []
        self.lastValue = 0

    def append(self, data):
        # remove plots that are too old
        scene = self.scene()
        while len(self.plots) > 20:
            scene.removeItem(self.plots.pop(0))

        # add the next plot, shift to its correct position
        p = pg.PlotDataItem(data)
        self.plots.append(p)
        p.setParentItem(self)

        shift = len(data) - 1
        for p in self.plots:
            p.moveBy(-shift, 0)

    def boundingRect(self):
        return QtCore.QRectF()


if __name__ == '__main__':
    app = QtGui.QApplication([])
    win = MainWindow()
    app.exec_()
