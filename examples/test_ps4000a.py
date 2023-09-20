# -*- coding: utf-8 -*-
"""
Testing the ps4000a Series.
"""

# Imports
import matplotlib.pyplot as plt
import numpy as np
from picoscope import ps4000a
import time


def test_general_unit_calls(picoscope):
    """Test general unit calls."""
    picoscope.flashLed()
    print(picoscope.getAllUnitInfo())
    assert not picoscope.ping(), "Ping failed."
    print("General unit calls test passed.")


def test_timebase(ps):
    """Test the timebase methods."""
    # Preparation
    ps.memorySegments(1)
    # Tests
    if ps.model == "4444":
        data = ((20e-9, 3),
                (40e-9, 4))
    else:
        data = ((25e-9, 1),
                (100e-9, 7))
    for (t, timebase) in data:
        text = f"time {t} does not fit timebase {timebase}."
        assert ps.getTimeBaseNum(t) == timebase, "timebasenum: " + text
        assert ps.getTimestepFromTimebase(timebase) == t, "Timestep " + text
        timestep, _ = ps._lowLevelGetTimebase(timebase, 10, None, 0)
        assert timestep == t, f"lowLevel: {timestep} != {t}"
    print("Timebase test passed.")


def test_deviceResolution(ps):
    """Test setting/getting device resolution."""
    if ps.model == "4444":
        ps.setResolution("12")
        assert ps.resolution == "12", "Resolution was not set."
        # assert ps.getResolution() == "12"  not implemented yet
        print("Device resolution test passed.")
    else:
        print("Model does not support resolution.")


def test_rapid_block_mode(ps,
                          n_captures=100,
                          sample_interval=100e-9,  # 100 ns
                          sample_duration=2e-3,  # 1 ms
                          ):
    """Test the rapid block mode."""
    # Configuration of Picoscope
    ps.setChannel(channel="A", coupling="DC", VRange=1)
    ps.setChannel(channel="B", enabled=False)

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
        if not isinstance(channel, int):
            channel = ps.CHANNELS[channel]
        ps._lowLevelSetDataBuffer(channel, data, 0, 0)
        ps._lowLevelGetValuesAsync(numSamples, 0, 1, 0, 0, data_ready, None)
        print("Get values async started.")
    else:
        print("Data is not ready. RunBlock had an error.")


def test_runBlock_async(picoscope, channel="A", sample_interval=100e-9,
                        sample_duration=2e-3):
    """Test running a block asynchronously."""
    # Configuration of Picoscope
    global ps
    ps = picoscope
    ps.setChannel(channel=channel, coupling="DC", VRange=1)
    ps.memorySegments(1)
    ps.setNoOfCaptures(1)
    i, samples, m = ps.setSamplingInterval(sample_interval, sample_duration)
    ps.setSimpleTrigger("A", threshold_V=0.1, timeout_ms=1)

    global config
    config = channel, samples
    # Run the block
    ps.runBlock(callback=test_read_async)
    print("Run Block started, waiting 2 s.")
    time.sleep(2)
    print("Run block finished")


if __name__ == "__main__":
    """Run all the tests."""
    # Initialize the picoscope
    ps = ps4000a.PS4000a()

    try:
        # Run tests.
        test_general_unit_calls(ps)
        test_deviceResolution(ps)
        test_rapid_block_mode(ps)
        test_runBlock_async(ps)
    finally:
        # Close the connection
        ps.close()
    print("All tests passed.")
