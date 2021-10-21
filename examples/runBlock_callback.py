from picoscope import ps4000a
import matplotlib.pyplot as plt
import time

ps = ps4000a.PS4000a()


def callbackFunction(handle, status, pParameter=None):
    """This function is executed once the block is ready."""
    if status == 0:
        print("Block is ready and can be read.")
        data = ps.getDataV('A')

        print("data transferred")
        plt.plot(data)
        plt.show()
    else:
        print("An error occurred.")


# Picoscope setup
ps.setChannel(channel="A", coupling="DC", VRange=1)
ps.setChannel(channel="B", enabled=False)
ps.setChannel(channel="C", enabled=False)
ps.setChannel(channel="D", enabled=False)

sample_interval = 100e-9  # 100 ns
sample_duration = 2e-3  # 1 ms
ps.setSamplingInterval(sample_interval, sample_duration)
ps.setSimpleTrigger("A", threshold_V=0.1, timeout_ms=1)

# Run a block
print("Run a block with a callback function")
ps.runBlock(callback=callbackFunction)

time.sleep(10)
ps.close()
print("end")
