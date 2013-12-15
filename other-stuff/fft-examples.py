# -*- coding: utf8 -*-

# Does some example FFTs & time-domain stuff, showing limitations of
# a scope that is BW limited, and shows FFT results with different
# number of bits in scope

import sys
import os
import threading
import time
import logging
import math
import numpy

import scipy
import scipy.fftpack
import scipy.signal as signal
import pylab
from scipy import pi
import numpy as np
import bl_waveforms as bl

    

def fft(signal, freq, plot=True):
    FFT = abs(scipy.fft(signal))
    FFTdb = 20*scipy.log10(FFT)
    freqs = scipy.fftpack.fftfreq(len(signal), 1/freq)

    FFTdb = FFTdb[2:len(freqs)/2]
    freqs = freqs[2:len(freqs)/2]

    if plot:
        pylab.plot(freqs,FFTdb)
        pylab.show()

    return (freqs, FFTdb)

def main():
    #Sample Frequency in Hz
    freqs = 5000E6

    #FFT Length
    fftlen = 2**16

    #Signal Frequency in Hz
    wffreq = 50E6

    #Bandwidth settings
    analogbw = 350E6
    filterorder = 3

    #Digitizing settings
    fscale = 0.8
    bits = 12

    print "FFT Len: %d"%fftlen    

    #Will need to remove these after
    fftlen += 2000

    #How many cycles should we complete?
    cycles = ((1/freqs) * fftlen) / (1/wffreq)

    sints = np.linspace(0, 2 * np.pi * cycles, fftlen)

    ##Wave Type - Sine or Square
    #rawx = np.sin(sints)
    rawx = bl.bl_square(sints)


    ##Bandwidth
    [b,a] = signal.butter(filterorder, analogbw / (freqs/2))
    filtx = signal.lfilter(b, a, rawx)[2000:]

    pylab.figure()
    pylab.hold(True)
    pylab.plot(filtx[0:1000])
    pylab.title("%d MHz Square Wave, %dMS/s, %dMHz BW"%(wffreq/1E6, freqs/1E6, analogbw/1E6))
    

    pylab.figure()
    
    ##Digitizing Error
    if bits is not None:
        digx = (filtx * fscale * ((2**bits) / 2))
        digx = digx.round() / ((2**bits) / 2)
    else:
        digx = filtx

    ##Add other processing here
    procx = digx

    #pylab.plot(sinx)
    #pylab.show()

    procx = procx / 1E3

    fft(procx, freqs)


     
if __name__ == '__main__':
    main()

    
