
from __future__ import division
import ps6000

from ctypes import byref, c_long, c_uint16, c_int16, c_uint8, c_float, create_string_buffer, POINTER, c_uint32

import time

import textwrap
import pylab as plt
import numpy as np

if __name__ == "__main__":
    print(textwrap.fill("This demo will use the AWG to generate a gaussian pulse and measure " +
    "it on Channel A. To run this demo connect the AWG output of the PS6000 channel A."))

    print("Attempting to open Picoscope 6000...")

    # see page 13 of the manual to understand how to work this beast
    ps = ps6000.PS6000()
    ps.open()

    print(ps.getAllUnitInfo())



    #time.sleep(10)

    obs_duration = 10E-3
    sampling_interval = obs_duration / 4096 / 10
    #obs_duration = waveform_duration

    (interval, nSamples, maxSamples) = ps.setSamplingInterval(sampling_interval, obs_duration)
    print("Sampling interval = %f ns"%(interval*1E9));
    print("Taking  samples = %d"%nSamples)
    print("Maximum samples = %d"%maxSamples)

    ps.setChannel('A', 'DC', 5.0, 0.0, True, False)
    ps.setChannel('B', 'DC', 5.0, 0.0, True, False)
    ps.setSimpleTrigger('A', 0.0, 'Rising', delay=0, timeout_ms=100, enabled=True)
    # Technically, this should generate a a 2.2 V peak to peak waveform, but there is a bug
    # with the picoscope, causing it to only generate a useless waveform....
    #ps.setSigGenBuiltInSimple(0, 2.0, "Square", 5E3)

    #waveform = np.array(np.linspace(-32512, 32512, num=16384, endpoint=True), dtype=np.int16)
    #waveform = np.linspace(-2, 2, num=ps.AWGMaxSamples, endpoint=True)
    #waveform = np.linspace(-2, 2, num=100, endpoint=True)
    #waveform = np.array(np.linspace(np.iinfo(np.int16).min, np.iinfo(np.int16).max, num=100, endpoint=True), dtype=np.int16)
    #(waveform_duration, deltaPhase) = ps.setAWGSimple(waveform, obs_duration/10, offsetVoltage=0.0, pkToPk=4.0, indexMode="Single", triggerSource='ScopeTrig', triggerType='Rising')
    offsetVoltage = 0.0
    pkToPk = 4.0
    waveform_len = 500
    waveform = (c_uint16 * waveform_len)()
    min_waveform = 0x0000
    max_waveform = 0x0FFF
    #min_waveform = -32768
    #max_waveform =  32767

    for i in xrange(waveform_len):
        waveform[i] = int((max_waveform - min_waveform) /(waveform_len-1) *i+ min_waveform)
        print("waveform[%2d] = 0x%x"%(i,waveform[i]))

    deltaPhase = ps.getAWGDeltaPhase(obs_duration/2 / waveform_len)

    triggerType = ps.SIGGEN_TRIGGER_TYPES['Rising']
    triggerSource = ps.SIGGEN_TRIGGER_SOURCES['ScopeTrig']

    indexMode = ps.AWG_INDEX_MODES['Single']
    shots = 1
    m = ps.lib.ps6000SetSigGenArbitrary(
                ps.handle,
                c_uint32(int(offsetVoltage * 1E6)), # offset voltage in microvolts
                c_uint32(int(pkToPk * 1E6)), # pkToPk in microvolts
                c_uint32(int(deltaPhase)), # startDeltaPhase
                c_uint32(int(deltaPhase)), # stopDeltaPhase
                0,          # deltaPhaseIncrement
                0,          # dwellCount
                waveform, # arbitraryWaveform
                waveform_len, # arbitraryWaveformSize
                0, # sweepType for deltaPhase
                0, # operation (adding random noise and whatnot)
                indexMode, # single, dual, quad
                shots,
                0, # sweeps
                triggerType,
                triggerSource,
                0) # extInThreshold


    #for i in xrange(10):
    ps.runBlock()
    #time.sleep(1)
    ps.waitReady()
    print("Done waiting for trigger")


    # returns a numpy array
    (dataA, numSamplesReturned, overflow) = ps.getDataV('A', nSamples)
    (dataB, numSamplesReturned, overflow) = ps.getDataV('B', nSamples)



    # call this when you are done taking data
    #ps.stop()

    print("We read %d samples from the requested %d"%(numSamplesReturned, nSamples))
    print("Overflow value is %d"%(overflow))
    #print("The first 100 datapoints are ")
    #print(data[0:100])



    plt.ion()
    plt.figure()
    plt.hold(True)
    plt.plot(np.arange(nSamples)*interval*1E6, dataA)
    plt.plot(np.arange(nSamples)*interval*1E6, dataB)
    #plt.plot(np.linspace(0, obs_duration, len(waveform))*1E6, waveform)

    #raw_input("Press enter to continue ...")
    ps.stop()
    ps.close()

