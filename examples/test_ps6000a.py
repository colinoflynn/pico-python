# -*- coding: utf-8 -*-
"""
Testing the ps6000a Series.

Created on Tue Jan 25 12:20:14 2022 by Benedikt Moneke
"""

# Imports
import matplotlib.pyplot as plt
import numpy as np
from picoscope import ps6000a
import time


def test_general_unit_calls():
    assert ps.openUnitProgress()
    ps.flashLed()
    print(ps.getAllUnitInfo())
    assert not ps.ping()
    print("General unit calls test passed.")


def test_timebase():
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
    for (time, timebase) in data:
        assert ps.getTimeBaseNum(time) == timebase
    data = ((200e-12, 0),
            (800e-12, 2),
            (3.2e-9, 4),
            (6.4e-9, 5),
            (12.8-9, 6),
            (3.84e-8, 10),
            (6.144e-7, 100))
    for (time, timebase) in data:
        assert ps.getTimestepFromTimebase(timebase) == time
        timestep, _ = ps._lowLevelGetTimebase(timebase, 10, None, 0)
        assert timestep == time
    print("Timebase test passed.")


def test_deviceResolution():
    """Test setting/getting device resolution, including ADC limits."""
    ps.setResolution("12")
    assert ps.resolution == "12"
    assert ps.getResolution() == "12"
    assert ps.MIN_VALUE == -32736
    assert ps.MAX_VALUE == 32736
    print("Device resolution test passed.")


def test_rapid_block_mode(n_captures=100,
                          sample_interval=100e-9,  # 100 ns
                          sample_duration=2e-3,  # 1 ms
                          ):
    """Test the rapid block mode."""
    # Configuration of Picoscope
    ps.setChannel(channel="A", coupling="DC", VRange=1)
    ps.setChannel(channel="B", enabled=False)

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

    ps.getDataRawBulk(data=data)

    t3 = time.time()
    print("Time to copy to RAM: ", str(t3 - t2))

    plt.imshow(data[:, 0:ps.noSamples], aspect='auto', interpolation='none',
               cmap=plt.cm.hot)
    plt.colorbar()
    plt.show()
    print("Rapid block mode test passed.")


def data_ready(handle, status, noOfSamples, overflow, pParameter=None):
    """Show the asynchronously received data."""
    if status == 0:
        print(f"{noOfSamples} samples received with overflow: {overflow}")
        plt.plot(data)
        plt.show()
        print("Data reading asynchronously test passed.")
    else:
        print(f"Data receiving error {status}.")


def test_read_async(handle=None, status=0, pParameter=None):
    """Test reading data asynchronously."""
    if status == 0:
        print("Block is ready and can be read.")
        channel, numSamples = config
        global data
        data = np.empty(numSamples, dtype=np.int16)
        ps._lowLevelSetDataBuffer(channel, data, 0, 0)
        ps._lowLevelGetValuesAsync(numSamples, 0, 1, 0, 0, data_ready)
        print("callback started, waiting 0.5 s.")
        time.wait(0.5)
    else:
        print("Data is not ready. RunBlock had an error.")


def test_runBlock_async(channel="A", sample_interval=100e-9,
                        sample_duration=2e-3):
    """Test running a block asynchronously."""
    # Configuration of Picoscope
    ps.setChannel(channel=channel, coupling="DC", VRange=1)
    ps.memorySegments(1)
    ps.setResolution('12')
    i, samples, m = ps.setSamplingInterval(sample_interval, sample_duration)
    ps.setSimpleTrigger("A", threshold_V=0.1, timeout_ms=1)

    global config
    config = channel, samples
    # Run the block
    ps.runBlock(callback=test_read_async)
    print("Run Block started, waiting 0.5 s.")
    time.wait(0.5)


if __name__ == "__main__":
    """Run all the tests."""
    # Initialize the picoscope
    ps = ps6000a.PS6000a()

    try:
        # Run tests.
        test_general_unit_calls()
        test_deviceResolution()
        test_rapid_block_mode()
        test_runBlock_async()
    finally:
        # Close the connection
        ps.close()
    print("All tests passed.")
