# -*- coding: utf-8 -*-
"""
Testing the ps6000a series software-device interaction.
======================================================

This file provides tests in order to verify that the software does with the
oscilloscope, what it is supposed to do. Additionally the tests serve as
examples on how to do certain tasks.

Usage
-----

- Run this file in order to execute all software tests on your device.
- Import this file and execute the tests you want with your already opened
  oscilloscope device.

Created on Tue Jan 25 12:20:14 2022 by Benedikt Moneke
"""

# Imports
import matplotlib.pyplot as plt
import numpy as np
from picoscope import ps6000a
import time


def test_general_unit_calls(ps):
    """Test general unit calls"""
    ps.flashLed()
    print(ps.getAllUnitInfo())
    assert not ps.ping(), "Ping failed."
    print("General unit calls test passed.")


def test_timebase(ps):
    """Test the timebase methods."""
    # Preparation
    ps.memorySegments(1)
    # Tests
    data = ((200e-12, 0),
            (800e-12, 2),
            (3.2e-9, 4),
            (6.4e-9, 5),
            (10e-9, 5),
            (15e-9, 6))
    for (t, timebase) in data:
        text = "Time {} does not give timebase {}".format(t, timebase)
        assert ps.getTimeBaseNum(t) == timebase, text
    data = (
        (800e-12, 2),
        (3.2e-9, 4),
        (6.4e-9, 5),
        (12.8e-9, 6),
        (19.2e-9, 7),
        (3.84e-8, 10),
        (6.144e-7, 100),
    )
    for (t, timebase) in data:
        text = "{} s does not fit timebase {}.".format(t, timebase)
        assert ps.getTimestepFromTimebase(timebase) == t, "Timestep: " + text
        try:
            timestep, _ = ps._lowLevelGetTimebase(timebase, 10, None, 0)
        except Exception:
            print(
                "getTimebase failed at time {}, timebase {}.".format(t,
                                                                     timebase))
            raise
        assert timestep == t, "LowLevel: {} != {}".format(timestep, t)
    print("Timebase test passed.")


def test_deviceResolution(ps):
    """Test setting/getting device resolution, including ADC limits."""
    ps.setResolution("12")
    assert ps.resolution == 1, "Picoscope variable was not set."
    assert ps.getResolution() == "12", "Picoscope resolution is wrong."
    assert ps.MIN_VALUE == -32736, "Minimum adc value is wrong."
    assert ps.MAX_VALUE == 32736, "Maximum adc value is wrong."
    print("Device resolution test passed.")


def test_rapid_block_mode(ps,
                          n_captures=100,
                          sample_interval=100e-9,  # 100 ns
                          sample_duration=2e-3,  # 1 ms
                          ):
    """Test the rapid block mode."""
    # Configuration of Picoscope
    ps.setChannel(channel="A", coupling="DC", VRange=1)
    ps.setChannel(channel="B", enabled=False)
    ps.setChannel(channel="C", enabled=False)
    ps.setChannel(channel="D", enabled=False)

    ps.setResolution('12')
    ps.setSamplingInterval(sample_interval, sample_duration)
    ps.setSimpleTrigger("A", threshold_V=0.1, timeout_ms=1)

    samples_per_segment = ps.memorySegments(n_captures)
    ps.setNoOfCaptures(n_captures)

    data = np.zeros((n_captures, samples_per_segment), dtype=np.int16)

    # Measurement
    t1 = time.time()

    ps.runBlock()
    ps.waitReady()

    t2 = time.time()
    print("Time to record data to scope: ", str(t2 - t1))

    # downSampleMode raw (no downsampling) is 0x80000000. 0 is invalid!
    ps.getDataRawBulk(data=data, downSampleMode=0x80000000)

    t3 = time.time()
    print("Time to copy to RAM: ", str(t3 - t2))

    plt.imshow(data[:, 0:ps.noSamples], aspect='auto', interpolation='none',
               cmap=plt.cm.hot)
    plt.colorbar()
    plt.title("rapid block mode")
    plt.show()
    print("Rapid block mode test passed.")


