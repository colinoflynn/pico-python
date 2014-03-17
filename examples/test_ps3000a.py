

# voltage range: -100:100 mV
# timebase: 50 ms

from picoscope import ps3000a
import matplotlib.pyplot as plt
import time
ps3000a = reload(ps3000a)

SERIAL_NUM = 'AR911/011\x00'
ps = ps3000a.PS3000a(SERIAL_NUM)

ps.setChannel(channel="A", coupling="AC", VRange=200e-3)
ps.setSamplingInterval(1e-5, 50e-3)
ps.setSimpleTrigger("A")

for i in range(5):
	ps.runBlock()
	while not ps.isReady():
		time.sleep(0.1)

	data = ps.getDataRaw()
	plt.plot(data[0])
plt.show()

ps.close()