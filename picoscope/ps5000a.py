# This is the instrument-specific file for the PS5000 series of instruments.
#
# pico-python is Copyright (c) 2013-2014 By:
# Colin O'Flynn <coflynn@newae.com>
# Mark Harfouche <mark.harfouche@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
This is the low level driver file for a specific Picoscope.

By this, I mean if parameters want to get passed as strings, they should be
handled by PSBase
All functions here should take things as close to integers as possible, the
only exception here is for array parameters. Array parameters should be passed
in a pythonic way through numpy since the PSBase class should not be aware of
the specifics behind how the clib is called.

The functions should not have any default values as these should be handled
by PSBase.
"""

from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import math

# to load the proper dll
import platform

# Do not import or use ill definied data types
# such as short int or long
# use the values specified in the h file
# float is always defined as 32 bits
# double is defined as 64 bits
from ctypes import byref, POINTER, create_string_buffer, c_float, \
    c_int16, c_int32, c_uint32, c_void_p, c_int64
from ctypes import c_int32 as c_enum

from picoscope.picobase import _PicoscopeBase


class PS5000a(_PicoscopeBase):
    """The following are low-level functions for the PS5000."""

    LIBNAME = "ps5000a"

    NUM_CHANNELS = 4
    CHANNELS = {"A": 0, "B": 1, "C": 2, "D": 3,
                "External": 4, "MaxChannels": 4, "TriggerAux": 5}

    ADC_RESOLUTIONS = {"8": 0, "12": 1, "14": 2, "15": 3, "16": 4}

    CHANNEL_RANGE = [{"rangeV": 10E-3, "apivalue": 0, "rangeStr": "10 mV"},
                     {"rangeV": 20E-3, "apivalue": 1, "rangeStr": "20 mV"},
                     {"rangeV": 50E-3, "apivalue": 2, "rangeStr": "50 mV"},
                     {"rangeV": 100E-3, "apivalue": 3, "rangeStr": "100 mV"},
                     {"rangeV": 200E-3, "apivalue": 4, "rangeStr": "200 mV"},
                     {"rangeV": 500E-3, "apivalue": 5, "rangeStr": "500 mV"},
                     {"rangeV": 1.0, "apivalue": 6, "rangeStr": "1 V"},
                     {"rangeV": 2.0, "apivalue": 7, "rangeStr": "2 V"},
                     {"rangeV": 5.0, "apivalue": 8, "rangeStr": "5 V"},
                     {"rangeV": 10.0, "apivalue": 9, "rangeStr": "10 V"},
                     {"rangeV": 20.0, "apivalue": 10, "rangeStr": "20 V"},
                     {"rangeV": 50.0, "apivalue": 11, "rangeStr": "50 V"},
                     ]

    CHANNEL_COUPLINGS = {"DC": 1, "AC": 0}

    # has_sig_gen = True
    WAVE_TYPES = {"Sine": 0, "Square": 1, "Triangle": 2,
                  "RampUp": 3, "RampDown": 4,
                  "Sinc": 5, "Gaussian": 6, "HalfSine": 7, "DCVoltage": 8,
                  "WhiteNoise": 9}

    SWEEP_TYPES = {"Up": 0, "Down": 1, "UpDown": 2, "DownUp": 3}

    SIGGEN_TRIGGER_TYPES = {"Rising": 0, "Falling": 1,
                            "GateHigh": 2, "GateLow": 3}
    SIGGEN_TRIGGER_SOURCES = {"None": 0, "ScopeTrig": 1, "AuxIn": 2,
                              "ExtIn": 3, "SoftTrig": 4, "TriggerRaw": 5}

    # This is actually different depending on the AB/CD models
    # I wonder how we could detect the difference between the oscilloscopes
    # I believe we can obtain this information from the setInfo function
    # by readign the hardware version
    # for the PS6403B version, the hardware version is "1 1",
    # an other possibility is that the PS6403B shows up as 6403 when using
    # VARIANT_INFO and others show up as PS6403X where X = A,C or D

    AWGPhaseAccumulatorSize = 32

    AWGDACInterval = 5E-9  # in seconds
    AWGDACFrequency = 1 / AWGDACInterval

    AWG_INDEX_MODES = {"Single": 0, "Dual": 1, "Quad": 2}

    MAX_VALUE_8BIT = 32512
    MIN_VALUE_8BIT = -32512
    MAX_VALUE_OTHER = 32767
    MIN_VALUE_OTHER = -32767

    EXT_RANGE_VOLTS = 5

    def __init__(self, serialNumber=None, connect=True):
        """Load DLL etc."""
        if platform.system() == 'Linux':
            from ctypes import cdll
            self.lib = cdll.LoadLibrary("lib" + self.LIBNAME + ".so")
        elif platform.system() == 'Darwin':
            from picoscope.darwin_utils import LoadLibraryDarwin
            self.lib = LoadLibraryDarwin("lib" + self.LIBNAME + ".dylib")
        else:
            from ctypes import windll
            from ctypes.util import find_library
            self.lib = windll.LoadLibrary(
                find_library(str(self.LIBNAME + ".dll"))
            )

        self.resolution = self.ADC_RESOLUTIONS["8"]

        super(PS5000a, self).__init__(serialNumber, connect)

    def _lowLevelOpenUnit(self, serialNumber):
        c_handle = c_int16()
        if serialNumber is not None:
            serialNumberStr = create_string_buffer(bytes(serialNumber,
                                                         encoding='utf-8'))
        else:
            serialNumberStr = None
        # Passing None is the same as passing NULL
        m = self.lib.ps5000aOpenUnit(byref(c_handle), serialNumberStr,
                                     self.resolution)
        self.handle = c_handle.value

        # This will check if the power supply is not connected
        # and change the power supply accordingly
        # Personally (me = Mark), I don't like this
        # since the user should address this immediately, and we
        # shouldn't let this go as a soft error
        # but I think this should do for now
        if m == 0x11A:
            self.changePowerSource(m)
        else:
            self.checkResult(m)

        # B models have different AWG buffer sizes
        # 5242B, 5442B: 2**14
        # 5243B, 5443B: 2**15
        # 5444B, 5244B: 3 * 2**14
        # Model 5444B identifies itself properly in VariantInfo, I will assume
        # the others do as well.

        self.model = self.getUnitInfo('VariantInfo')
        # print("Checking variant, found: " + str(self.model))
        if self.model in ('5244B', '5444B'):
            self.AWGBufferAddressWidth = math.log(3 * 2**14, 2)
            self.AWGMaxVal = 32767
            self.AWGMinVal = -32768
            self.AWGMaxSamples = 49152
        elif self.model in ('5243B', '5443B', '5243D', '5443D'):
            self.AWGBufferAddressWidth = 15
            self.AWGMaxVal = 32767
            self.AWGMinVal = -32768
            self.AWGMaxSamples = 2**self.AWGBufferAddressWidth
        else:
            # This is what the previous PS5000a used for all scopes.
            # I am leaving it the same, although I think the AWGMaxVal and
            # AWGMinVal issue was fixed and should be -32768 to 32767 for all
            # 5000 models
            self.AWGBufferAddressWidth = 14
            # Note this is NOT what is written in the Programming guide as of
            # version # 10_5_0_28
            # This issue was acknowledged in this thread
            # http://www.picotech.com/support/topic13217.html
            self.AWGMaxVal = 0x0FFF
            self.AWGMinVal = 0x0000
            self.AWGMaxSamples = 2**self.AWGBufferAddressWidth

    def _lowLevelCloseUnit(self):
        m = self.lib.ps5000aCloseUnit(c_int16(self.handle))
        self.checkResult(m)

    def _lowLevelSetChannel(self, chNum, enabled, coupling, VRange, VOffset,
                            bandwidth):
        m = self.lib.ps5000aSetChannel(c_int16(self.handle), c_enum(chNum),
                                       c_int16(enabled), c_enum(coupling),
                                       c_enum(VRange), c_float(VOffset))
        self.checkResult(m)

        # The error this might through are
        #    INVALID_HANDLE
        #    INVALID_CHANNEL
        #    INVALID_BANDWIDTH
        # Invalid bandwidth is the only case that could go wrong.
        # The others would be thrown above (assuming no race condition:
        # i.e. unplugging the scope in between this call.
        # I decided to keep the logic below to avoid a possible error
        # picobase/SetChannel should be changed to the following
        # Set the channel
        # save the new channel settings
        # check if ps5000a
        # change the bandwidth separately
        # changing the bandwidth would be it's own function (implemented below)
        if bandwidth:
            m = self.lib.ps5000aSetBandwidthFilter(c_int16(self.handle),
                                                   c_enum(chNum), c_enum(1))
        else:
            m = self.lib.ps5000aSetBandwidthFilter(c_int16(self.handle),
                                                   c_enum(chNum), c_enum(0))
        self.checkResult(m)

    def _lowLevelSetBandwidthFilter(self, channel, bandwidth):
        m = self.lib.ps5000aSetBandwidthFilter(c_int16(self.handle),
                                               c_enum(channel),
                                               c_enum(bandwidth))
        self.checkResult(m)

    def _lowLevelStop(self):
        m = self.lib.ps5000aStop(c_int16(self.handle))
        self.checkResult(m)

    def _lowLevelGetUnitInfo(self, info):
        s = create_string_buffer(256)
        requiredSize = c_int16(0)

        m = self.lib.ps5000aGetUnitInfo(c_int16(self.handle), byref(s),
                                        c_int16(len(s)), byref(requiredSize),
                                        c_enum(info))
        self.checkResult(m)
        if requiredSize.value > len(s):
            s = create_string_buffer(requiredSize.value + 1)
            m = self.lib.ps5000aGetUnitInfo(c_int16(self.handle), byref(s),
                                            c_int16(len(s)),
                                            byref(requiredSize), c_enum(info))
            self.checkResult(m)

        # should this bee ascii instead?
        # I think they are equivalent...
        return s.value.decode('utf-8')

    def _lowLevelFlashLed(self, times):
        m = self.lib.ps5000aFlashLed(c_int16(self.handle), c_int16(times))
        self.checkResult(m)

    def _lowLevelSetSimpleTrigger(self, enabled, trigsrc, threshold_adc,
                                  direction, delay, timeout_ms):
        m = self.lib.ps5000aSetSimpleTrigger(
            c_int16(self.handle), c_int16(enabled),
            c_enum(trigsrc), c_int16(threshold_adc),
            c_enum(direction), c_uint32(delay), c_int16(timeout_ms))
        self.checkResult(m)

    def _lowLevelRunBlock(self, numPreTrigSamples, numPostTrigSamples,
                          timebase, oversample, segmentIndex):
        # Oversample is NOT used!
        timeIndisposedMs = c_int32()
        m = self.lib.ps5000aRunBlock(
            c_int16(self.handle), c_uint32(numPreTrigSamples),
            c_uint32(numPostTrigSamples), c_uint32(timebase),
            byref(timeIndisposedMs), c_uint32(segmentIndex),
            c_void_p(), c_void_p())
        self.checkResult(m)
        return timeIndisposedMs.value

    def _lowLevelIsReady(self):
        ready = c_int16()
        m = self.lib.ps5000aIsReady(c_int16(self.handle), byref(ready))
        self.checkResult(m)
        if ready.value:
            return True
        else:
            return False

    def _lowLevelPingUnit(self):
        m = self.lib.ps5000aPingUnit(c_int16(self.handle))
        return m

    def _lowLevelGetTimebase(self, tb, noSamples, oversample, segmentIndex):
        """Return (timeIntervalSeconds, maxSamples)."""
        maxSamples = c_int32()
        sampleRate = c_float()

        m = self.lib.ps5000aGetTimebase2(c_int16(self.handle), c_uint32(tb),
                                         c_uint32(noSamples),
                                         byref(sampleRate),
                                         byref(maxSamples),
                                         c_uint32(segmentIndex))
        self.checkResult(m)

        return (sampleRate.value / 1.0E9, maxSamples.value)

    def getTimeBaseNum(self, sampleTimeS):
        """Convert sample time in S to something to pass to API Call."""
        if self.resolution == self.ADC_RESOLUTIONS["8"]:
            maxSampleTime = (((2 ** 32 - 1) - 2) / 125000000)
            if sampleTimeS < 8.0E-9:
                st = math.floor(math.log(sampleTimeS * 1E9, 2))
                st = max(st, 0)
            else:
                if sampleTimeS > maxSampleTime:
                    sampleTimeS = maxSampleTime
                st = math.floor((sampleTimeS * 125000000) + 2)

        elif self.resolution == self.ADC_RESOLUTIONS["12"]:
            maxSampleTime = (((2 ** 32 - 1) - 3) / 62500000)
            if sampleTimeS < 16.0E-9:
                st = math.floor(math.log(sampleTimeS * 5E8, 2)) + 1
                st = max(st, 1)
            else:
                if sampleTimeS > maxSampleTime:
                    sampleTimeS = maxSampleTime
                st = math.floor((sampleTimeS * 62500000) + 3)

        elif (self.resolution == self.ADC_RESOLUTIONS["14"]) or (
                self.resolution == self.ADC_RESOLUTIONS["15"]):
            maxSampleTime = (((2 ** 32 - 1) - 2) / 125000000)
            if sampleTimeS > maxSampleTime:
                sampleTimeS = maxSampleTime
            st = math.floor((sampleTimeS * 125000000) + 2)
            st = max(st, 3)

        elif self.resolution == self.ADC_RESOLUTIONS["16"]:
            maxSampleTime = (((2 ** 32 - 1) - 3) / 62500000)
            if sampleTimeS > maxSampleTime:
                sampleTimeS = maxSampleTime
            st = math.floor((sampleTimeS * 62500000) + 3)
            st = max(st, 3)

        else:
            raise ValueError("Invalid Resolution for Device?")

        # is this cast needed?
        st = int(st)
        return st

    def getTimestepFromTimebase(self, timebase):
        """Return Timestep from timebase."""
        if self.resolution == self.ADC_RESOLUTIONS["8"]:
            if timebase < 3:
                dt = 2. ** timebase / 1.0E9
            else:
                dt = (timebase - 2.0) / 125000000.
        elif self.resolution == self.ADC_RESOLUTIONS["12"]:
            if timebase < 4:
                dt = 2. ** (timebase - 1) / 5.0E8
            else:
                dt = (timebase - 3.0) / 62500000.
        elif (self.resolution == self.ADC_RESOLUTIONS["14"]) or (
                self.resolution == self.ADC_RESOLUTIONS["15"]):
            dt = (timebase - 2.0) / 125000000.
        elif self.resolution == self.ADC_RESOLUTIONS["16"]:
            dt = (timebase - 3.0) / 62500000.
        return dt

    def _lowLevelSetAWGSimpleDeltaPhase(self, waveform, deltaPhase,
                                        offsetVoltage, pkToPk, indexMode,
                                        shots, triggerType, triggerSource):
        """Waveform should be an array of shorts."""
        waveformPtr = waveform.ctypes.data_as(POINTER(c_int16))

        m = self.lib.ps5000aSetSigGenArbitrary(
            c_int16(self.handle),
            c_uint32(int(offsetVoltage * 1E6)),  # offset voltage in microvolts
            c_uint32(int(pkToPk * 1E6)),         # pkToPk in microvolts
            c_uint32(int(deltaPhase)),           # startDeltaPhase
            c_uint32(int(deltaPhase)),           # stopDeltaPhase
            c_uint32(0),                         # deltaPhaseIncrement
            c_uint32(0),                         # dwellCount
            waveformPtr,                         # arbitraryWaveform
            c_int32(len(waveform)),              # arbitraryWaveformSize
            c_enum(0),                           # sweepType for deltaPhase
            c_enum(0),            # operation (adding random noise and whatnot)
            c_enum(indexMode),                   # single, dual, quad
            c_uint32(shots),
            c_uint32(0),                         # sweeps
            c_uint32(triggerType),
            c_uint32(triggerSource),
            c_int16(0))                          # extInThreshold
        self.checkResult(m)

    def _lowLevelSetDataBuffer(self, channel, data, downSampleMode,
                               segmentIndex):
        """Set the data buffer.

        Be sure to call _lowLevelClearDataBuffer
        when you are done with the data array
        or else subsequent calls to GetValue will still use the same array.
        """
        dataPtr = data.ctypes.data_as(POINTER(c_int16))
        numSamples = len(data)

        m = self.lib.ps5000aSetDataBuffer(c_int16(self.handle),
                                          c_enum(channel),
                                          dataPtr, c_int32(numSamples),
                                          c_uint32(segmentIndex),
                                          c_enum(downSampleMode))
        self.checkResult(m)

    def _lowLevelSetDataBufferBulk(self, channel, data, segmentIndex,
                                   downSampleMode):
        """Just calls setDataBuffer with argument order changed.

        For compatibility with current picobase.py.
        """
        self._lowLevelSetDataBuffer(channel,
                                    data,
                                    downSampleMode,
                                    segmentIndex)

    def _lowLevelClearDataBuffer(self, channel, segmentIndex):
        m = self.lib.ps5000aSetDataBuffer(c_int16(self.handle),
                                          c_enum(channel),
                                          c_void_p(), c_uint32(0),
                                          c_uint32(segmentIndex),
                                          c_enum(0))
        self.checkResult(m)

    def _lowLevelGetValues(self, numSamples, startIndex, downSampleRatio,
                           downSampleMode, segmentIndex):
        numSamplesReturned = c_uint32()
        numSamplesReturned.value = numSamples
        overflow = c_int16()
        m = self.lib.ps5000aGetValues(
            c_int16(self.handle), c_uint32(startIndex),
            byref(numSamplesReturned), c_uint32(downSampleRatio),
            c_enum(downSampleMode), c_uint32(segmentIndex),
            byref(overflow))
        self.checkResult(m)
        return (numSamplesReturned.value, overflow.value)

    def _lowLevelSetSigGenBuiltInSimple(self, offsetVoltage, pkToPk, waveType,
                                        frequency, shots, triggerType,
                                        triggerSource, stopFreq, increment,
                                        dwellTime, sweepType, numSweeps):
        # TODO, I just noticed that V2 exists
        # Maybe change to V2 in the future

        if stopFreq is None:
            stopFreq = frequency

        m = self.lib.ps5000aSetSigGenBuiltIn(
            c_int16(self.handle),
            c_int32(int(offsetVoltage * 1000000)),
            c_int32(int(pkToPk * 1000000)),
            c_int16(waveType),
            c_float(frequency), c_float(stopFreq),
            c_float(increment), c_float(dwellTime),
            c_enum(sweepType), c_enum(0),
            c_uint32(shots), c_uint32(numSweeps),
            c_enum(triggerType), c_enum(triggerSource),
            c_int16(0))
        self.checkResult(m)

    def _lowLevelSetDeviceResolution(self, resolution):
        self.resolution = resolution
        m = self.lib.ps5000aSetDeviceResolution(
            c_int16(self.handle),
            c_enum(resolution))
        self.checkResult(m)

    def _lowLevelChangePowerSource(self, powerstate):
        m = self.lib.ps5000aChangePowerSource(
            c_int16(self.handle),
            c_enum(powerstate))
        self.checkResult(m)

    # Morgan's additions
    def _lowLevelGetValuesBulk(self, numSamples, fromSegment, toSegment,
                               downSampleRatio, downSampleMode, overflow):
        """Copy data from several memory segments at once."""
        overflowPoint = overflow.ctypes.data_as(POINTER(c_int16))
        m = self.lib.ps5000aGetValuesBulk(
            c_int16(self.handle),
            byref(c_int32(numSamples)),
            c_int32(fromSegment),
            c_int32(toSegment),
            c_int32(downSampleRatio),
            c_enum(downSampleMode),
            overflowPoint
            )
        self.checkResult(m)

    def _lowLevelSetNoOfCaptures(self, numCaptures):
        m = self.lib.ps5000aSetNoOfCaptures(
            c_int16(self.handle),
            c_uint32(numCaptures))
        self.checkResult(m)

    def _lowLevelMemorySegments(self, numSegments):
        maxSamples = c_int32()
        m = self.lib.ps5000aMemorySegments(
            c_int16(self.handle), c_uint32(numSegments), byref(maxSamples))
        self.checkResult(m)
        return maxSamples.value

    def _lowLevelGetValuesTriggerTimeOffsetBulk(self, fromSegment, toSegment):
        """Supposedly gets the trigger times for a bunch of segments at once.

        For block mode.
        Can't get it to work yet, however.
        """
        import numpy as np

        nSegments = toSegment - fromSegment + 1
        # time = c_int64()
        times = np.ascontiguousarray(
            np.zeros(nSegments, dtype=np.int64)
            )
        timeUnits = np.ascontiguousarray(
            np.zeros(nSegments, dtype=np.int32)
            )

        m = self.lib.ps5000aGetValuesTriggerTimeOffsetBulk64(
            c_int16(self.handle),
            times.ctypes.data_as(POINTER(c_int64)),
            timeUnits.ctypes.data_as(POINTER(c_enum)),
            c_uint32(fromSegment),
            c_uint32(toSegment)
            )
        self.checkResult(m)
        # timeUnits=np.array([self.TIME_UNITS[tu] for tu in timeUnits])
        return times, timeUnits