class Handler:

    def printing(self, text):
        print(text)

    def data_ready(self, handle, status, noOfSamples, overflow,
                   pParameter=None):
        """Show the asynchronously received data."""
        if status == 0:
            self.printing("{} samples received with overflow: {}".format(
                noOfSamples, overflow))
            plt.plot(self.data)
            plt.title("async")
            plt.show()
            self.ps._lowLevelClearDataBuffer(self.config[0], 0,
                                             downSampleMode=0x80000000)
            self.printing("Data reading asynchronously test passed.")
        else:
            self.printing("Data receiving error {}.".format(status))

    def test_read_async(self, handle=None, status=0, pParameter=None):
        """
        Test reading data asynchronously.

        If you call it manually instead of using it as a callback, use
        pParameter for handing over the picoscope instance.
        """
        if pParameter is not None:
            ps = pParameter
        else:
            ps = self.ps
        if status == 0:
            self.printing("Block is ready and can be read.")
            # config is a global variable written by the caller.
            channel, numSamples = self.config
            # Define data for data_ready.
            self.data = np.zeros(ps.noSamples, dtype=np.int16)
            if not isinstance(channel, int):
                channel = ps.CHANNELS[channel]
            self.config = channel, numSamples
            ps._lowLevelClearDataBufferAll(channel, 0)
            ps._lowLevelSetDataBuffer(channel, self.data,
                                      downSampleMode=0x80000000,
                                      segmentIndex=0)
            ps._lowLevelGetValuesAsync(ps.noSamples, 0, 1, 0x80000000, 0,
                                       self.data_ready, None)
            self.printing("Get values async started.")
        else:
            self.printing("Data is not ready. RunBlock had an error.")


def test_runBlock_async(ps, channel="A", sample_interval=100e-9,
                        sample_duration=2e-3):
    """Test running a block asynchronously."""
    # Define a handler to exchange data
    global handler
    handler = Handler()
    handler.ps = ps
    # Configuration of Picoscope
    ps.setChannel(channel=channel, coupling="DC", VRange=1)
    ps.memorySegments(1)
    ps.setNoOfCaptures(1)
    ps.setResolution('12')
    interval, samples, maxSamples = ps.setSamplingInterval(sample_interval,
                                                           sample_duration)
    ps.setSimpleTrigger("A", threshold_V=0.1, timeout_ms=1)

    handler.config = channel, samples
    # Run the block
    ps.runBlock(callback=handler.test_read_async)
    print("Run block started, waiting 1 s.")
    time.sleep(1)
    print("Run block finished.")


def test_downsampling(ps,
                      sample_interval=100e-9,  # 100 ns
                      sample_duration=2e-3,  # 1 ms
                      ):
    """Test for different downsampling methods."""
    ps._lowLevelClearDataBufferAll()
    ps.setChannel(channel="A", coupling="DC", VRange=1)
    ps.setChannel(channel="B", enabled=False)
    ps.setChannel(channel="C", enabled=False)
    ps.setChannel(channel="D", enabled=False)

    ps.setResolution('12')
    ps.memorySegments(1)
    ps.setNoOfCaptures(1)
    interval, samples, maxSamples = ps.setSamplingInterval(sample_interval,
                                                           sample_duration)
    ps.setSimpleTrigger("A", threshold_V=0.1, timeout_ms=1)

    ps.runBlock()
    ps.waitReady()

    data0 = np.zeros(ps.noSamples, dtype=np.int16)
    data1 = np.zeros(ps.noSamples, dtype=np.int16)
    data2 = np.zeros(ps.noSamples, dtype=np.int16)

    # downSampleMode raw (no downsampling) is 0x80000000. 0 is invalid!
    ps.getDataRaw(data=data0, downSampleMode=0x80000000)
    ps.getDataRaw(data=data1, downSampleMode=ps.RATIO_MODE['decimate'],
                  downSampleRatio=10)
    ps.getDataRaw(data=data2, downSampleMode=ps.RATIO_MODE['average'],
                  downSampleRatio=10)

    samplesReduced = len(data0) // 10
    plt.plot(data0, label="raw")
    plt.plot(range(0, 10 * samplesReduced, 10)[:samplesReduced],
             data1[:samplesReduced], label="decimate")
    plt.plot(range(0, 10 * samplesReduced, 10)[:samplesReduced],
             data2[:samplesReduced], label="average")
    plt.title("downsampling")
    plt.legend()
    plt.show()
    print("Downsampling test passed.")


if __name__ == "__main__":
    """Run all the tests."""
    # Initialize the picoscope
    ps = ps6000a.PS6000a()

    try:
        # Run tests.
        test_general_unit_calls(ps)
        test_timebase(ps)
        test_deviceResolution(ps)
        test_rapid_block_mode(ps)
        test_downsampling(ps)
        test_runBlock_async(ps)
    finally:
        # Close the connection
        ps.close()
    print("All tests passed.")
