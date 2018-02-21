import matplotlib.pyplot as plt
import numpy as np
import time

from picoscope import ps3000a

SERIAL_NUM = 'AR911/011\x00'
ps = ps3000a.PS3000a(SERIAL_NUM)

# now = time.strftime("%Y%m%d_%H%M%S")
# filename = "sweep_" + now + ".swp"
# output_file = open(filename, "wb")

c = 3e8

# rapid block mode

ps.setChannel(channel="A", coupling="DC", VRange=1)

n_captures = 2300 * 3  # int(600 * 1.4)
sample_interval = 5 / 3e8
sample_duration = 1e3 * 2 / 3e8

ps.setSamplingInterval(sample_interval, sample_duration)
ps.setSimpleTrigger("A", threshold_V=0.2)

samples_per_segment = ps.memorySegments(n_captures)
ps.setNoOfCaptures(n_captures)

data = np.zeros((n_captures, samples_per_segment), dtype=np.int16)

t1 = time.time()

ps.runBlock()
ps.waitReady()

t2 = time.time()
print("Time to get sweep: " + str(t2 - t1))

ps.getDataRawBulk(data=data)

# for i in range(n_captures):
#     ps._lowLevelSetDataBuffer(ps.CHANNELS["A"],
#         data[i, :], 0, i)

# # t2 = time.time()
# nsamples = c_int32(ps.noSamples)
# from_segment_index = 0
# to_segment_index = n_captures - 1
# downsample_ratio = 0
# downsample_mode = 0
# overflow = np.zeros(n_captures, dtype=np.int16)
# overflow_ptr = overflow.ctypes.data_as(POINTER(c_int16))

# m = ps.lib.ps3000aGetValuesBulk(c_int16(ps.handle),
#         byref(nsamples),
#         c_int16(from_segment_index),
#         c_int16(to_segment_index),
#         c_int32(downsample_ratio),
#         c_int16(downsample_mode),
#         overflow_ptr)
# print m

# ps.checkResult(m)

t3 = time.time()
print("Time to read data: " + str(t3 - t2))


# output_file.write(data)
# t4 = time.time()
# print "Time to write data to disk: ", str(t4 - t3)
# output_file.close()

plt.imshow(data[:, 0:ps.noSamples], aspect='auto', interpolation='none',
           cmap=plt.cm.hot)
plt.colorbar()
plt.show()

ps.close()
