# -*- coding: utf-8
#
# Colin O'Flynn, Copyright (C) 2013. All Rights Reserved. <coflynn@newae.com>
#
import time
import numpy as np
from picoscope import ps6000

import pylab as plt

import scipy
import scipy.fftpack


def fft(signal, freq):
    FFT = abs(scipy.fft(signal))
    FFTdb = 20*scipy.log10(FFT)
    freqs = scipy.fftpack.fftfreq(len(signal), 1/freq)

    FFTdb = FFTdb[2:len(freqs)/2]
    freqs = freqs[2:len(freqs)/2]

    return (freqs, FFTdb)


def examplePS6000():
    fig = plt.figure()  # noqa
    plt.ion()
    plt.show()

    print("Attempting to open...")
    ps = ps6000.PS6000()

    # Example of simple capture
    res = ps.setSamplingFrequency(250E6, 4096)
    sampleRate = res[0]  # noqa
    print("Sampling @ %f MHz, %d samples" % (res[0]/1E6, res[1]))
    ps.setChannel("A", "AC", 50E-3)

    blockdata = np.array(0)

    for i in range(0, 50):
        ps.runBlock()
        while(ps.isReady() is False):
            time.sleep(0.01)

        print("Sampling Done")
        data = ps.getDataV("A", 4096)
        blockdata = np.append(blockdata, data)

        # Simple FFT
        # print "FFT In Progress"
        # [freqs, FFTdb] = fft(data, res[0])
        # plt.clf()
        # plt.plot(freqs, FFTdb)
        # plt.draw()

        start = (i - 5) * 4096
        if start < 0:
            start = 0
        # Spectrum Graph, keeps growing
        plt.clf()
        plt.specgram(blockdata[start:], NFFT=4096, Fs=res[0], noverlap=512)
        plt.xlabel('Measurement #')
        plt.ylabel('Frequency (Hz)')
        plt.draw()

    ps.close()


if __name__ == "__main__":
    examplePS6000()
