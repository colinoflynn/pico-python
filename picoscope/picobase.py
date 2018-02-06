# -*- coding: utf-8 -*-

# This is the base class that all picoscope modules use. As much as possible logic is
# put into this file. At minimum each instrument file requires you to modify the name
# of the API function call (e.g. ps6000xxxx vs ps4000xxxx). You can find pico-python
# at github.com/colinoflynn/pico-python .
#
# pico-python is Copyright (c) 2013-2014 By:
# Colin O'Flynn <coflynn@newae.com>
# Mark Harfouche <mark.harfouche@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Inspired by Patrick Carle's code at http://www.picotech.com/support/topic11239.html
# which was adapted from http://www.picotech.com/support/topic4926.html

"""This is the base class for PicoScope instruments."""

from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import inspect
import time

import numpy as np


class _PicoscopeBase(object):
    """
    This class defines a general interface for Picoscope oscilloscopes.

    This  class should not be called directly since it relies on lower level
    functions to communicate with the actual devices.

    """

    ### You must reimplement this in device specific classes

    # Do not include .dll or .so, these will be appended automatically
    LIBNAME = "ps6000"

    MAX_VALUE = 32764
    MIN_VALUE = -32764

    EXT_MAX_VALUE = 32767
    EXT_MIN_VALUE = -32767
    EXT_RANGE_VOLTS = 20

    CHANNEL_RANGE = [{"rangeV": 20E-3,  "apivalue": 1, "rangeStr": "20 mV"},
                     {"rangeV": 50E-3,  "apivalue": 2, "rangeStr": "50 mV"},
                     {"rangeV": 100E-3, "apivalue": 3, "rangeStr": "100 mV"},
                     {"rangeV": 200E-3, "apivalue": 4, "rangeStr": "200 mV"},
                     {"rangeV": 500E-3, "apivalue": 5, "rangeStr": "500 mV"},
                     {"rangeV": 1.0,    "apivalue": 6, "rangeStr": "1 V"},
                     {"rangeV": 2.0,    "apivalue": 7, "rangeStr": "2 V"},
                     {"rangeV": 5.0,    "apivalue": 8, "rangeStr": "5 V"},
                     ]

    NUM_CHANNELS = 2
    CHANNELS = {"A": 0, "B": 1}

    CHANNEL_COUPLINGS = {"DC50": 2, "DC": 1, "AC": 0}

    ###End of things you must reimplement (I think).

    # If we don't get this CaseInsentiveDict working, I would prefer to stick
    # with their spelling of archaic C all caps for this. I know it is silly,
    # but it removes confusion for certain things like
    # DC_VOLTAGE = DCVoltage or DcVoltage or DC_Voltage
    # or even better
    # SOFT_TRIG = SoftwareTrigger vs SoftTrig

    # For some reason this isn't working with me :S
    THRESHOLD_TYPE = {"Above": 0,
                      "Below": 1,
                      "Rising": 2,
                      "Falling": 3,
                      "RiseOrFall": 4}

    ### getUnitInfo parameter types
    UNIT_INFO_TYPES = {"DriverVersion"          : 0x0,
                       "USBVersion"             : 0x1,
                       "HardwareVersion"        : 0x2,
                       "VariantInfo"             : 0x3,
                       "BatchAndSerial"         : 0x4,
                       "CalDate"                : 0x5,
                       "KernelVersion"          : 0x6,
                       "DigitalHardwareVersion" : 0x7,
                       "AnalogueHardwareVersion": 0x8,
                       "PicoFirmwareVersion1"   : 0x9,
                       "PicoFirmwareVersion2"   : 0xA}

    def __init__(self, serialNumber=None, connect=True):
        """ Create a picoscope class, and by default also connect to the scope. """

        # TODO: Make A class for each channel
        # that way the settings will make more sense

        # These do not correspond to API values, but rather to
        # the "true" voltage as seen at the oscilloscope probe
        self.CHRange = [5.0] * self.NUM_CHANNELS
        self.CHOffset = [0.0] * self.NUM_CHANNELS
        self.ProbeAttenuation = [1.0] * self.NUM_CHANNELS

        self.handle = None

        if connect is True:
            self.open(serialNumber)

    def getUnitInfo(self, info):
        """ Return: A string containing the requested information. """
        if not isinstance(info, int):
            info = self.UNIT_INFO_TYPES[info]
        return self._lowLevelGetUnitInfo(info)

    def getMaxValue(self):
        """ Return the maximum ADC value, used for scaling. """
        # TODO: make this more consistent accross versions
        # This was a "fix" when we started supported PS5000a
        return self.MAX_VALUE

    def getMinValue(self):
        """ Return the minimum ADC value, used for scaling. """
        return self.MIN_VALUE

    def getAllUnitInfo(self):
        """ Return: human readible unit information as a string. """
        s = ""
        for key in sorted(self.UNIT_INFO_TYPES.keys(), key=self.UNIT_INFO_TYPES.get):
            s += key.ljust(30) + ": " + self.getUnitInfo(key) + "\n"

        s = s[:-1]
        return s

    def setChannel(self, channel='A', coupling="AC", VRange=2.0, VOffset=0.0, enabled=True,
                   BWLimited=False, probeAttenuation=1.0):
        """
        Set up a specific channel.

        It finds the smallest range that is capable of accepting your signal.
        Return actual range of the scope as double.

        The VOffset, is an offset that the scope will ADD to your signal.

        If using a probe (or a sense resitor), the probeAttenuation value is used to find
        the approriate channel range on the scope to use.

        e.g. to use a 10x attenuation probe, you must supply the following parameters
        ps.setChannel('A', "DC", 20.0, 5.0, True, False, 10.0)

        The scope will then be set to use the +- 2V mode at the scope allowing you to measure
        your signal from -25V to +15V.
        After this point, you can set everything in terms of units as seen at the tip of the probe.
        For example, you can set a trigger of 15V and it will trigger at the correct value.

        When using a sense resistor, lets say R = 1.3 ohm, you obtain the relation:

        V = IR, meaning that your probe as an attenuation of R compared to the current you are
        trying to measure.

        You should supply probeAttenuation = 1.3
        The rest of your units should be specified in amps.

        Unfortunately, you still have to supply a VRange that is very close to the allowed values.
        This will change in furture version where we will find the next largest range to
        accomodate the desired range.

        If you want to use units of mA, supply a probe attenuation of 1.3E3.
        Note, the authors recommend sticking to SI units because it makes it easier to guess
        what units each parameter is in.

        """
        if enabled:
            enabled = 1
        else:
            enabled = 0

        if not isinstance(channel, int):
            chNum = self.CHANNELS[channel]
        else:
            chNum = channel

        if not isinstance(coupling, int):
            coupling = self.CHANNEL_COUPLINGS[coupling]

        # finds the next largest range accounting for small floating point errors
        VRangeAPI = None
        for item in self.CHANNEL_RANGE:
            if item["rangeV"] - VRange / probeAttenuation > -1E-4:
                if VRangeAPI is None:
                    VRangeAPI = item
                    # break
                # Don't know if this is necessary assuming that it will iterate in order
                elif VRangeAPI["rangeV"] > item["rangeV"]:
                    VRangeAPI = item

        if VRangeAPI is None:
            raise ValueError("Desired range %f is too large. Maximum range is %f." %
                             (VRange, self.CHANNEL_RANGE[-1]["rangeV"] * probeAttenuation))

        # store the actually chosen range of the scope
        VRange = VRangeAPI["rangeV"] * probeAttenuation

        if BWLimited == 2:
            BWLimited = 2  # Bandwidth Limiter for PicoScope 6404
        elif BWLimited == 1:
            BWLimited = 1  # Bandwidth Limiter for PicoScope 6402/6403
        else:
            BWLimited = 0

        self._lowLevelSetChannel(chNum, enabled, coupling, VRangeAPI["apivalue"],
                                 VOffset / probeAttenuation, BWLimited)

        # if all was successful, save the parameters
        self.CHRange[chNum] = VRange
        self.CHOffset[chNum] = VOffset
        self.ProbeAttenuation[chNum] = probeAttenuation

        return VRange

    def runBlock(self, pretrig=0.0, segmentIndex=0):
        """ Run a single block, must have already called setSampling for proper setup. """

        # getting max samples is riddiculous. 1GS buffer means it will take so long
        nSamples = min(self.noSamples, self.maxSamples)

        self._lowLevelRunBlock(int(round(nSamples * pretrig)),          # to return the same No. Samples ( if pretrig != 0.0 ) I'm wrong ?
                               int(round(nSamples * (1 - pretrig))),
                               self.timebase, self.oversample, segmentIndex)

    def isReady(self):
        """
        Check if scope done.

        Returns: bool.

        """
        return self._lowLevelIsReady()

    def waitReady(self):
        """ Block until the scope is ready. """
        while not self.isReady():
            time.sleep(0.01)

    def setSamplingInterval(self, sampleInterval, duration, oversample=0, segmentIndex=0):
        """ Return (actualSampleInterval, noSamples, maxSamples). """
        self.oversample = oversample
        self.timebase = self.getTimeBaseNum(sampleInterval)

        timebase_dt = self.getTimestepFromTimebase(self.timebase)

        noSamples = int(round(duration / timebase_dt))

        (self.sampleInterval, self.maxSamples) = \
            self._lowLevelGetTimebase(self.timebase, noSamples, oversample, segmentIndex)

        self.noSamples = noSamples
        self.sampleRate = 1.0 / self.sampleInterval
        return (self.sampleInterval, self.noSamples, self.maxSamples)

    def setSamplingFrequency(self, sampleFreq, noSamples, oversample=0, segmentIndex=0):
        """ Return (actualSampleFreq, maxSamples). """
        # TODO: make me more like the functions above
        #       at least in terms of what I return
        sampleInterval = 1.0 / sampleFreq
        duration = noSamples * sampleInterval
        self.setSamplingInterval(sampleInterval, duration, oversample, segmentIndex)
        return (self.sampleRate, self.maxSamples)

    def setNoOfCaptures(self, noCaptures):
        self._lowLevelSetNoOfCaptures(noCaptures)

    def memorySegments(self, noSegments):
        maxSamples = self._lowLevelMemorySegments(noSegments)
        self.maxSamples = maxSamples
        self.noSegments = noSegments
        return self.maxSamples

    def getMaxMemorySegments(self):
        segments = self._lowLevelGetMaxSegments()
        return segments

    def setSimpleTrigger(self, trigSrc, threshold_V=0, direction="Rising", delay=0, timeout_ms=100,
                         enabled=True):
        """
        Simple Trigger setup.

        trigSrc can be either a number corresponding to the low level
        specifications of the scope or a string such as 'A' or 'AUX'

        direction can be a text string such as "Rising" or "Falling",
        or the value of the dict from self.THRESHOLD_TYPE[] corresponding
        to your trigger type.

        delay is number of clock cycles to wait from trigger conditions met
        until we actually trigger capture.

        timeout_ms is time to wait in mS from calling runBlock() or similar
        (e.g. when trigger arms) for the trigger to occur. If no trigger
        occurs it gives up & auto-triggers.

        Support for offset is currently untested

        Note, the AUX port (or EXT) only has a range of +- 1V (at least in PS6000)

        """
        if not isinstance(trigSrc, int):
            trigSrc = self.CHANNELS[trigSrc]

        if not isinstance(direction, int):
            direction = self.THRESHOLD_TYPE[direction]

        if trigSrc >= self.NUM_CHANNELS:
            threshold_adc = int((threshold_V / self.EXT_RANGE_VOLTS) * self.EXT_MAX_VALUE)

            # The external port is typically used as a clock. So I don't think we should
            # raise errors
            threshold_adc = min(threshold_adc, self.EXT_MAX_VALUE)
            threshold_adc = max(threshold_adc, self.EXT_MIN_VALUE)
        else:
            a2v = self.CHRange[trigSrc] / self.getMaxValue()
            threshold_adc = int((threshold_V + self.CHOffset[trigSrc]) / a2v)

            if threshold_adc > self.getMaxValue() or threshold_adc < self.getMinValue():
                raise IOError("Trigger Level of %fV outside allowed range (%f, %f)" % (
                    threshold_V, -self.CHRange[trigSrc] - self.CHOffset[trigSrc],
                    self.CHRange[trigSrc] - self.CHOffset[trigSrc]))

        enabled = int(bool(enabled))

        self._lowLevelSetSimpleTrigger(enabled, trigSrc, threshold_adc, direction, delay,
                                       timeout_ms)


    def getTriggerTimeOffset(self, segmentIndex = 0):
        return self._lowLevelGetTriggerTimeOffset(segmentIndex)


    def flashLed(self, times=5, start=False, stop=False):
        """
        Flash the front panel LEDs.

        Use one of input arguments to specify how the Picoscope will flash the
        LED

        times = The number of times the picoscope will flash the LED
        start = If true, will flash the LED indefinitely
        stop  = If true, will stop any flashing.

        Note that calls to the RunStreaming or RunBlock will stop any flashing.

        """
        if start:
            times = -1
        if stop:
            times = 0

        self._lowLevelFlashLed(times)

    def getScaleAndOffset(self,channel):
        """
        Return the scale and offset used to convert the raw waveform

        To use: first multiply by the scale, then subtract the offset

        Returns a dictionary with keys scale and offset
        """
        if not isinstance(channel, int):
            channel = self.CHANNELS[channel]
        return {'scale': self.CHRange[channel] / float(self.getMaxValue()), 'offset': self.CHOffset[channel]}


    def rawToV(self, channel, dataRaw, dataV=None, dtype=np.float64):
        """ Convert the raw data to voltage units. Return as numpy array. """
        if not isinstance(channel, int):
            channel = self.CHANNELS[channel]

        if dataV is None:
            dataV = np.empty(dataRaw.size, dtype=dtype)

        a2v = self.CHRange[channel] / dtype(self.getMaxValue())
        np.multiply(dataRaw, a2v, dataV)
        np.subtract(dataV, self.CHOffset[channel], dataV)

        return dataV

    def getDataV(self, channel, numSamples=0, startIndex=0, downSampleRatio=1, downSampleMode=0,
                 segmentIndex=0, returnOverflow=False, exceptOverflow=False,
                 dataV=None, dataRaw=None, dtype=np.float64):
        """
        Return the data as an array of voltage values.

        it returns (dataV, overflow) if returnOverflow = True
        else, it returns returns dataV
        dataV is an array with size numSamplesReturned
        overflow is a flag that is true when the signal was either too large
                 or too small to be properly digitized

        if exceptOverflow is true, an IOError exception is raised on overflow if
        returnOverflow is False. This allows you to detect overflows at
        higher layers w/o complicated return trees. You cannot however read the '
        good' data, you only get the exception information then.

        """

        (dataRaw, numSamplesReturned, overflow) = self.getDataRaw(channel, numSamples, startIndex,
                                                                  downSampleRatio, downSampleMode,
                                                                  segmentIndex, dataRaw)

        if dataV is None:
            dataV = self.rawToV(channel, dataRaw, dtype=dtype)
            dataV = dataV[:numSamplesReturned]
        else:
            self.rawToV(channel, dataRaw, dataV, dtype=dtype)
            dataV[numSamplesReturned:] = np.nan

        if returnOverflow:
            return (dataV, overflow)
        else:
            if overflow and exceptOverflow:
                raise IOError("Overflow detected in data")
            return dataV

    def getDataRaw(self, channel='A', numSamples=0, startIndex=0, downSampleRatio=1,
                   downSampleMode=0, segmentIndex=0, data=None):
        """
        Return the data in the purest form.

        it returns a tuple containing:
        (data, numSamplesReturned, overflow)
        data is an array of size numSamples
        numSamplesReturned is the number of samples returned by the Picoscope
                (I don't know when this would not be equal to numSamples)
        overflow is a flag that is true when the signal was either too large
                 or too small to be properly digitized

        """

        if not isinstance(channel, int):
            channel = self.CHANNELS[channel]

        if numSamples == 0:
            # maxSamples is probably huge, 1Gig Sample can be HUGE....
            numSamples = min(self.maxSamples, self.noSamples)

        if data is None:
            data = np.empty(numSamples, dtype=np.int16)
        else:

            if data.dtype != np.int16:
                raise TypeError('Provided array must be int16')
            if data.size < numSamples:
                raise ValueError('Provided array must be at least as big as numSamples.')
            # see http://docs.scipy.org/doc/numpy/reference/generated/numpy.ndarray.flags.html
            if data.flags['CARRAY'] is False:
                raise TypeError('Provided array must be c_contiguous, aligned and writeable.')

        self._lowLevelSetDataBuffer(channel, data, downSampleMode, segmentIndex)

        (numSamplesReturned, overflow) = self._lowLevelGetValues(numSamples, startIndex,
                                                                 downSampleRatio, downSampleMode,
                                                                 segmentIndex)
        #necessary or else the next call to getValues will try to fill this array
        # unless it is a call trying to read the same channel.
        self._lowLevelClearDataBuffer(channel, segmentIndex)

        # overflow is a bitwise mask
        overflow = bool(overflow & (1 << channel))

        return (data, numSamplesReturned, overflow)

    def getDataRawBulk(self, channel='A', numSamples=0, fromSegment=0,
        toSegment=None, downSampleRatio=1, downSampleMode=0, data=None):
        '''
        Get data recorded in block mode.
        '''
        if not isinstance(channel, int):
            channel = self.CHANNELS[channel]
        if toSegment is None:
            toSegment = self.noSegments - 1
        if numSamples == 0:
            numSamples = min(self.maxSamples, self.noSamples)

        numSegmentsToCopy = toSegment - fromSegment + 1
        if data is None:
            data = np.ascontiguousarray(
                np.zeros((numSegmentsToCopy, numSamples), dtype=np.int16)
                )

        # set up each row in the data array as a buffer for one of
        # the memory segments in the scope
        for i, segment in enumerate(range(fromSegment, toSegment+1)):
            self._lowLevelSetDataBufferBulk(channel,
                                            data[i],
                                            segment,
                                            downSampleMode)
        overflow = np.ascontiguousarray(
            np.zeros(numSegmentsToCopy, dtype=np.int16)
            )

        self._lowLevelGetValuesBulk(numSamples, fromSegment, toSegment,
            downSampleRatio, downSampleMode, overflow)

        return (data, numSamples, overflow)



    def setSigGenBuiltInSimple(self, offsetVoltage=0, pkToPk=2, waveType="Sine",
                         frequency=1E6, shots=1, triggerType="Rising",
                         triggerSource="None", stopFreq=None, increment = 10.0,
                         dwellTime=1E-3, sweepType="Up", numSweeps=0):

        """
        This function generates simple signals using the built-in waveforms

        Supported waveforms include:
           Sine, Square, Triangle, RampUp, RampDown, and DCVoltage

        Some hardware also supports these additional waveforms:
           Sinc, Gaussian, HalfSine, and WhiteNoise

        To sweep the waveform, set the stopFrequency and optionally the
        increment, dwellTime, sweepType and numSweeps.

        Supported sweep types: Up, Down, UpDown, DownUp
        """
        # I put this here, because the python idiom None is very
        # close to the "None" string we expect
        if triggerSource is None:
            triggerSource = "None"

        if not isinstance(waveType, int):
            waveType = self.WAVE_TYPES[waveType]
        if not isinstance(triggerType, int):
            triggerType = self.SIGGEN_TRIGGER_TYPES[triggerType]
        if not isinstance(triggerSource, int):
            triggerSource = self.SIGGEN_TRIGGER_SOURCES[triggerSource]
        if not isinstance(sweepType, int):
            sweepType = self.SWEEP_TYPES[sweepType]


        self._lowLevelSetSigGenBuiltInSimple(offsetVoltage, pkToPk, waveType,
                                             frequency, shots, triggerType,
                                             triggerSource, stopFreq, increment,
                                             dwellTime, sweepType, numSweeps)



    def setAWGSimple(self, waveform, duration, offsetVoltage=None,
                     pkToPk=None, indexMode="Single", shots=1, triggerType="Rising",
                     triggerSource="ScopeTrig"):
        """
        Set the AWG to output your desired wavefrom.

        If you require precise control of the timestep increment, you should use
        setSigGenAritrarySimpleDelaPhase instead


        Check setSigGenAritrarySimpleDelaPhase for parameter explanation

        Returns: The actual duration of the waveform

        """
        sampling_interval = duration / len(waveform)

        if not isinstance(indexMode, int):
            indexMode = self.AWG_INDEX_MODES[indexMode]

        if indexMode == self.AWG_INDEX_MODES["Single"]:
            pass
        elif indexMode == self.AWG_INDEX_MODES["Dual"]:
            sampling_interval /= 2
        elif indexMode == self.AWG_INDEX_MODES["Quad"]:
            sampling_interval /= 4

        deltaPhase = self.getAWGDeltaPhase(sampling_interval)

        actual_druation = self.setAWGSimpleDeltaPhase(waveform, deltaPhase, offsetVoltage,
                                                      pkToPk, indexMode, shots, triggerType,
                                                      triggerSource)

        return (actual_druation, deltaPhase)

    def setAWGSimpleDeltaPhase(self, waveform, deltaPhase, offsetVoltage=None,
                               pkToPk=None, indexMode="Single", shots=1, triggerType="Rising",
                               triggerSource="ScopeTrig"):
        """
        Specify deltaPhase between each sample instead of the total waveform duration.

        Returns the actual time duration of the waveform

        If pkToPk and offset Voltage are both set to None, then their values are computed as

        pkToPk = np.max(waveform) - np.min(waveform)
        offset = (np.max(waveform) + np.min(waveform)) / 2

        This should in theory minimize the quantization error in the ADC.

        else, the waveform shoudl be a numpy int16 type array with the containing
        waveform

        For the Quad mode, if offset voltage is not provided, then waveform[0]
        is assumed to be the offset. In quad mode, the offset voltage is the point of symmetry

        This is function provides a little more control than
        setAWGSimple in the sense that you are able to specify deltaPhase
        directly. It should only be used when deltaPhase becomes very large.

        Warning. Ideally, you would want this to be a power of 2 that way each
        sample is given out at exactly the same difference in time otherwise,
        if you give it something closer to .75 you would obtain

         T  | phase accumulator value | sample
         0  |      0                  |      0
         5  |      0.75               |      0
        10  |      1.50               |      1
        15  |      2.25               |      2
        20  |      3.00               |      3
        25  |      3.75               |      3

        notice how sample 0 and 3 were played twice  while others were only
        played once.
        This is why this low level function is exposed to the user so that he
        can control these edge cases

        I would suggest using something like this: if you care about obtaining
        evenly spaced samples at the expense of the precise duration of the your
        waveform
        To find the next highest power of 2
            always a smaller sampling interval than the one you asked for
        math.pow(2, math.ceil(math.log(deltaPhase, 2)))

        To find the next smaller power of 2
            always a larger sampling interval than the one you asked for
        math.pow(2, math.floor(math.log(deltaPhase, 2)))

        To find the nearest power of 2
        math.pow(2, int(math.log(deltaPhase, 2), + 0.5))
        """

        """
        This part of the code is written for the PS6403 (PS6403B if that matters)
        I don't really know a good way to differentiate between PS6403 versions

        It essentially does some autoscaling for the waveform so that it can be sent
        to the Picoscope to allow for maximum resolution from the DDS.

        I haven't tested if you can actually obtain more resolution than simply setting
        the DDS to output from -2 to +2

        I assume they have some type of adjustable gain and offset on their DDS
        allowing them to claim that they can get extremely high resolution.
        """

        if not isinstance(indexMode, int):
            indexMode = self.AWG_INDEX_MODES[indexMode]
        if not isinstance(triggerType, int):
            triggerType = self.SIGGEN_TRIGGER_TYPES[triggerType]
        if not isinstance(triggerSource, int):
            triggerSource = self.SIGGEN_TRIGGER_SOURCES[triggerSource]

        if waveform.dtype == np.int16:
            if offsetVoltage is None:
                offsetVoltage = 0.0
            if pkToPk is None:
                pkToPk = 2.0  # TODO: make this a per scope function assuming 2.0 V AWG
        else:
            if indexMode == self.AWG_INDEX_MODES["Quad"]:
                # Optimize for the Quad mode.
                """
                Quad mode. The generator outputs the contents of the buffer,
                then on its second pass through the buffer outputs the same
                data in reverse order. On the third and fourth passes
                it does the same but with a negative version of the data. This
                allows you to specify only the first quarter of a waveform with
                fourfold symmetry, such as a sine wave, and let the generator
                fill in the other three quarters.
                """
                if offsetVoltage is None:
                    offsetVoltage = waveform[0]
            else:
                # Nothing to do for the dual mode or the single mode
                if offsetVoltage is None:
                    offsetVoltage = (np.max(waveform) + np.min(waveform)) / 2

            # make a copy of the original data as to not clobber up the array
            waveform = waveform - offsetVoltage
            if pkToPk is None:
                pkToPk = np.max(np.absolute(waveform)) * 2

            # waveform should now be baised around 0
            # with
            #     max(waveform) = +pkToPk/2
            #     min(waveform) = -pkToPk/2
            waveform /= pkToPk

            # waveform should now be a number between -0.5 and +0.5

            waveform += 0.5
            # and now the waveform is between 0 and 1
            # inclusively???

            # now the waveform is properly quantized
            waveform *= (self.AWGMaxVal - self.AWGMinVal)
            waveform += self.AWGMinVal

            waveform.round(out=waveform)

            # convert to an int16 typqe as requried by the function
            waveform = np.array(waveform, dtype=np.int16)

            # funny floating point rounding errors
            waveform.clip(self.AWGMinVal, self.AWGMaxVal, out=waveform)

        self._lowLevelSetAWGSimpleDeltaPhase(waveform, deltaPhase, offsetVoltage, pkToPk,
                                             indexMode, shots, triggerType, triggerSource)

        timeIncrement = self.getAWGTimeIncrement(deltaPhase)
        waveform_duration = timeIncrement * len(waveform)

        #if   indexMode == self.AWG_INDEX_MODES["Single"]:
            #pass
        #elif
        if indexMode == self.AWG_INDEX_MODES["Dual"]:
            waveform_duration *= 2
        elif indexMode == self.AWG_INDEX_MODES["Quad"]:
            waveform_duration *= 4

        return waveform_duration

    def getAWGDeltaPhase(self, timeIncrement):
        """
        Return the deltaPhase integer used by the AWG.

        This is useful when you are trying to generate very fast waveforms when
        you are getting close to the limits of your waveform generator.

        For example, the PS6000's DDS phase accumulator increments by
        deltaPhase every AWGDACInterval.
        The top 2**self.AWGBufferAddressWidth bits indicate which sample is
        being output by the DDS.

        """
        samplingFrequency = 1 / timeIncrement
        deltaPhase = int(samplingFrequency / self.AWGDACFrequency *
                          2 ** (self.AWGPhaseAccumulatorSize - self.AWGBufferAddressWidth))
        return deltaPhase

    def getAWGTimeIncrement(self, deltaPhase):
        """
        Return the time between AWG samples given a certain deltaPhase.

        You should use this function in conjunction with
        getAWGDeltaPhase to obtain the actual timestep of AWG.

        """
        samplingFrequency = deltaPhase * self.AWGDACFrequency / \
                            2 ** (self.AWGPhaseAccumulatorSize - self.AWGBufferAddressWidth)
        return 1 / samplingFrequency

    def setResolution(self, resolution):
        """For 5000-series scopes ONLY, sets the resolution. Error on other devices."""
        self._lowLevelSetDeviceResolution(self.ADC_RESOLUTIONS[resolution])

    def enumerateUnits(self):
        """ Enumerate connceted units. Return serial numbers as list of strings. """
        return self._lowLevelEnumerateUnits()

    def open(self, serialNumber=None):
        """ Open the scope, if serialNumber is None just opens first one found. """

        self._lowLevelOpenUnit(serialNumber)

    def openUnitAsync(self, serialNumber=None):
        """ Open the scope asynchronously. """
        self._lowLevelOpenUnitAsync(serialNumber)

    def openUnitProgress(self):
        """ Return a tuple (progress, completed). """
        return self._lowLevelOpenUnitProgress()

    def close(self):
        """
        Close the scope.

        You should call this yourself because the Python garbage collector
        might take some time.

        """
        if not self.handle is None:
            self._lowLevelCloseUnit()
            self.handle = None

    def stop(self):
        """ Stop scope acquisition. """
        self._lowLevelStop()

    def __del__(self):
        self.close()

    def checkResult(self, ec):
        """ Check result of function calls, raise exception if not 0. """
        # NOTE: This will break some oscilloscopes that are powered by USB.
        # Some of the newer scopes, can actually be powered by USB and will return
        # a useful value. That should be given back to the user.
        # I guess we can deal with these edge cases in the functions themselves
        if ec == 0:
            return

        else:
            #print("Error Num: 0x%x"%ec)
            ecName = self.errorNumToName(ec)
            ecDesc = self.errorNumToDesc(ec)
            raise IOError('Error calling %s: %s (%s)' % (str(inspect.stack()[1][3]), ecName, ecDesc))

    def errorNumToName(self, num):
        """ Return the name of the error as a string. """
        for t in self.ERROR_CODES:
            if t[0] == num:
                return t[1]

    def errorNumToDesc(self, num):
        """ Return the description of the error as a string. """
        for t in self.ERROR_CODES:
            if t[0] == num:
                try:
                    return t[2]
                except IndexError:
                    return ""

    def changePowerSource(self, powerstate):
        """ Change the powerstate of the scope. Valid only for PS54XXA/B? """
        # I should probably make an enumerate table for these two cases, but htey are in fact just the
        # error codes. Picoscope should have made it a separate enumerate themselves.
        # I'll just keep this hack for now
        if not isinstance(powerstate, int):
            if powerstate == "PICO_POWER_SUPPLY_CONNECTED":
                powerstate = 0x119
            elif powerstate == "PICO_POWER_SUPPLY_NOT_CONNECTED":
                powerstate = 0x11A
        self._lowLevelChangePowerSource(powerstate)

    ###Error codes - copied from PS6000 programmers manual.
    #To get formatting correct do following copy-replace in Programmers Notepad
    #1. Copy/replace ' - ' with '", "'
    #2. Copy/replace '\r' with '"],\r' (enable slash expressions when doing this)
    #3. Copy/replace '^([0-9A-F]{2} ){1}' with '0x\1, "' (enable regex when doing this)
    #4. Copy/replace '^([0-9A-F]{3} ){1}' with '0x\1, "' (enable regex when doing this)
    #5. Copy/repplace '0x' with '[0x'
    ERROR_CODES = [[0x00 , "PICO_OK", "The PicoScope XXXX is functioning correctly."],
        [0x01 , "PICO_MAX_UNITS_OPENED", "An attempt has been made to open more than PSXXXX_MAX_UNITS."],
        [0x02 , "PICO_MEMORY_FAIL", "Not enough memory could be allocated on the host machine."],
        [0x03 , "PICO_NOT_FOUND", "No PicoScope XXXX could be found."],
        [0x04 , "PICO_FW_FAIL", "Unable to download firmware."],
        [0x05 , "PICO_OPEN_OPERATION_IN_PROGRESS"],
        [0x06 , "PICO_OPERATION_FAILED"],
        [0x07 , "PICO_NOT_RESPONDING", "The PicoScope XXXX is not responding to commands from the PC."],
        [0x08 , "PICO_CONFIG_FAIL", "The configuration information in the PicoScope XXXX has become corrupt or is missing."],
        [0x09 , "PICO_KERNEL_DRIVER_TOO_OLD", "The picopp.sys file is too old to be used with the device driver."],
        [0x0A , "PICO_EEPROM_CORRUPT", "The EEPROM has become corrupt, so the device will use a default setting."],
        [0x0B , "PICO_OS_NOT_SUPPORTED", "The operating system on the PC is not supported by this driver."],
        [0x0C , "PICO_INVALID_HANDLE", "There is no device with the handle value passed."],
        [0x0D , "PICO_INVALID_PARAMETER", "A parameter value is not valid."],
        [0x0E , "PICO_INVALID_TIMEBASE", "The timebase is not supported or is invalid."],
        [0x0F , "PICO_INVALID_VOLTAGE_RANGE", "The voltage range is not supported or is invalid."],
        [0x10 , "PICO_INVALID_CHANNEL", "The channel number is not valid on this device or no channels have been set."],
        [0x11 , "PICO_INVALID_TRIGGER_CHANNEL", "The channel set for a trigger is not available on this device."],
        [0x12 , "PICO_INVALID_CONDITION_CHANNEL", "The channel set for a condition is not available on this device."],
        [0x13 , "PICO_NO_SIGNAL_GENERATOR", "The device does not have a signal generator."],
        [0x14 , "PICO_STREAMING_FAILED", "Streaming has failed to start or has stopped without user request."],
        [0x15 , "PICO_BLOCK_MODE_FAILED", "Block failed to start", "a parameter may have been set wrongly."],
        [0x16 , "PICO_NULL_PARAMETER", "A parameter that was required is NULL."],
        [0x18 , "PICO_DATA_NOT_AVAILABLE", "No data is available from a run block call."],
        [0x19 , "PICO_STRING_BUFFER_TOO_SMALL", "The buffer passed for the information was too small."],
        [0x1A , "PICO_ETS_NOT_SUPPORTED", "ETS is not supported on this device."],
        [0x1B , "PICO_AUTO_TRIGGER_TIME_TOO_SHORT", "The auto trigger time is less than the time it will take to collect the pre-trigger data."],
        [0x1C , "PICO_BUFFER_STALL", "The collection of data has stalled as unread data would be overwritten."],
        [0x1D , "PICO_TOO_MANY_SAMPLES", "Number of samples requested is more than available in the current memory segment."],
        [0x1E , "PICO_TOO_MANY_SEGMENTS", "Not possible to create number of segments requested."],
        [0x1F , "PICO_PULSE_WIDTH_QUALIFIER", "A null pointer has been passed in the trigger function or one of the parameters is out of range."],
        [0x20 , "PICO_DELAY", "One or more of the hold-off parameters are out of range."],
        [0x21 , "PICO_SOURCE_DETAILS", "One or more of the source details are incorrect."],
        [0x22 , "PICO_CONDITIONS", "One or more of the conditions are incorrect."],
        [0x23 , "PICO_USER_CALLBACK", "The driver's thread is currently in the psXXXXBlockReady callback function and therefore the action cannot be carried out."],
        [0x24 , "PICO_DEVICE_SAMPLING", "An attempt is being made to get stored data while streaming. Either stop streaming by calling psXXXXStop, or use psXXXXGetStreamingLatestValues."],
        [0x25 , "PICO_NO_SAMPLES_AVAILABLE", "because a run has not been completed."],
        [0x26 , "PICO_SEGMENT_OUT_OF_RANGE", "The memory index is out of range."],
        [0x27 , "PICO_BUSY", "Data cannot be returned yet."],
        [0x28 , "PICO_STARTINDEX_INVALID", "The start time to get stored data is out of range."],
        [0x29 , "PICO_INVALID_INFO", "The information number requested is not a valid number."],
        [0x2A , "PICO_INFO_UNAVAILABLE", "The handle is invalid so no information is available about the device. Only PICO_DRIVER_VERSION is available."],
        [0x2B , "PICO_INVALID_SAMPLE_INTERVAL", "The sample interval selected for streaming is out of range."],
        [0x2D , "PICO_MEMORY", "Driver cannot allocate memory."],
        [0x2E , "PICO_SIG_GEN_PARAM", "Incorrect parameter passed to signal generator."],
        [0x34 , "PICO_WARNING_AUX_OUTPUT_CONFLICT", "AUX cannot be used as input and output at the same time."],
        [0x35 , "PICO_SIGGEN_OUTPUT_OVER_VOLTAGE", "The combined peak to peak voltage and the analog offset voltage exceed the allowable voltage the signal generator can produce."],
        [0x36 , "PICO_DELAY_NULL", "NULL pointer passed as delay parameter."],
        [0x37 , "PICO_INVALID_BUFFER", "The buffers for overview data have not been set while streaming."],
        [0x38 , "PICO_SIGGEN_OFFSET_VOLTAGE", "The analog offset voltage is out of range."],
        [0x39 , "PICO_SIGGEN_PK_TO_PK", "The analog peak to peak voltage is out of range."],
        [0x3A , "PICO_CANCELLED", "A block collection has been cancelled."],
        [0x3B , "PICO_SEGMENT_NOT_USED", "The segment index is not currently being used."],
        [0x3C , "PICO_INVALID_CALL", "The wrong GetValues function has been called for the collection mode in use."],
        [0x3F , "PICO_NOT_USED", "The function is not available."],
        [0x40 , "PICO_INVALID_SAMPLERATIO", "The aggregation ratio requested is out of range."],
        [0x41 , "PICO_INVALID_STATE", "Device is in an invalid state."],
        [0x42 , "PICO_NOT_ENOUGH_SEGMENTS", "The number of segments allocated is fewer than the number of captures requested."],
        [0x43 , "PICO_DRIVER_FUNCTION", "You called a driver function while another driver function was still being processed."],
        [0x45 , "PICO_INVALID_COUPLING", "An invalid coupling type was specified in psXXXXSetChannel."],
        [0x46 , "PICO_BUFFERS_NOT_SET", "An attempt was made to get data before a data buffer was defined."],
        [0x47 , "PICO_RATIO_MODE_NOT_SUPPORTED", "The selected downsampling mode (used for data reduction) is not allowed."],
        [0x49 , "PICO_INVALID_TRIGGER_PROPERTY", "An invalid parameter was passed to psXXXXSetTriggerChannelProperties."],
        [0x4A , "PICO_INTERFACE_NOT_CONNECTED", "The driver was unable to contact the oscilloscope."],
        [0x4D , "PICO_SIGGEN_WAVEFORM_SETUP_FAILED", "A problem occurred in psXXXXSetSigGenBuiltIn or psXXXXSetSigGenArbitrary."],
        [0x4E , "PICO_FPGA_FAIL"],
        [0x4F , "PICO_POWER_MANAGER"],
        [0x50 , "PICO_INVALID_ANALOGUE_OFFSET", "An impossible analogue offset value was specified in psXXXXSetChannel."],
        [0x51 , "PICO_PLL_LOCK_FAILED", "Unable to configure the PicoScope XXXX."],
        [0x52 , "PICO_ANALOG_BOARD", "The oscilloscope's analog board is not detected, or is not connected to the digital board."],
        [0x53 , "PICO_CONFIG_FAIL_AWG", "Unable to configure the signal generator."],
        [0x54 , "PICO_INITIALISE_FPGA", "The FPGA cannot be initialized, so unit cannot be opened."],
        [0x56 , "PICO_EXTERNAL_FREQUENCY_INVALID", "The frequency for the external clock is not within ±5% of the stated value."],
        [0x57 , "PICO_CLOCK_CHANGE_ERROR", "The FPGA could not lock the clock signal."],
        [0x58 , "PICO_TRIGGER_AND_EXTERNAL_CLOCK_CLASH", "You are trying to configure the AUX input as both a trigger and a reference clock."],
        [0x59 , "PICO_PWQ_AND_EXTERNAL_CLOCK_CLASH", "You are trying to configure the AUX input as both a pulse width qualifier and a reference clock."],
        [0x5A , "PICO_UNABLE_TO_OPEN_SCALING_FILE", "The scaling file set can not be opened."],
        [0x5B , "PICO_MEMORY_CLOCK_FREQUENCY", "The frequency of the memory is reporting incorrectly."],
        [0x5C , "PICO_I2C_NOT_RESPONDING", "The I2C that is being actioned is not responding to requests."],
        [0x5D , "PICO_NO_CAPTURES_AVAILABLE", "There are no captures available and therefore no data can be returned."],
        [0x5E , "PICO_NOT_USED_IN_THIS_CAPTURE_MODE", "The capture mode the device is currently running in does not support the current request."],
        [0x103 , "PICO_GET_DATA_ACTIVE", "Reserved"],
        [0x104 , "PICO_IP_NETWORKED", "The device is currently connected via the IP Network socket and thus the call made is not supported."],
        [0x105 , "PICO_INVALID_IP_ADDRESS", "An IP address that is not correct has been passed to the driver."],
        [0x106 , "PICO_IPSOCKET_FAILED", "The IP socket has failed."],
        [0x107 , "PICO_IPSOCKET_TIMEDOUT", "The IP socket has timed out."],
        [0x108 , "PICO_SETTINGS_FAILED", "The settings requested have failed to be set."],
        [0x109 , "PICO_NETWORK_FAILED", "The network connection has failed."],
        [0x10A , "PICO_WS2_32_DLL_NOT_LOADED", "Unable to load the WS2 dll."],
        [0x10B , "PICO_INVALID_IP_PORT", "The IP port is invalid."],
        [0x10C , "PICO_COUPLING_NOT_SUPPORTED", "The type of coupling requested is not supported on the opened device."],
        [0x10D , "PICO_BANDWIDTH_NOT_SUPPORTED", "Bandwidth limit is not supported on the opened device."],
        [0x10E , "PICO_INVALID_BANDWIDTH", "The value requested for the bandwidth limit is out of range."],
        [0x10F , "PICO_AWG_NOT_SUPPORTED", "The device does not have an arbitrary waveform generator."],
        [0x110 , "PICO_ETS_NOT_RUNNING", "Data has been requested with ETS mode set but run block has not been called, or stop has been called."],
        [0x111 , "PICO_SIG_GEN_WHITENOISE_NOT_SUPPORTED", "White noise is not supported on the opened device."],
        [0x112 , "PICO_SIG_GEN_WAVETYPE_NOT_SUPPORTED", "The wave type requested is not supported by the opened device."],
        [0x116 , "PICO_SIG_GEN_PRBS_NOT_SUPPORTED", "Siggen does not generate pseudorandom bit stream."],
        [0x117 , "PICO_ETS_NOT_AVAILABLE_WITH_LOGIC_CHANNELS", "When a digital port is enabled, ETS sample mode is not available for use."],
        [0x118 , "PICO_WARNING_REPEAT_VALUE", "Not applicable to this device."],
        [0x119 , "PICO_POWER_SUPPLY_CONNECTED", "The DC power supply is connected."],
        [0x11A , "PICO_POWER_SUPPLY_NOT_CONNECTED", "The DC power supply isn’t connected."],
        [0x11B , "PICO_POWER_SUPPLY_REQUEST_INVALID", "Incorrect power mode passed for current power source."],
        [0x11C , "PICO_POWER_SUPPLY_UNDERVOLTAGE", "The supply voltage from the USB source is too low."],
        [0x11D , "PICO_CAPTURING_DATA", "The device is currently busy capturing data."],
        [0x11E , "PICO_USB3_0_DEVICE_NON_USB3_0_PORT", "You must connect the device to a USB 3.0 port, or call ps4000aChangePowerSource to switch the device into non-USB 3.0-power mode"],
        [0x11F , "PICO_NOT_SUPPORTED_BY_THIS_DEVICE", "A function has been called that is not supported by the current device variant."],
        [0x120 , "PICO_INVALID_DEVICE_RESOLUTION", "The device resolution is invalid (out of range)."],
        [0x121 , "PICO_INVALID_NUMBER_CHANNELS_FOR_RESOLUTION", "The number of channels which can be enabled is limited in 15 and 16-bit modes"],
        [0x122 , "PICO_CHANNEL_DISABLED_DUE_TO_USB_POWERED", "USB Power not sufficient to power all channels."]]
