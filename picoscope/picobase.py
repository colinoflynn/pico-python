# -*- coding: utf-8 -*-
"""
This is the base class that all picoscope modules use.

As much logic as possible is put into this file.
At minimum each instrument file requires you to modify the name of the API
function call (e.g. ps6000xxxx vs ps4000xxxx).

This is to force the authors of the instrument files to actually read the
documentation as opposed to assuming similarities between scopes.

You can find pico-python at github.com/colinoflynn/pico-python .
"""

from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import inspect
import time

import numpy as np

from .error_codes import ERROR_CODES as _ERROR_CODES


"""
pico-python is Copyright (c) 2013-2014 By:
Colin O'Flynn <coflynn@newae.com>
Mark Harfouche <mark.harfouche@gmail.com>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

Inspired by Patrick Carle's code at
http://www.picotech.com/support/topic11239.html
which was adapted from
http://www.picotech.com/support/topic4926.html
"""


class _PicoscopeBase(object):
    """
    This class defines a general interface for Picoscope oscilloscopes.

    This  class should not be called directly since it relies on lower level
    functions to communicate with the actual devices.

    """

    #########################################################
    # You must reimplement this in device specific classes
    #########################################################

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

    BW_LIMITS = {"Full": 0, "20MHZ": 1}

    ############################################################
    # End of things you must reimplement (I think).
    ############################################################

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

    # getUnitInfo parameter types
    UNIT_INFO_TYPES = {"DriverVersion": 0x0,
                       "USBVersion": 0x1,
                       "HardwareVersion": 0x2,
                       "VariantInfo": 0x3,
                       "BatchAndSerial": 0x4,
                       "CalDate": 0x5,
                       "KernelVersion": 0x6,
                       "DigitalHardwareVersion": 0x7,
                       "AnalogueHardwareVersion": 0x8,
                       "PicoFirmwareVersion1": 0x9,
                       "PicoFirmwareVersion2": 0xA}

    def __init__(self, serialNumber=None, connect=True):
        """Create a the scope object, and by default also connect to it."""
        # TODO: Make A class for each channel
        # that way the settings will make more sense

        # These do not correspond to API values, but rather to
        # the "true" voltage as seen at the oscilloscope probe
        self.CHRange = [5.0] * self.NUM_CHANNELS
        self.CHOffset = [0.0] * self.NUM_CHANNELS
        self.CHCoupling = [1] * self.NUM_CHANNELS
        self.ProbeAttenuation = [1.0] * self.NUM_CHANNELS

        self.handle = None

        if connect is True:
            self.open(serialNumber)

    def getUnitInfo(self, info):
        """Return: A string containing the requested information."""
        if not isinstance(info, int):
            info = self.UNIT_INFO_TYPES[info]
        return self._lowLevelGetUnitInfo(info)

    def getMaxValue(self):
        """Return the maximum ADC value, used for scaling."""
        # TODO: make this more consistent accross versions
        # This was a "fix" when we started supported PS5000a
        return self.MAX_VALUE

    def getMinValue(self):
        """Return the minimum ADC value, used for scaling."""
        return self.MIN_VALUE

    def getAllUnitInfo(self):
        """Return: human readible unit information as a string."""
        s = ""
        for key in sorted(self.UNIT_INFO_TYPES.keys(),
                          key=self.UNIT_INFO_TYPES.get):
            s += key.ljust(30) + ": " + self.getUnitInfo(key) + "\n"

        s = s[:-1]
        return s

    def setChannel(self, channel='A', coupling="AC", VRange=2.0,
                   VOffset=0.0, enabled=True, BWLimited=0,
                   probeAttenuation=1.0):
        """
        Set up a specific chthe scopeannel.

        It finds the smallest range that is capable of accepting your signal.
        Return actual range of the scope as double.

        The VOffset, is an offset that the scope will ADD to your signal.

        If using a probe (or a sense resitor), the probeAttenuation value is
        used to find the approriate channel range on the scope to use.

        e.g. to use a 10x attenuation probe, you must supply the following
        parameters ps.setChannel('A', "DC", 20.0, 5.0, True, False, 10.0)

        The scope will then be set to use the +- 2V mode at the scope allowing
        you to measure your signal from -25V to +15V.
        After this point, you can set everything in terms of units as seen at
        the tip of the probe. For example, you can set a trigger of 15V and it
        will trigger at the correct value.

        When using a sense resistor, lets say R = 1.3 ohm, you obtain the
        relation:
        V = IR, meaning that your probe as an attenuation of R compared to the
        current you are trying to measure.

        You should supply probeAttenuation = 1.3
        The rest of your units should be specified in amps.

        Unfortunately, you still have to supply a VRange that is very close to
        the allowed values. This will change in furture version where we will
        find the next largest range to accomodate the desired range.

        Note that if you set a channel to use AC coupling, you may need
        to make a "dummy call" to runBlock, or the first batch of data
        returned via getData* may be inaccurate.
        See https://www.picotech.com/support/topic35401.html for more details.

        If you want to use units of mA, supply a probe attenuation of 1.3E3.
        Note, the authors recommend sticking to SI units because it makes it
        easier to guess what units each parameter is in.

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

        # finds the next largest range
        VRangeAPI = None
        for item in self.CHANNEL_RANGE:
            if item["rangeV"] - VRange / probeAttenuation > -1E-4:
                if VRangeAPI is None:
                    VRangeAPI = item
                    # break
                # Don't know if this is necessary assuming that it will iterate
                # in order
                elif VRangeAPI["rangeV"] > item["rangeV"]:
                    VRangeAPI = item

        if VRangeAPI is None:
            raise ValueError(
                "Desired range %f is too large. Maximum range is %f." %
                (VRange, self.CHANNEL_RANGE[-1]["rangeV"] * probeAttenuation))

        # store the actually chosen range of the scope
        VRange = VRangeAPI["rangeV"] * probeAttenuation

        if not isinstance(BWLimited, int):
            BWLimited = self.BW_LIMITS[BWLimited]

        if BWLimited == 3:
            BWLimited = 3  # 1MHz Bandwidth Limiter for PicoScope 4444
        elif BWLimited == 2:
            BWLimited = 2  # Bandwidth Limiter for PicoScope 6404,
            # 100kHz Bandwidth Limiter for PicoScope 4444
        elif BWLimited == 1:
            BWLimited = 1  # Bandwidth Limiter for PicoScope 6402/6403,
            # 20kHz Bandwidth Limiter for PicoScope 4444
        else:
            BWLimited = 0

        self._lowLevelSetChannel(chNum, enabled, coupling,
                                 VRangeAPI["apivalue"],
                                 VOffset / probeAttenuation, BWLimited)

        # if all was successful, save the parameters
        self.CHRange[chNum] = VRange
        self.CHOffset[chNum] = VOffset
        self.CHCoupling[chNum] = coupling
        self.ProbeAttenuation[chNum] = probeAttenuation

        return VRange

    def runBlock(self, pretrig=0.0, segmentIndex=0):
        """Run a single block.

        Must have already called setSampling for proper setup.
        """
        # getting max samples is riddiculous.
        # 1GS buffer means it will take so long
        nSamples = min(self.noSamples, self.maxSamples)

        # to return the same No. Samples ( if pretrig != 0.0 ) I'm wrong ?
        nSamples_pretrig = int(round(nSamples * pretrig))
        self._lowLevelRunBlock(nSamples_pretrig,
                               nSamples - nSamples_pretrig,
                               self.timebase, self.oversample, segmentIndex)

    def isReady(self):
        """
        Check if scope done.

        Returns: bool.

        """
        return self._lowLevelIsReady()

    def waitReady(self, spin_delay=0.01):
        """Block until the scope is ready."""
        while not self.isReady():
            time.sleep(spin_delay)

    def setSamplingInterval(self, sampleInterval, duration, oversample=0,
                            segmentIndex=0):
        """Return (actualSampleInterval, noSamples, maxSamples)."""
        self.oversample = oversample
        self.timebase = self.getTimeBaseNum(sampleInterval)

        timebase_dt = self.getTimestepFromTimebase(self.timebase)

        noSamples = int(round(duration / timebase_dt))

        (self.sampleInterval, self.maxSamples) = self._lowLevelGetTimebase(
            self.timebase, noSamples, oversample, segmentIndex)

        self.noSamples = noSamples
        self.sampleRate = 1.0 / self.sampleInterval
        return (self.sampleInterval, self.noSamples, self.maxSamples)

    def setSamplingFrequency(self, sampleFreq, noSamples, oversample=0,
                             segmentIndex=0):
        """Return (actualSampleFreq, maxSamples)."""
        # TODO: make me more like the functions above
        #       at least in terms of what I return
        sampleInterval = 1.0 / sampleFreq
        duration = noSamples * sampleInterval
        self.setSamplingInterval(sampleInterval, duration, oversample,
                                 segmentIndex)
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

    def setExtTriggerRange(self, VRange=0.5):
        """ This function sets the range for the EXT trigger channel

            This is only implemented for PS4000 series devices where
            the only acceptable values for VRange are 0.5 or 5.0
        """
        VRangeAPI = None
        for item in self.CHANNEL_RANGE:
            if np.isclose(item["rangeV"], VRange):
                VRangeAPI = item
                break

        if VRangeAPI is None:
            raise ValueError('Provided VRange is not valid')

        self._lowLevelSetExtTriggerRange(VRangeAPI["apivalue"])

    def setSimpleTrigger(self, trigSrc, threshold_V=0, direction="Rising",
                         delay=0, timeout_ms=100, enabled=True):
        """Set up a simple trigger.

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

        Note, the AUX port (or EXT) only has a range of +- 1V
        (at least in PS6000)
        """
        if not isinstance(trigSrc, int):
            trigSrc = self.CHANNELS[trigSrc]

        if not isinstance(direction, int):
            direction = self.THRESHOLD_TYPE[direction]

        if trigSrc >= self.NUM_CHANNELS:
            threshold_adc = int((threshold_V / self.EXT_RANGE_VOLTS) *
                                self.EXT_MAX_VALUE)

            # The external port is typically used as a clock. So I don't think
            # we should raise errors
            threshold_adc = min(threshold_adc, self.EXT_MAX_VALUE)
            threshold_adc = max(threshold_adc, self.EXT_MIN_VALUE)
        else:
            a2v = self.CHRange[trigSrc] / self.getMaxValue()
            threshold_adc = int((threshold_V + self.CHOffset[trigSrc]) / a2v)

            if (threshold_adc > self.getMaxValue() or
               threshold_adc < self.getMinValue()):
                raise IOError(
                    "Trigger Level of %fV outside allowed range (%f, %f)" % (
                        threshold_V,
                        -self.CHRange[trigSrc] - self.CHOffset[trigSrc],
                        +self.CHRange[trigSrc] - self.CHOffset[trigSrc]))

        enabled = int(bool(enabled))

        self._lowLevelSetSimpleTrigger(enabled, trigSrc, threshold_adc,
                                       direction, delay, timeout_ms)

    def getTriggerTimeOffset(self, segmentIndex=0):
        return self._lowLevelGetTriggerTimeOffset(segmentIndex)

    def flashLed(self, times=5, start=False, stop=False):
        """Flash the front panel LEDs.

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

    def getScaleAndOffset(self, channel):
        """Return the scale and offset used to convert the raw waveform.

        To use: first multiply by the scale, then subtract the offset

        Returns a dictionary with keys scale and offset
        """
        if not isinstance(channel, int):
            channel = self.CHANNELS[channel]
        return {'scale': self.CHRange[channel] / float(self.getMaxValue()),
                'offset': self.CHOffset[channel]}

    def rawToV(self, channel, dataRaw, dataV=None, dtype=np.float64):
        """Convert the raw data to voltage units. Return as numpy array."""
        if not isinstance(channel, int):
            channel = self.CHANNELS[channel]

        if dataV is None:
            dataV = np.empty(dataRaw.shape, dtype=dtype)

        a2v = self.CHRange[channel] / dtype(self.getMaxValue())
        np.multiply(dataRaw, a2v, dataV)
        np.subtract(dataV, self.CHOffset[channel], dataV)

        return dataV

    def getDataV(self, channel, numSamples=0, startIndex=0, downSampleRatio=1,
                 downSampleMode=0, segmentIndex=0, returnOverflow=False,
                 exceptOverflow=False, dataV=None, dataRaw=None,
                 dtype=np.float64):
        """Return the data as an array of voltage values.

        it returns (dataV, overflow) if returnOverflow = True
        else, it returns returns dataV
        dataV is an array with size numSamplesReturned
        overflow is a flag that is true when the signal was either too large
                 or too small to be properly digitized

        if exceptOverflow is true, an IOError exception is raised on overflow
        if returnOverflow is False. This allows you to detect overflows at
        higher layers w/o complicated return trees. You cannot however read the
        'good' data, you only get the exception information then.
        """
        (dataRaw, numSamplesReturned, overflow) = self.getDataRaw(
            channel, numSamples, startIndex, downSampleRatio, downSampleMode,
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

    def getDataRaw(self, channel='A', numSamples=0, startIndex=0,
                   downSampleRatio=1, downSampleMode=0, segmentIndex=0,
                   data=None):
        """Return the data in the purest form.

        It returns a tuple containing:
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
                raise ValueError(
                    'Provided array must be at least as big as numSamples.')
            # see numpy.ndarray.flags
            if data.flags['CARRAY'] is False:
                raise TypeError('Provided array must be c_contiguous,' +
                                ' aligned and writeable.')

        self._lowLevelSetDataBuffer(channel, data, downSampleMode,
                                    segmentIndex)

        (numSamplesReturned, overflow) = self._lowLevelGetValues(
            numSamples, startIndex, downSampleRatio, downSampleMode,
            segmentIndex)
        # necessary or else the next call to getValues will try to fill
        # this array unless it is a call trying to read the same channel.
        self._lowLevelClearDataBuffer(channel, segmentIndex)

        # overflow is a bitwise mask
        overflow = bool(overflow & (1 << channel))

        return (data, numSamplesReturned, overflow)

    def getDataRawBulk(self, channel='A', numSamples=0, fromSegment=0,
                       toSegment=None, downSampleRatio=1, downSampleMode=0,
                       data=None):
        """Get data recorded in block mode."""
        if not isinstance(channel, int):
            channel = self.CHANNELS[channel]
        if toSegment is None:
            toSegment = self.noSegments - 1
        if numSamples == 0:
            numSamples = min(self.maxSamples, self.noSamples)

        numSegmentsToCopy = toSegment - fromSegment + 1
        if data is None:
            data = np.ascontiguousarray(
                np.zeros((numSegmentsToCopy, numSamples), dtype=np.int16))

        # set up each row in the data array as a buffer for one of
        # the memory segments in the scope
        for i, segment in enumerate(range(fromSegment, toSegment + 1)):
            self._lowLevelSetDataBufferBulk(channel,
                                            data[i],
                                            segment,
                                            downSampleMode)
        overflow = np.ascontiguousarray(
            np.zeros(numSegmentsToCopy, dtype=np.int16))

        self._lowLevelGetValuesBulk(numSamples, fromSegment, toSegment,
                                    downSampleRatio, downSampleMode, overflow)

        # don't leave the API thinking these can be written to later
        for i, segment in enumerate(range(fromSegment, toSegment + 1)):
            self._lowLevelClearDataBuffer(channel, segment)

        return (data, numSamples, overflow)

    def setSigGenBuiltInSimple(self,
                               offsetVoltage=0, pkToPk=2, waveType="Sine",
                               frequency=1E6, shots=1, triggerType="Rising",
                               triggerSource="None", stopFreq=None,
                               increment=10.0, dwellTime=1E-3, sweepType="Up",
                               numSweeps=0):
        """Generate simple signals using the built-in waveforms.

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

        self._lowLevelSetSigGenBuiltInSimple(
            offsetVoltage, pkToPk, waveType, frequency, shots, triggerType,
            triggerSource, stopFreq, increment, dwellTime, sweepType,
            numSweeps)

    def setAWGSimple(self, waveform, duration, offsetVoltage=None,
                     pkToPk=None, indexMode="Single", shots=1,
                     triggerType="Rising", triggerSource="ScopeTrig"):
        """Set the AWG to output your desired wavefrom.

        If you require precise control of the timestep increment, you should
        use setSigGenAritrarySimpleDelaPhase instead

        Check setSigGenAritrarySimpleDelaPhase for parameter explanation

        Returns:
            The actual duration of the waveform

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

        actual_druation = self.setAWGSimpleDeltaPhase(
            waveform, deltaPhase, offsetVoltage, pkToPk, indexMode, shots,
            triggerType, triggerSource)

        return (actual_druation, deltaPhase)

    def setAWGSimpleDeltaPhase(self, waveform, deltaPhase, offsetVoltage=None,
                               pkToPk=None, indexMode="Single", shots=1,
                               triggerType="Rising",
                               triggerSource="ScopeTrig"):
        """Specify deltaPhase between each sample and not the total waveform
        duration.

        Returns the actual time duration of the waveform

        If pkToPk and offset Voltage are both set to None, then their values
        are computed as

        pkToPk = np.max(waveform) - np.min(waveform)
        offset = (np.max(waveform) + np.min(waveform)) / 2

        This should in theory minimize the quantization error in the ADC.

        else, the waveform shoudl be a numpy int16 type array with the
        containing waveform

        For the Quad mode, if offset voltage is not provided, then waveform[0]
        is assumed to be the offset. In quad mode, the offset voltage is the
        point of symmetry

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
        evenly spaced samples at the expense of the precise duration of the
        your waveform
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
        This part of the code is written for the PS6403
        (PS6403B if that matters)
        I don't really know a good way to differentiate between PS6403 versions

        It essentially does some autoscaling for the waveform so that it can be
        sent to the Picoscope to allow for maximum resolution from the DDS.

        I haven't tested if you can actually obtain more resolution than simply
        setting the DDS to output from -2 to +2

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
                pkToPk = 2.0
                # TODO: make this a per scope function assuming 2.0 V AWG
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

        self._lowLevelSetAWGSimpleDeltaPhase(
            waveform, deltaPhase, offsetVoltage, pkToPk, indexMode, shots,
            triggerType, triggerSource)

        timeIncrement = self.getAWGTimeIncrement(deltaPhase)
        waveform_duration = timeIncrement * len(waveform)

        if indexMode == self.AWG_INDEX_MODES["Single"]:
            pass
        elif indexMode == self.AWG_INDEX_MODES["Dual"]:
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
                         2 ** (self.AWGPhaseAccumulatorSize -
                               self.AWGBufferAddressWidth))
        return deltaPhase

    def getAWGTimeIncrement(self, deltaPhase):
        """
        Return the time between AWG samples given a certain deltaPhase.

        You should use this function in conjunction with
        getAWGDeltaPhase to obtain the actual timestep of AWG.

        """
        samplingFrequency = deltaPhase * self.AWGDACFrequency / (
            2 ** (self.AWGPhaseAccumulatorSize - self.AWGBufferAddressWidth))
        return 1 / samplingFrequency

    def sigGenSoftwareControl(self, state=True):
        """
        Trigger the AWG when configured with software triggering.
        """
        self._lowLevelSigGenSoftwareControl(state)

    def setResolution(self, resolution):
        """For 5000-series or certain 4000-series scopes ONLY,
        sets the resolution.
        """
        self._lowLevelSetDeviceResolution(self.ADC_RESOLUTIONS[resolution])

    def enumerateUnits(self):
        """Enumerate connceted units.

        Return serial numbers as list of strings.
        """
        return self._lowLevelEnumerateUnits()

    def ping(self):
        """Ping unit to check that the already opened device is connected."""
        return self._lowLevelPingUnit()

    def open(self, serialNumber=None):
        """Open the scope, using a serialNumber if given."""
        self._lowLevelOpenUnit(serialNumber)

    def openUnitAsync(self, serialNumber=None):
        """Open the scope asynchronously."""
        self._lowLevelOpenUnitAsync(serialNumber)

    def openUnitProgress(self):
        """Return a tuple (progress, completed)."""
        return self._lowLevelOpenUnitProgress()

    def close(self):
        """
        Close the scope.

        You should call this yourself because the Python garbage collector
        might take some time.

        """
        if self.handle is not None:
            self._lowLevelCloseUnit()
            self.handle = None

    def stop(self):
        """Stop scope acquisition."""
        self._lowLevelStop()

    def __del__(self):
        self.close()

    def checkResult(self, ec):
        """Check result of function calls, raise exception if not 0."""
        # NOTE: This will break some oscilloscopes that are powered by USB.
        # Some of the newer scopes, can actually be powered by USB and will
        # return a useful value. That should be given back to the user.
        # I guess we can deal with these edge cases in the functions themselves
        if ec == 0:
            return

        else:
            # print("Error Num: 0x%x"%ec)
            ecName = self.errorNumToName(ec)
            ecDesc = self.errorNumToDesc(ec)
            raise IOError('Error calling %s: %s (%s)' % (
                str(inspect.stack()[1][3]), ecName, ecDesc))

    def errorNumToName(self, num):
        """Return the name of the error as a string."""
        for t in self.ERROR_CODES:
            if t[0] == num:
                return t[1]

    def errorNumToDesc(self, num):
        """Return the description of the error as a string."""
        for t in self.ERROR_CODES:
            if t[0] == num:
                try:
                    return t[2]
                except IndexError:
                    return ""

    def changePowerSource(self, powerstate):
        """Change the powerstate of the scope.

        Valid only for PS54XXA/B?
        """
        # I should probably make an enumerate table for these two cases,
        # but they are in fact just the
        # error codes. Picoscope should have made it a separate enumerate
        # themselves.
        # I'll just keep this hack for now
        if not isinstance(powerstate, int):
            if powerstate == "PICO_POWER_SUPPLY_CONNECTED":
                powerstate = 0x119
            elif powerstate == "PICO_POWER_SUPPLY_NOT_CONNECTED":
                powerstate = 0x11A
        self._lowLevelChangePowerSource(powerstate)

    ERROR_CODES = _ERROR_CODES
