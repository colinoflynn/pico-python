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

# This is the instrument-specific file for the PS2000a series of instruments.
#
# pico-python is Copyright (c) 2013-2016 By:
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

from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import math
import numpy as np

# to load the proper dll
import platform

# Do not import or use ill definied data types
# such as short int or long
# use the values specified in the h file
# float is always defined as 32 bits
# double is defined as 64 bits
from ctypes import byref, POINTER, create_string_buffer, c_float, \
    c_int16, c_int32, c_uint16, c_uint32, c_void_p
from ctypes import c_int32 as c_enum

from picoscope.picobase import _PicoscopeBase


class PS2000a(_PicoscopeBase):
    """The following are low-level functions for the PS2000a."""

    LIBNAME = "ps2000a"

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

    # TIME_UNITS = {'PS2000A_FS':0,'PS2000A_PS':1,
    # 'PS2000A_NS':2,'PS2000A_US':3,'PS2000A_MS':4,
    # 'PS2000A_S':5,'PS2000A_MAX_TIME_UNITS':6}
    TIME_UNITS = {0: 1e-15, 1: 1e-12, 2: 1e-9, 3: 1e-6, 4: 1e-3, 5: 1e0}

    AWGPhaseAccumulatorSize = 32

    # AWG scaling according to programming manual p.72
    # Vout = 1uV * (pkToPk/2) * (sample_value / 32767) + offsetVoltage
    # The API datatype is a (signed) short
    AWGMaxVal = 32767
    AWGMinVal = -32767

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
            self.lib = self.loadLibraryDarwin("lib" + self.LIBNAME + ".dylib")
        else:
            from ctypes import windll
            from ctypes.util import find_library
            self.lib = windll.LoadLibrary(
                find_library(str(self.LIBNAME + ".dll"))
            )

        self.resolution = self.ADC_RESOLUTIONS["8"]

        super(PS2000a, self).__init__(serialNumber, connect)

    def _lowLevelOpenUnit(self, sn):
        c_handle = c_int16()
        if sn is not None:
            serialNullTermStr = byref(create_string_buffer(sn))
        else:
            serialNullTermStr = None
        # Passing None is the same as passing NULL
        m = self.lib.ps2000aOpenUnit(byref(c_handle), serialNullTermStr)
        self.checkResult(m)
        self.handle = c_handle.value

        # The scaling factor used in the timebase calculation varies based on
        # the particular model. See section 2.8 (pg 27) of the 2000a
        # programmer's guide
        self.model = self.getUnitInfo('VariantInfo')
        if self.model in ('2205AMSO', '2206', '2206A', '2206B', '2405A'):
            # 500 MS/s
            self._timebase_to_timestep = \
                lambda n: (2**n / 5e8) if n < 3 else ((n - 2) / 625e5)
            self._timestep_to_timebase = \
                lambda t: math.log(t * 5e8, 2) if t < 16e-9 else (
                    (t * 625e5) + 2)
        elif self.model in ('2206BMSO', '2207', '2207A', '2207B', '2207BMSO',
                            '2208', '2208A', '2208B', '2208BMSO', '2406B',
                            '2407B', '2408B'):
            # 1 GS/s
            self._timebase_to_timestep = lambda n: (2**n / 1e9) if n < 3 else (
                (n - 2) / 125e6)
            self._timestep_to_timebase = \
                lambda t: math.log(t * 1e9, 2) if t < 8e-9 else (
                    (t * 125e6) + 2)
        elif self.model == '2205MSO':
            self._timebase_to_timestep = \
                lambda n: (2**n / 2e8) if n < 1 else (n / 1e8)
            self._timestep_to_timebase = \
                lambda t: math.log(t * 2e8, 2) if t < 10e-9 else (t * 1e8)
        else:
            raise ValueError("Unrecognised variant {}".format(self.model))

        # The AWG parameters vary based on the particular model. See section
        # 3.51.2 of the 2000a programmer's guide
        if self.model in ('2205AMSO', '2206', '2206A', '2207', '2207A', '2208',
                          '2208A', '2405A'):
            self.AWGBufferAddressWidth = 13
            self.AWGDACInterval = 50E-9
        elif self.model in ('2206B', '2206BMSO', '2207B', '2207BMSO', '2208B',
                            '2208BMSO', '2406B', '2407B', '2408B'):
            self.AWGBufferAddressWidth = 15
            self.AWGDACInterval = 50E-9
        else:
            # The programmer's manual indicates that some older models have
            # these parameters. Just use them as a catch-all for any models
            # not listed above
            self.AWGBufferAddressWidth = 13
            self.AWGDACInterval = 20.83E-9

        self.AWGMaxSamples = 2 ** self.AWGBufferAddressWidth
        self.AWGDACFrequency = 1 / self.AWGDACInterval

    def _lowLevelCloseUnit(self):
        m = self.lib.ps2000aCloseUnit(c_int16(self.handle))
        self.checkResult(m)

    def _lowLevelSetChannel(self, chNum, enabled, coupling, VRange, VOffset,
                            BWLimited):
        m = self.lib.ps2000aSetChannel(c_int16(self.handle), c_enum(chNum),
                                       c_int16(enabled), c_enum(coupling),
                                       c_enum(VRange), c_float(VOffset))
        self.checkResult(m)

    def _lowLevelStop(self):
        m = self.lib.ps2000aStop(c_int16(self.handle))
        self.checkResult(m)

    def _lowLevelGetUnitInfo(self, info):
        s = create_string_buffer(256)
        requiredSize = c_int16(0)

        m = self.lib.ps2000aGetUnitInfo(c_int16(self.handle), byref(s),
                                        c_int16(len(s)), byref(requiredSize),
                                        c_enum(info))
        self.checkResult(m)
        if requiredSize.value > len(s):
            s = create_string_buffer(requiredSize.value + 1)
            m = self.lib.ps2000aGetUnitInfo(c_int16(self.handle), byref(s),
                                            c_int16(len(s)),
                                            byref(requiredSize), c_enum(info))
            self.checkResult(m)

        # should this bee ascii instead?
        # I think they are equivalent...
        return s.value.decode('utf-8')

    def _lowLevelFlashLed(self, times):
        m = self.lib.ps2000aFlashLed(c_int16(self.handle), c_int16(times))
        self.checkResult(m)

    def _lowLevelSetSimpleTrigger(self, enabled, trigsrc, threshold_adc,
                                  direction, delay, auto):
        m = self.lib.ps2000aSetSimpleTrigger(
            c_int16(self.handle), c_int16(enabled),
            c_enum(trigsrc), c_int16(threshold_adc),
            c_enum(direction), c_uint32(delay), c_int16(auto))
        self.checkResult(m)

    def _lowLevelSetNoOfCaptures(self, numCaptures):
        m = self.lib.ps2000aSetNoOfCaptures(
            c_int16(self.handle), c_uint16(numCaptures))
        self.checkResult(m)

    def _lowLevelMemorySegments(self, numSegments):
        maxSamples = c_int32()
        m = self.lib.ps2000aMemorySegments(c_int16(self.handle),
                                           c_uint16(numSegments),
                                           byref(maxSamples))
        self.checkResult(m)
        return maxSamples.value

    def _lowLevelGetMaxSegments(self):
        maxSegments = c_int16()
        m = self.lib.ps2000aGetMaxSegments(c_int16(self.handle),
                                           byref(maxSegments))
        self.checkResult(m)
        return maxSegments.value

    def _lowLevelRunBlock(self, numPreTrigSamples, numPostTrigSamples,
                          timebase, oversample, segmentIndex):
        # NOT: Oversample is NOT used!
        timeIndisposedMs = c_int32()
        m = self.lib.ps2000aRunBlock(
            c_int16(self.handle), c_uint32(numPreTrigSamples),
            c_uint32(numPostTrigSamples), c_uint32(timebase),
            c_int16(oversample), byref(timeIndisposedMs),
            c_uint32(segmentIndex),
            c_void_p(), c_void_p())
        self.checkResult(m)
        return timeIndisposedMs.value

    def _lowLevelIsReady(self):
        ready = c_int16()
        m = self.lib.ps2000aIsReady(c_int16(self.handle), byref(ready))
        self.checkResult(m)
        if ready.value:
            return True
        else:
            return False

    def _lowLevelGetTimebase(self, tb, noSamples, oversample, segmentIndex):
        """Return (timeIntervalSeconds, maxSamples)."""
        maxSamples = c_int32()
        intervalNanoSec = c_float()

        m = self.lib.ps2000aGetTimebase2(
            c_int16(self.handle), c_uint32(tb), c_uint32(noSamples),
            byref(intervalNanoSec), c_int16(oversample), byref(maxSamples),
            c_uint32(segmentIndex))
        self.checkResult(m)
        # divide by 1e9 to return interval in seconds
        return (intervalNanoSec.value * 1e-9, maxSamples.value)

    def getTimeBaseNum(self, sampleTimeS):
        """Convert sample time in S to something to pass to API Call."""
        clipped = np.clip(math.floor(self._timestep_to_timebase(sampleTimeS)),
                          0, np.iinfo(np.int32).max)

        return int(clipped)

    def getTimestepFromTimebase(self, timebase):
        """Convvert API timestep code to sampling interval.

        API timestep as an integer from 0-32,
        sampling interval in seconds.
        """
        return self._timebase_to_timestep(timebase)

    def _lowLevelSetAWGSimpleDeltaPhase(self, waveform, deltaPhase,
                                        offsetVoltage, pkToPk, indexMode,
                                        shots, triggerType, triggerSource):
        """Waveform should be an array of shorts."""
        waveformPtr = waveform.ctypes.data_as(POINTER(c_int16))

        m = self.lib.ps2000aSetSigGenArbitrary(
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
        """Set the buffer for the picoscope.

        Be sure to call _lowLevelClearDataBuffer
        when you are done with the data array
        or else subsequent calls to GetValue will still use the same array.
        """
        dataPtr = data.ctypes.data_as(POINTER(c_int16))
        numSamples = len(data)

        m = self.lib.ps2000aSetDataBuffer(
            c_int16(self.handle), c_enum(channel), dataPtr,
            c_int32(numSamples), c_uint32(segmentIndex),
            c_enum(downSampleMode))
        self.checkResult(m)

    def _lowLevelSetMultipleDataBuffers(self, channel, data, downSampleMode):
        max_segments = self._lowLevelGetMaxSegments()
        if data.shape[0] < max_segments:
            raise ValueError(
                "data array has fewer rows" +
                " than current number of memory segments")
        if data.shape[1] < self.maxSamples:
            raise ValueError("data array has fewer columns than maxSamples")

        for i in range(max_segments):
            m = self._lowLevelSetDataBuffer(channel, data[i, :],
                                            downSampleMode, i)
            self.checkResult(m)

    def _lowLevelClearDataBuffer(self, channel, segmentIndex):
        """Clear the data in the picoscope."""
        m = self.lib.ps2000aSetDataBuffer(
            c_int16(self.handle), c_enum(channel),
            c_void_p(), c_uint32(0), c_uint32(segmentIndex), c_enum(0))
        self.checkResult(m)

    def _lowLevelGetValues(self, numSamples, startIndex, downSampleRatio,
                           downSampleMode, segmentIndex):
        numSamplesReturned = c_uint32()
        numSamplesReturned.value = numSamples
        overflow = c_int16()
        m = self.lib.ps2000aGetValues(
            c_int16(self.handle), c_uint32(startIndex),
            byref(numSamplesReturned), c_uint32(downSampleRatio),
            c_enum(downSampleMode), c_uint32(segmentIndex),
            byref(overflow))
        self.checkResult(m)
        return (numSamplesReturned.value, overflow.value)

    def _lowLevelGetValuesBulk(self, numSamples, fromSegment, toSegment,
                               downSampleRatio, downSampleMode, overflow):
        m = self.lib.ps2000aGetValuesBulk(
            c_int16(self.handle),
            byref(c_int16(numSamples)),
            c_int16(fromSegment),
            c_int16(toSegment),
            c_int32(downSampleRatio),
            c_int16(downSampleMode),
            overflow.ctypes.data_as(POINTER(c_int16))
            )
        self.checkResult(m)
        return overflow, numSamples

    def _lowLevelGetTriggerTimeOffset(self, segmentIndex):
        timeUpper = c_uint32()
        timeLower = c_uint32()
        timeUnits = c_int16()
        m = self.lib.ps2000aGetTriggerTimeOffset(
            c_int16(self.handle),
            byref(timeUpper),
            byref(timeLower),
            byref(timeUnits),
            c_uint32(segmentIndex),
            )
        self.checkResult(m)

        # timeUpper and timeLower are the upper 4 and lower 4 bytes of a 64-bit
        # (8-byte) integer which is scaled by timeUnits to get the precise
        # trigger location
        return (((timeUpper.value << 32) + timeLower.value) *
                self.TIME_UNITS[timeUnits.value])

    def _lowLevelSetSigGenBuiltInSimple(self, offsetVoltage, pkToPk, waveType,
                                        frequency, shots, triggerType,
                                        triggerSource, stopFreq, increment,
                                        dwellTime, sweepType, numSweeps):
        # TODO, I just noticed that V2 exists
        # Maybe change to V2 in the future

        if stopFreq is None:
            stopFreq = frequency

        m = self.lib.ps2000aSetSigGenBuiltIn(
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

    def _lowLevelSigGenSoftwareControl(self, triggerType):
        m = self.lib.ps2000aSigGenSoftwareControl(
            c_int16(self.handle), c_enum(triggerType))
        self.checkResult(m)
