"""
PS2000 Demo.

By: Colin O'Flynn, based on Mark Harfouche's software

This is a demo of how to use AWG with the Picoscope 2204 along with capture
It was tested with the PS2204A USB2.0 version

The AWG is connected to Channel A.
Nothing else is required.

NOTE: Must change line below to use with "A" and "B" series PS2000 models

See http://www.picotech.com/document/pdf/ps2000pg.en-10.pdf for PS2000 models:
PicoScope 2104
PicoScope 2105
PicoScope 2202
PicoScope 2203
PicoScope 2204
PicoScope 2205
PicoScope 2204A
PicoScope 2205A

See http://www.picotech.com/document/pdf/ps2000apg.en-6.pdf for PS2000A models:
PicoScope 2205 MSO
PicoScope 2206
PicoScope 2206A
PicoScope 2206B
PicoScope 2207
PicoScope 2207A
PicoScope 2208
PicoScope 2208A
"""
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import time
from picoscope import ps2000
# from picoscope import ps2000a
import pylab as plt
import numpy as np

if __name__ == "__main__":
    print(__doc__)

    print("Attempting to open Picoscope 2000...")

    ps = ps2000.PS2000()
    # Uncomment this line to use with the 2000a/2000b series
    # ps = ps2000a.PS2000a()

    print("Found the following picoscope:")
    print(ps.getAllUnitInfo())

    waveform_desired_duration = 50E-6
    obs_duration = 3 * waveform_desired_duration
    sampling_interval = obs_duration / 4096

    (actualSamplingInterval, nSamples, maxSamples) = \
        ps.setSamplingInterval(sampling_interval, obs_duration)
    print("Sampling interval = %f ns" % (actualSamplingInterval * 1E9))
    print("Taking  samples = %d" % nSamples)
    print("Maximum samples = %d" % maxSamples)

    # the setChannel command will chose the next largest amplitude
    channelRange = ps.setChannel('A', 'DC', 2.0, 0.0, enabled=True,
                                 BWLimited=False)
    print("Chosen channel range = %d" % channelRange)

    ps.setSimpleTrigger('A', 1.0, 'Falling', timeout_ms=100, enabled=True)

    ps.setSigGenBuiltInSimple(offsetVoltage=0, pkToPk=1.2, waveType="Sine",
                              frequency=50E3)

    ps.runBlock()
    ps.waitReady()
    print("Waiting for awg to settle.")
    time.sleep(2.0)
    ps.runBlock()
    ps.waitReady()
    print("Done waiting for trigger")
    dataA = ps.getDataV('A', nSamples, returnOverflow=False)

    dataTimeAxis = np.arange(nSamples) * actualSamplingInterval

    ps.stop()
    ps.close()

    # Uncomment following for call to .show() to not block
    # plt.ion()

    plt.figure()
    plt.hold(True)
    plt.plot(dataTimeAxis, dataA, label="Clock")
    plt.grid(True, which='major')
    plt.title("Picoscope 2000 waveforms")
    plt.ylabel("Voltage (V)")
    plt.xlabel("Time (ms)")
    plt.legend()
    plt.show()
