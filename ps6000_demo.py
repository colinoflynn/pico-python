"""
PS6000 AWG Demo
By: Mark Harfouche

This is a demo of how to use AWG with the Picoscope 6000
It was tested with the PS6403D USB2.0 version

It shows how to setup the AWG in single shot mode to trigger
with the waveform acquisition.

The system triggers on an external clock connected to Channel A
The AWG is connected to Channel B
"""
from __future__ import division
import ps6000

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


    clk_period = 1E-3
    obs_duration = 10*clk_period
    sampling_interval = clk_period/4096

    (interval, nSamples, maxSamples) = ps.setSamplingInterval(sampling_interval, obs_duration)
    print("Sampling interval = %f ns"%(interval*1E9));
    print("Taking  samples = %d"%nSamples)
    print("Maximum samples = %d"%maxSamples)

    ps.setChannel('A', 'DC', 2.0, 0.0, True, False)
    ps.setChannel('B', 'DC', 2.0, 0.0, True, False)
    ps.setSimpleTrigger('A', 0.0, 'Rising', delay=0, timeout_ms=100, enabled=True)
    # Technically, this should generate a a 2.2 V peak to peak waveform, but there is a bug
    # with the picoscope, causing it to only generate a useless waveform....
    #ps.setSigGenBuiltInSimple(0, 2.0, "Square", 5E3)

    waveform = np.linspace(0.5, 1.25, num=ps.AWGMaxSamples, endpoint=True)
    waveform_desired_duration = clk_period*2
    (waveform_duration, deltaPhase) = ps.setAWGSimple(waveform, waveform_desired_duration,
        offsetVoltage=0.0, indexMode="Dual", triggerSource='ScopeTrig', triggerType='Rising')

    # take the desired waveform
    # This measures all the channels that have been enabled
    ps.runBlock()
    ps.waitReady()
    print("Done waiting for trigger")


    # Get the data one by one
    # There is no way to get the data all at once using our Python interface yet
    dataA = ps.getDataV('A', nSamples, returnOverflow=False)
    dataB = ps.getDataV('B', nSamples, returnOverflow=False)


    # call this when you are done taking data
    #ps.stop()

    # if you uncomment this and you aren't running inside an interactive
    # environment like Python(x,y), then you won't have time to view
    # the plot
    #plt.ion()

    plt.figure()
    plt.hold(True)
    plt.plot(np.arange(nSamples)*interval*1E3, dataA, label="Clock")
    plt.plot(np.arange(nSamples)*interval*1E3, dataB, label="AWG Waveform")
    plt.grid(True, which='major')
    plt.title("Picoscope 6000 waveforms")
    plt.ylabel("Voltage (V)")
    plt.xlabel("Time (ms)")
    plt.legend()
    plt.draw()

    ps.stop()
    ps.close()

