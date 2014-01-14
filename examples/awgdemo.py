"""
PS6000 AWG Demo
By: Mark Harfouche

This is a demo of how to use AWG with the Picoscope 6000
It was tested with the PS6403B USB2.0 version

The AWG is connected to Channel A.
Nothing else is required

Warning, there seems to be a bug with AWG
see http://www.picotech.com/support/topic12969.html

"""
from __future__ import division

from picoscope import ps6000
import pylab as plt
import numpy as np

if __name__ == "__main__":
    print(__doc__)

    print("Attempting to open Picoscope 6000...")

    # see page 13 of the manual to understand how to work this beast
    ps = ps6000.PS6000()

    print(ps.getAllUnitInfo())


    waveform_desired_duration = 1E-3
    obs_duration = 3*waveform_desired_duration
    sampling_interval = obs_duration/4096

    (actualSamplingInterval, nSamples, maxSamples) = ps.setSamplingInterval(sampling_interval, obs_duration)
    print("Sampling interval = %f ns"%(actualSamplingInterval*1E9));
    print("Taking  samples = %d"%nSamples)
    print("Maximum samples = %d"%maxSamples)

    waveformAmplitude = 1.5
    waveformOffset = 0
    x = np.linspace(-1, 1, num=ps.AWGMaxSamples, endpoint=False)
    # generate an interesting looking waveform
    waveform = waveformOffset + (x/2 + (x**2)/2) * waveformAmplitude

    (waveform_duration, deltaPhase) = ps.setAWGSimple(waveform, waveform_desired_duration,
        offsetVoltage=0.0, indexMode="Dual", triggerSource='None')

    ps.setChannel('A', 'DC', 2.0, 0.0, enabled=True, BWLimited=False)
    ps.setSimpleTrigger('A', 0.0, 'Falling', delay=0, timeout_ms=100, enabled=True)


    ps.runBlock()
    ps.waitReady()
    print("Done waiting for trigger")
    dataA = ps.getDataV('A', nSamples, returnOverflow=False)

    dataTimeAxis = np.arange(nSamples) * actualSamplingInterval


    plt.figure()
    plt.hold(True)
    plt.plot(dataTimeAxis, dataA, label="Clock")
    plt.grid(True, which='major')
    plt.title("Picoscope 6000 waveforms")
    plt.ylabel("Voltage (V)")
    plt.xlabel("Time (ms)")
    plt.legend()
    plt.show()

    ps.stop()
    ps.close()

