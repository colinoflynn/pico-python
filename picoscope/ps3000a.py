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
    c_int16, c_int32, c_uint16, c_uint32, c_void_p
from ctypes import c_int32 as c_enum

from picoscope.picobase import _PicoscopeBase


class PS3000a(_PicoscopeBase):
    """The following are low-level functions for the PS3000a."""

    LIBNAME = "ps3000a"

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
    AWGBufferAddressWidth = 14
    AWGMaxSamples = 2 ** AWGBufferAddressWidth

    AWGDACInterval = 5E-9  # in seconds
    AWGDACFrequency = 1 / AWGDACInterval

    # Note this is NOT what is written in the Programming guide as of version
    # 10_5_0_28
    # This issue was acknowledged in this thread
    # http://www.picotech.com/support/topic13217.html
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
            from picoscope.darwin_utils import LoadLibraryDarwin
            self.lib = LoadLibraryDarwin("lib" + self.LIBNAME + ".dylib")
        else:
            from ctypes import windll
            from ctypes.util import find_library
            self.lib = windll.LoadLibrary(
                find_library(str(self.LIBNAME + ".dll"))
            )

        self.resolution = self.ADC_RESOLUTIONS["8"]

        super(PS3000a, self).__init__(serialNumber, connect)

    def _lowLevelOpenUnit(self, serialNumber):
        c_handle = c_int16()
        if serialNumber is not None:
            serialNumberStr = create_string_buffer(bytes(serialNumber,
                                                         encoding='utf-8'))
        else:
            serialNumberStr = None
        # Passing None is the same as passing NULL
        m = self.lib.ps3000aOpenUnit(byref(c_handle), serialNumberStr)
        self.handle = c_handle.value

        # copied over from ps5000a:
        # This will check if the power supply is not connected
        # and change the power supply accordingly
        # Personally (me = Mark), I don't like this
        # since the user should address this immediately, and we
        # shouldn't let this go as a soft error
        # but I think this should do for now
        if m == 0x11A:
            self.changePowerSource("PICO_POWER_SUPPLY_NOT_CONNECTED")
        else:
            self.checkResult(m)

    def _lowLevelCloseUnit(self):
        m = self.lib.ps3000aCloseUnit(c_int16(self.handle))
        self.checkResult(m)

    def _lowLevelEnumerateUnits(self):
        count = c_int16(0)
        m = self.lib.ps3000aEnumerateUnits(byref(count), None, None)
        self.checkResult(m)
        # a serial number is rouhgly 8 characters
        # an extra character for the comma
        # and an extra one for the space after the comma?
        # the extra two also work for the null termination
        serialLth = c_int16(count.value * (8 + 2))
        serials = create_string_buffer(serialLth.value + 1)

        m = self.lib.ps3000aEnumerateUnits(byref(count), serials,
                                           byref(serialLth))
        self.checkResult(m)

        serialList = str(serials.value.decode('utf-8')).split(',')

        serialList = [x.strip() for x in serialList]

        return serialList

    def _lowLevelSetChannel(self, chNum, enabled, coupling, VRange, VOffset,
                            BWLimited):
        m = self.lib.ps3000aSetChannel(c_int16(self.handle), c_enum(chNum),
                                       c_int16(enabled), c_enum(coupling),
                                       c_enum(VRange), c_float(VOffset))
        self.checkResult(m)

        m = self.lib.ps3000aSetBandwidthFilter(c_int16(self.handle),
                                               c_enum(chNum),
                                               c_enum(BWLimited))
        self.checkResult(m)

    def _lowLevelStop(self):
        m = self.lib.ps3000aStop(c_int16(self.handle))
        self.checkResult(m)

    def _lowLevelGetUnitInfo(self, info):
        s = create_string_buffer(256)
        requiredSize = c_int16(0)

        m = self.lib.ps3000aGetUnitInfo(c_int16(self.handle), byref(s),
                                        c_int16(len(s)), byref(requiredSize),
                                        c_enum(info))
        self.checkResult(m)
        if requiredSize.value > len(s):
            s = create_string_buffer(requiredSize.value + 1)
            m = self.lib.ps3000aGetUnitInfo(c_int16(self.handle), byref(s),
                                            c_int16(len(s)),
                                            byref(requiredSize), c_enum(info))
            self.checkResult(m)

        # should this bee ascii instead?
        # I think they are equivalent...
        return s.value.decode('utf-8')

    def _lowLevelFlashLed(self, times):
        m = self.lib.ps3000aFlashLed(c_int16(self.handle), c_int16(times))
        self.checkResult(m)

    def _lowLevelSetSimpleTrigger(self, enabled, trigsrc, threshold_adc,
                                  direction, delay, auto):
        m = self.lib.ps3000aSetSimpleTrigger(
            c_int16(self.handle), c_int16(enabled),
            c_enum(trigsrc), c_int16(threshold_adc),
            c_enum(direction), c_uint32(delay), c_int16(auto))
        self.checkResult(m)

    def _lowLevelSetNoOfCaptures(self, numCaptures):
        m = self.lib.ps3000aSetNoOfCaptures(c_int16(self.handle),
                                            c_uint16(numCaptures))
        self.checkResult(m)

    def _lowLevelMemorySegments(self, numSegments):
        maxSamples = c_int32()
        m = self.lib.ps3000aMemorySegments(c_int16(self.handle),
                                           c_uint16(numSegments),
                                           byref(maxSamples))
        self.checkResult(m)
        return maxSamples.value

    def _lowLevelGetMaxSegments(self):
        maxSegments = c_int16()
        m = self.lib.ps3000aGetMaxSegments(c_int16(self.handle),
                                           byref(maxSegments))
        self.checkResult(m)
        return maxSegments.value

    def _lowLevelRunBlock(self, numPreTrigSamples, numPostTrigSamples,
                          timebase, oversample, segmentIndex):
        # NOT: Oversample is NOT used!
        timeIndisposedMs = c_int32()
        m = self.lib.ps3000aRunBlock(
            c_int16(self.handle), c_uint32(numPreTrigSamples),
            c_uint32(numPostTrigSamples), c_uint32(timebase),
            c_int16(oversample), byref(timeIndisposedMs),
            c_uint32(segmentIndex),
            c_void_p(), c_void_p())
        self.checkResult(m)
        return timeIndisposedMs.value

    def _lowLevelIsReady(self):
        ready = c_int16()
        m = self.lib.ps3000aIsReady(c_int16(self.handle), byref(ready))
        self.checkResult(m)
        if ready.value:
            return True
        else:
            return False

    def _lowlevelPingUnit(self):
        m = self.lib.ps3000aPingUnit(c_int16(self.handle))
        return m

    def _lowLevelGetTimebase(self, tb, noSamples, oversample, segmentIndex):
        """Return (timeIntervalSeconds, maxSamples)."""
        maxSamples = c_int32()
        intervalNanoSec = c_float()

        m = self.lib.ps3000aGetTimebase2(c_int16(self.handle), c_uint32(tb),
                                         c_uint32(noSamples),
                                         byref(intervalNanoSec),
                                         c_int16(oversample),
                                         byref(maxSamples),
                                         c_uint32(segmentIndex))
        self.checkResult(m)
        # divide by 1e9 to return interval in seconds
        return (intervalNanoSec.value * 1e-9, maxSamples.value)

    def getTimeBaseNum(self, sampleTimeS):
        """Convert sample time in S to something to pass to API Call."""
        maxSampleTime = (((2 ** 32 - 1) - 2) / 125000000)
        if sampleTimeS < 8.0E-9:
            st = math.floor(math.log(sampleTimeS * 1E9, 2))
            st = max(st, 0)
        else:
            if sampleTimeS > maxSampleTime:
                sampleTimeS = maxSampleTime
            st = math.floor((sampleTimeS * 125000000) + 2)

        # is this cast needed?
        st = int(st)
        return st

    def getTimestepFromTimebase(self, timebase):
        """Take API timestep code and returns the sampling period.

        API timestep is an integer from 0-32
        """
        if timebase < 3:
            dt = 2. ** timebase / 1.0E9
        else:
            dt = (timebase - 2.0) / 125000000.
        return dt

    def _lowLevelSetAWGSimpleDeltaPhase(self, waveform, deltaPhase,
                                        offsetVoltage, pkToPk, indexMode,
                                        shots, triggerType, triggerSource):
        """Waveform should be an array of shorts."""
        waveformPtr = waveform.ctypes.data_as(POINTER(c_int16))

        m = self.lib.ps3000aSetSigGenArbitrary(
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

        m = self.lib.ps3000aSetDataBuffer(
            c_int16(self.handle), c_enum(channel),
            dataPtr, c_int32(numSamples),
            c_uint32(segmentIndex),
            c_enum(downSampleMode))
        self.checkResult(m)

    def _lowLevelSetDataBufferBulk(self, channel, data, segmentIndex,
                                   downSampleMode):
        """Set the bulk data buffer.

        In ps3000a, ps3000aSetDataBuffer combines the functionality of
        psX000YSetDataBuffer and psX000YSetDataBufferBulk. Since the rapid
        block functions in picoscope.py call the Bulk version, a delegator is
        needed. Note that the order of segmentIndex and downSampleMode is
        reversed.
        """
        self._lowLevelSetDataBuffer(channel, data, downSampleMode,
                                    segmentIndex)

    def _lowLevelSetMultipleDataBuffers(self, channel, data, downSampleMode):
        max_segments = self._lowLevelGetMaxSegments()
        if data.shape[0] < max_segments:
            raise ValueError("data array has fewer rows than current number " +
                             "of memory segments")
        if data.shape[1] < self.maxSamples:
            raise ValueError("data array has fewer columns than maxSamples")

        for i in range(max_segments):
            m = self._lowLevelSetDataBuffer(channel, data[i, :],
                                            downSampleMode, i)
            self.checkResult(m)

    def _lowLevelClearDataBuffer(self, channel, segmentIndex):
        m = self.lib.ps3000aSetDataBuffer(c_int16(self.handle),
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
        m = self.lib.ps3000aGetValues(
            c_int16(self.handle), c_uint32(startIndex),
            byref(numSamplesReturned), c_uint32(downSampleRatio),
            c_enum(downSampleMode), c_uint32(segmentIndex),
            byref(overflow))
        self.checkResult(m)
        return (numSamplesReturned.value, overflow.value)

    def _lowLevelGetValuesBulk(self, numSamples, fromSegment, toSegment,
                               downSampleRatio, downSampleMode, overflow):
        m = self.lib.ps3000aGetValuesBulk(
            c_int16(self.handle),
            byref(c_uint32(numSamples)),
            c_uint32(fromSegment),
            c_uint32(toSegment),
            c_uint32(downSampleRatio),
            c_int16(downSampleMode),
            overflow.ctypes.data_as(POINTER(c_int16))
            )
        self.checkResult(m)
        return overflow, numSamples

    def _lowLevelSetSigGenBuiltInSimple(self, offsetVoltage, pkToPk, waveType,
                                        frequency, shots, triggerType,
                                        triggerSource, stopFreq, increment,
                                        dwellTime, sweepType, numSweeps):
        # TODO, I just noticed that V2 exists
        # Maybe change to V2 in the future
        if stopFreq is None:
            stopFreq = frequency

        m = self.lib.ps3000aSetSigGenBuiltIn(
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

    def _lowLevelChangePowerSource(self, powerstate):
        m = self.lib.ps3000aChangePowerSource(
            c_int16(self.handle),
            c_enum(powerstate))
        self.checkResult(m)

    def _lowLevelSigGenSoftwareControl(self, triggerType):
        m = self.lib.ps3000aSigGenSoftwareControl(
            c_int16(self.handle),
            c_enum(triggerType))
        self.checkResult(m)
