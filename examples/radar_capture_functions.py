import numpy as np
import time

# collect 20% more samples than nominally necessary
SAMPLE_SAFETY_MARGIN = 1.25
LIGHTSPEED = 2.99e8


class RadarScope(object):
    """Interface to picoscope, connected to radar"""

    def __init__(self, ps, rotation_period=2.4, pulse_rate=2100,
                 range_resolution=10.0, max_range=1e3, video_chan="A",
                 video_voltage=[-0.1, 2], trigger_voltage=0.4,
                 heading_chan="B", heading_voltage=[1, -10], data_dir="."):
        '''
        Set up interface to PicoScope for radar data collection.

        Parameters
        ----------
        ps : ps3000a object
        rotation_period : float
            Nominal antenna rotation period.
        pulse_rate : int
            Nominal radar pulse rate.
        max_range : float
            range, in meters, to which samples will be recorderd
        range_resolution : float
            Nominal range resolution for radar data capturing. This is
            translated to the digital (time) sampling rate.  The actual
            physical range resolution is limited by the radar pulse length.
        video_chan, heading_chan : String
            Oscilloscope channels (e.g. "A", "B") connected to the radar's
            video and heading pulse signals.
        video_voltage, heading_voltage : List
            Lists containing the minimum and maximum DC voltages needed
            to capture the input signals
        trigger_voltage : float
            Trigger data collection when video rises past this threshold
        '''
        super(RadarScope, self).__init__()
        self.ps = ps
        self.rotation_period = rotation_period
        self.pulse_rate = pulse_rate
        self.max_range = max_range
        self.range_resolution = range_resolution
        self.video_chan = video_chan
        self.heading_chan = heading_chan
        self.video_voltage = video_voltage
        self.heading_voltage = heading_voltage
        self.n_captures = int(self.pulse_rate * rotation_period *
                              SAMPLE_SAFETY_MARGIN)
        self.sample_interval = 2 * self.range_resolution / LIGHTSPEED
        self.capture_duration = self.max_range * 2 / LIGHTSPEED
        self.data_dir = data_dir

        # set up oscilloscope channels, trigger, and sampling rate
        self.ps.setChannel(channel=self.video_chan, coupling="DC",
                           VRange=max([abs(x) for x in video_voltage]))
        self.ps.setChannel(channel=self.heading_chan, coupling="DC",
                           VRange=max([abs(x) for x in heading_voltage]))
        self.ps.setSamplingInterval(self.sample_interval,
                                    self.capture_duration)

        self.ps.setSimpleTrigger("A", threshold_V=trigger_voltage)
        self.max_samples_per_segment = self.ps.memorySegments(self.n_captures)
        self.samples_per_segment = int(self.capture_duration /
                                       self.sample_interval)
        self.ps.setNoOfCaptures(self.n_captures)

        self.video_buffer = np.zeros((self.n_captures,
                                      self.samples_per_segment),
                                     dtype=np.int16)
        self.heading_buffer = np.zeros((self.n_captures,
                                        self.samples_per_segment),
                                       dtype=np.int16)

    def run_sweep(self):
        '''
        Tells the PicoScope to run one rapid block of radar pulses
        according to the pre-specified settings.  Does not transfer the data
        collected from the PicoScope's memory to the computer.
        '''
        self.last_sweep_time = time.strftime("%Y%m%d_%H%M%S")
        self.ps.runBlock()

    def transfer_data(self, downsample_ratio=0, downsample_mode=0):
        '''
        Transfers stored data from the PicoScope's buffers to the computer's
        memory.
        '''
        t1 = time.time()
        ps.getDataRawBulk(channel=self.video_chan, data=self.video_buffer)
        ps.getDataRawBulk(channel=self.heading_chan, data=self.heading_buffer)
        print("Time to transfer data: " + str(time.time() - t1))

    def capture_sweep(self, downsample_ratio=0, downsample_mode=0):
        t1 = time.time()
        self.run_sweep()
        self.ps.waitReady()
        print("Time to capture data: " + str(time.time() - t1))
        self.transfer_data(downsample_ratio, downsample_mode)

    def zero_heading_indices(self, threshold=0):
        '''
        Returns the indices of the data blocks where the heading signal
        indicates that the antenna was at the zero point.
        '''
        pass

    def to_file(self, dir=None, echo=False):
        t1 = time.time()
        if dir is None:
            dir = self.data_dir
        filename = "sweep_" + self.last_sweep_time + ".swp"
        output_file = open(filename, "wb")
        output_file.write(self.video_buffer)
        output_file.write(self.heading_buffer)
        output_file.close()
        if echo:
            print(filename)
        print("Time to write data: " + str(time.time() - t1))

    def record(self, n_sweeps=1, minimum_interval=5):
        '''
        Capture n_sweeps sweeps, waiting no less than minimum_interval
        in between them.
        '''
        i = 0
        t1 = minimum_interval + 1
        while i < n_sweeps:
            while time.time() - t1 < minimum_interval:
                time.sleep(0)
            t1 = time.time()
            self.capture_sweep()
            self.to_file(echo=True)
            i += 1

    def disconnect(self):
        '''
        Closes the PicoScope API, releasing the oscilloscope.
        '''
        self.ps.close()


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    # picoscope = reload(picoscope)
    from picoscope import ps3000a
    # ps3000a = reload(ps3000a)

    SERIAL_NUM = 'AR911/011\x00'
    ps = ps3000a.PS3000a(SERIAL_NUM)

    rscope = RadarScope(ps, max_range=1e3, range_resolution=5)

    rscope.capture_sweep()
    # rscope.to_file()
    # rscope.record(10, 5)

    plt.imshow(rscope.video_buffer, aspect="auto")
    plt.show()

    rscope.disconnect()
