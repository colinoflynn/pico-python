# -*- coding: utf-8
# Example by Colin O'Flynn
#
import time
import numpy as np
from picoscope import ps5000a

from matplotlib.mlab import find


class freqMeasure():
    def __init__(self):
        self.ps = ps5000a.PS5000a(connect=False)

    def openScope(self):
        self.ps.open()

        self.ps.setChannel("A", coupling="DC", VRange=5.0, probeAttenuation=10)
        self.ps.setChannel("B", enabled=False)
        self.ps.setChannel("C", enabled=False)
        self.ps.setChannel("D", enabled=False)
        res = self.ps.setSamplingFrequency(1000E6, 50000)
        self.sampleRate = res[0]
        print("Sampling @ %f MHz, %d samples" % (res[0]/1E6, res[1]))

        # Use external trigger to mark when we sample
        self.ps.setSimpleTrigger(trigSrc="External", threshold_V=0.150,
                                 timeout_ms=5000)

    def closeScope(self):
        self.ps.close()

    def armMeasure(self):
        self.ps.runBlock()

    def freq_from_crossings(self, sig):
        """Estimate frequency by counting zero crossings"""
        # From https://gist.github.com/endolith/255291:

        fs = self.sampleRate

        # Find all indices right before a rising-edge zero crossing
        indices = find((sig[1:] >= 0) & (sig[:-1] < 0))
        # More accurate, using linear interpolation to find intersample
        # zero-crossings (Measures 1000.000129 Hz for 1000 Hz, for instance)
        crossings = [i - sig[i] / (sig[i+1] - sig[i]) for i in indices]
        # Some other interpolation based on neighboring points might be better.
        # Spline, cubic, whatever
        return fs / np.mean(np.diff(crossings))

    def measure(self):
        print("Waiting for trigger")
        while(self.ps.isReady() is False):
            time.sleep(0.01)
        print("Sampling Done")
        data = self.ps.getDataV("A", 50000)

        data = data - np.mean(data)
        freq = self.freq_from_crossings(data)

        print(freq)


if __name__ == "__main__":
    fm = freqMeasure()
    fm.openScope()

    try:
        while 1:
            fm.armMeasure()
            fm.measure()
    except KeyboardInterrupt:
        pass

    fm.closeScope()
