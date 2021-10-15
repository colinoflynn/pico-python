# This is the instrument-specific file for the PS4000 series of instruments.
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

# 3.0 compatibility
# see http://docs.python.org/2/library/__future__.html
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
    c_int16, c_uint16, c_int32, c_uint32, c_uint64, c_void_p
from ctypes import c_int32 as c_enum

from picoscope.picobase import _PicoscopeBase


class PS4000(_PicoscopeBase):
    """The following are low-level functions for the PS4000."""

    LIBNAME = "ps4000"

    MAX_VALUE = 32764
    MIN_VALUE = -32764

    # AWG stuff here:
    AWGMaxSamples = 4096

    AWGDACInterval = 1 / 192000  # [s]
    AWGDACFrequency = 192000  # [Hz]
    AWGPhaseAccumulatorSize = 32

    AWGMaxVal = 32767
    AWGMinVal = -32768

    AWG_INDEX_MODES = {"Single": 0, "Dual": 1, "Quad": 2}

    AWGBufferAddressWidth = 12
    AWGMaxSamples = 2 ** AWGBufferAddressWidth

    SIGGEN_TRIGGER_TYPES = {"Rising": 0, "Falling": 1,
                            "GateHigh": 2, "GateLow": 3}

    SIGGEN_TRIGGER_SOURCES = {"None": 0, "ScopeTrig": 1,
                              "AuxIn": 2, "ExtIn": 3, "SoftTrig": 4}

    # EXT/AUX seems to have an imput impedence of 50 ohm (PS6403B)
    EXT_MAX_VALUE = 32767
    EXT_MIN_VALUE = -32767
    EXT_RANGE_VOLTS = 1

    # I don't think that the 50V range is allowed, but I left it there anyway
    # The 10V and 20V ranges are only allowed in high impedence modes
    CHANNEL_RANGE = [{"rangeV": 20E-3,  "apivalue": 1, "rangeStr": "20 mV"},
                     {"rangeV": 50E-3,  "apivalue": 2, "rangeStr": "50 mV"},
                     {"rangeV": 100E-3, "apivalue": 3, "rangeStr": "100 mV"},
                     {"rangeV": 200E-3, "apivalue": 4, "rangeStr": "200 mV"},
                     {"rangeV": 500E-3, "apivalue": 5, "rangeStr": "500 mV"},
                     {"rangeV": 1.0,    "apivalue": 6, "rangeStr": "1 V"},
                     {"rangeV": 2.0,    "apivalue": 7, "rangeStr": "2 V"},
                     {"rangeV": 5.0,    "apivalue": 8, "rangeStr": "5 V"},
                     {"rangeV": 10.0,   "apivalue": 9, "rangeStr": "10 V"},
                     {"rangeV": 20.0,   "apivalue": 10, "rangeStr": "20 V"},
                     {"rangeV": 50.0,   "apivalue": 11, "rangeStr": "50 V"},
                     ]

    NUM_CHANNELS = 4
    CHANNELS = {"A": 0, "B": 1, "C": 2, "D": 3, "EXT": 4}

    CHANNEL_COUPLINGS = {"DC50": 2, "DC": 1, "AC": 0}

    WAVE_TYPES = {"Sine": 0, "Square": 1, "Triangle": 2,
                  "RampUp": 3, "RampDown": 4,
                  "Sinc": 5, "Gaussian": 6, "HalfSine": 7, "DCVoltage": 8,
                  "WhiteNoise": 9}

    SWEEP_TYPES = {"Up": 0, "Down": 1, "UpDown": 2, "DownUp": 3}

    def __init__(self, serialNumber=None, connect=True):
        """Load DLLs."""
        self.handle = None
        if platform.system() == 'Linux':
            from ctypes import cdll
            # ok I don't know what is wrong with my installer,
            # but I need to include .so.2
            self.lib = cdll.LoadLibrary("lib" + self.LIBNAME + ".so.2")
        elif platform.system() == 'Darwin':
            from picoscope.darwin_utils import LoadLibraryDarwin
            self.lib = LoadLibraryDarwin("lib" + self.LIBNAME + ".dylib")
        else:
            from ctypes import windll
            from ctypes.util import find_library
            self.lib = windll.LoadLibrary(
                find_library(str(self.LIBNAME + ".dll"))
            )

        super(PS4000, self).__init__(serialNumber, connect)
        # check to see which model we have and use special functions if needed

        unit_number = self.getUnitInfo('VariantInfo')
        if unit_number == '4262':
            self.getTimestepFromTimebase = self._getTimestepFromTimebase4262
            self.getTimeBaseNum = self._getTimeBaseNum4262
        elif unit_number in {'4223', '4224', '4423', '4424'}:
            self.getTimestepFromTimebase = self._getTimestepFromTimebase4223
            self.getTimeBaseNum = self._getTimeBaseNum4223
        else:
            raise NotImplementedError('Timebase functions have not been '
                                      'written for the ' + unit_number)

    def _lowLevelOpenUnit(self, serialNumber):
        c_handle = c_int16()
        if serialNumber is not None:
            serialNumberStr = create_string_buffer(bytes(serialNumber,
                                                         encoding='utf-8'))
        else:
            serialNumberStr = None
        # Passing None is the same as passing NULL
        m = self.lib.ps4000OpenUnit(byref(c_handle), serialNumberStr)
        self.checkResult(m)
        self.handle = c_handle.value

    def _lowLevelOpenUnitAsync(self, serialNumber):
        c_status = c_int16()
        if serialNumber is not None:
            serialNumberStr = create_string_buffer(bytes(serialNumber,
                                                         encoding='utf-8'))
        else:
            serialNumberStr = None
        # Passing None is the same as passing NULL
        m = self.lib.ps4000OpenUnitAsync(byref(c_status), serialNumberStr)
        self.checkResult(m)

        return c_status.value

    def _lowLevelOpenUnitProgress(self):
        complete = c_int16()
        progressPercent = c_int16()
        handle = c_int16()

        m = self.lib.ps4000OpenUnitProgress(byref(handle),
                                            byref(progressPercent),
                                            byref(complete))
        self.checkResult(m)

        if complete.value != 0:
            self.handle = handle.value

        # if we only wanted to return one value, we could do somethign like
        # progressPercent = progressPercent * (1 - 0.1 * complete)
        return (progressPercent.value, complete.value)

    def _lowLevelCloseUnit(self):
        m = self.lib.ps4000CloseUnit(c_int16(self.handle))
        self.checkResult(m)

    def _lowLevelEnumerateUnits(self):
        count = c_int16(0)
        m = self.lib.ps4000EnumerateUnits(byref(count), None, None)
        self.checkResult(m)
        # a serial number is rouhgly 8 characters
        # an extra character for the comma
        # and an extra one for the space after the comma?
        # the extra two also work for the null termination
        serialLth = c_int16(count.value * (8 + 2))
        serials = create_string_buffer(serialLth.value + 1)

        m = self.lib.ps4000EnumerateUnits(byref(count), serials,
                                          byref(serialLth))
        self.checkResult(m)

        serialList = str(serials.value.decode('utf-8')).split(',')

        serialList = [x.strip() for x in serialList]

        return serialList

    def _lowLevelSetChannel(self, chNum, enabled, coupling, VRange, VOffset,
                            BWLimited):
        m = self.lib.ps4000SetChannel(c_int16(self.handle), c_enum(chNum),
                                      c_int16(enabled), c_enum(coupling),
                                      c_enum(VRange), c_float(VOffset),
                                      c_enum(BWLimited))
        self.checkResult(m)

    def _lowLevelStop(self):
        m = self.lib.ps4000Stop(c_int16(self.handle))
        self.checkResult(m)

    def _lowLevelGetUnitInfo(self, info):
        s = create_string_buffer(256)
        requiredSize = c_int16(0)

        m = self.lib.ps4000GetUnitInfo(c_int16(self.handle), byref(s),
                                       c_int16(len(s)), byref(requiredSize),
                                       c_enum(info))
        self.checkResult(m)
        if requiredSize.value > len(s):
            s = create_string_buffer(requiredSize.value + 1)
            m = self.lib.ps4000GetUnitInfo(c_int16(self.handle), byref(s),
                                           c_int16(len(s)),
                                           byref(requiredSize), c_enum(info))
            self.checkResult(m)

        # should this bee ascii instead?
        # I think they are equivalent...
        return s.value.decode('utf-8')

    def _lowLevelFlashLed(self, times):
        m = self.lib.ps4000FlashLed(c_int16(self.handle), c_int16(times))
        self.checkResult(m)

    def _lowLevelSetSimpleTrigger(self, enabled, trigsrc, threshold_adc,
                                  direction, delay, timeout_ms):
        m = self.lib.ps4000SetSimpleTrigger(
            c_int16(self.handle), c_int16(enabled),
            c_enum(trigsrc), c_int16(threshold_adc),
            c_enum(direction), c_uint32(delay), c_int16(timeout_ms))
        self.checkResult(m)

    def _lowLevelRunBlock(self, numPreTrigSamples, numPostTrigSamples,
                          timebase, oversample, segmentIndex):
        timeIndisposedMs = c_int32()
        m = self.lib.ps4000RunBlock(
            c_int16(self.handle), c_uint32(numPreTrigSamples),
            c_uint32(numPostTrigSamples), c_uint32(timebase),
            c_int16(oversample), byref(timeIndisposedMs),
            c_uint16(segmentIndex), c_void_p(), c_void_p())
        self.checkResult(m)
        return timeIndisposedMs.value

    def _lowLevelIsReady(self):
        ready = c_int16()
        m = self.lib.ps4000IsReady(c_int16(self.handle), byref(ready))
        self.checkResult(m)
        if ready.value:
            return True
        else:
            return False

    def _lowLevelGetTimebase(self, tb, noSamples, oversample, segmentIndex):
        """Return (timeIntervalSeconds, maxSamples)."""
        maxSamples = c_int32()
        sampleRate = c_float()

        m = self.lib.ps4000GetTimebase2(c_int16(self.handle), c_uint32(tb),
                                        c_uint32(noSamples), byref(sampleRate),
                                        c_int16(oversample), byref(maxSamples),
                                        c_uint16(segmentIndex))
        self.checkResult(m)

        return (sampleRate.value / 1.0E9, maxSamples.value)

    def getTimeBaseNum(self, sampleTimeS):
        """Return sample time in seconds to timebase as int for API calls."""
        raise NotImplementedError('Timebase functions have not been '
                                  'written for the scope.')

    def getTimestepFromTimebase(self, timebase):
        """Return timebase to sampletime as seconds."""
        raise NotImplementedError('Timebase functions have not been '
                                  'written for the scope.')

    def _getTimeBaseNum4223(self, sampleTimeS):
        """Return sample time in seconds to timebase as int for API calls."""
        maxSampleTime = (((2 ** 32 - 1) - 4) / 2e7)

        if sampleTimeS <= 12.5E-9:
            timebase = math.floor(math.log(sampleTimeS * 8E7, 2))
            timebase = max(timebase, 0)
        else:
            # Otherwise in range 2^32-1
            if sampleTimeS > maxSampleTime:
                sampleTimeS = maxSampleTime

            timebase = math.floor((sampleTimeS * 2e7) + 1)

        # is this cast needed?
        timebase = int(timebase)
        return timebase

    def _getTimestepFromTimebase4223(self, timebase):
        """Return timebase to sampletime as seconds."""
        if timebase < 3:
            dt = 2. ** timebase / 8e7
        else:
            dt = (timebase - 1) / 2e7
        return dt

    def _getTimestepFromTimebase4262(self, timebase):
        """Return timebase to sampletime as seconds for ps4262."""
        someConstant = 10000000.0
        return (timebase+1) / someConstant

    def _getTimeBaseNum4262(self, sampleTimeS):
        """Return timebase for the ps4262.

        Return sample time in seconds to timebase as
        int for API calls for ps4262.
        """
        someConstant = 10000000.0
        maxSampleTime = ((2 ** 30) / someConstant)
        minSampleTime = 1 / someConstant

        if sampleTimeS <= minSampleTime:
            timebase = 0
        elif sampleTimeS >= maxSampleTime:
            timebase = (2 ** 30)
        else:
            timebase = round(sampleTimeS * someConstant) - 1

        # is this cast needed?
        timebase = int(timebase)
        return timebase

    def _lowLevelSetDataBuffer(self, channel, data, downSampleMode,
                               segmentIndex):
        """Set the data buffer.

        Be sure to call _lowLevelClearDataBuffer
        when you are done with the data array
        or else subsequent calls to GetValue will still use the same array.

        segmentIndex is unused, but required by other versions of the API
        (eg PS5000a)
        """
        dataPtr = data.ctypes.data_as(POINTER(c_int16))
        numSamples = len(data)

        m = self.lib.ps4000SetDataBuffer(c_int16(self.handle), c_enum(channel),
                                         dataPtr, c_uint32(numSamples))
        self.checkResult(m)

    def _lowLevelClearDataBuffer(self, channel, segmentIndex):
        m = self.lib.ps4000SetDataBuffer(c_int16(self.handle), c_enum(channel),
                                         c_void_p(), c_uint32(0), c_enum(0))
        self.checkResult(m)

    def _lowLevelGetValues(self, numSamples, startIndex, downSampleRatio,
                           downSampleMode, segmentIndex):
        numSamplesReturned = c_uint32()
        numSamplesReturned.value = numSamples
        overflow = c_int16()
        m = self.lib.ps4000GetValues(
            c_int16(self.handle), c_uint32(startIndex),
            byref(numSamplesReturned), c_uint32(downSampleRatio),
            c_enum(downSampleMode), c_uint16(segmentIndex),
            byref(overflow))
        self.checkResult(m)
        return (numSamplesReturned.value, overflow.value)

    def _lowLevelSetAWGSimpleDeltaPhase(self, waveform, deltaPhase,
                                        offsetVoltage, pkToPk, indexMode,
                                        shots, triggerType, triggerSource):
        """Waveform should be an array of shorts."""
        waveformPtr = waveform.ctypes.data_as(POINTER(c_int16))

        m = self.lib.ps4000SetSigGenArbitrary(
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

    def _lowLevelSetSigGenBuiltInSimple(self, offsetVoltage, pkToPk, waveType,
                                        frequency, shots, triggerType,
                                        triggerSource, stopFreq, increment,
                                        dwellTime, sweepType, numSweeps):
        if stopFreq is None:
            stopFreq = frequency

        m = self.lib.ps4000SetSigGenBuiltIn(
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

        m = self.lib.ps4000SigGenSoftwareControl(
            c_int16(self.handle), c_enum(triggerType))
        self.checkResult(m)

    # use VRange=5 for +/- 500mV signal range
    # OR
    # VRange=8 for +/- 5V range
    def _lowLevelSetExtTriggerRange(self, VRange):
        m = self.lib.ps4000SetExtTriggerRange(
            c_int16(self.handle),
            c_enum(VRange))
        self.checkResult(m)

    ####################################################################
    # Untested functions below                                         #
    #                                                                  #
    ####################################################################

    def _lowLevelGetMaxDownSampleRatio(self, noOfUnaggregatedSamples,
                                       downSampleRatioMode, segmentIndex):
        maxDownSampleRatio = c_uint32()

        m = self.lib.ps4000GetMaxDownSampleRatio(
            c_int16(self.handle),
            c_uint32(noOfUnaggregatedSamples),
            byref(maxDownSampleRatio),
            c_enum(downSampleRatioMode),
            c_uint16(segmentIndex))
        self.checkResult(m)

        return maxDownSampleRatio.value

    def _lowLevelGetNoOfCaptures(self):
        nCaptures = c_uint32()

        m = self.lib.ps4000GetNoOfCaptures(
            c_int16(self.handle), byref(nCaptures))
        self.checkResult(m)

        return nCaptures.value

    def _lowLevelGetTriggerTimeOffset(self, segmentIndex):
        time = c_uint64()
        timeUnits = c_enum()

        m = self.lib.ps4000GetTriggerTimeOffset64(
            c_int16(self.handle),
            byref(time),
            byref(timeUnits),
            c_uint16(segmentIndex))

        self.checkResult(m)

        if timeUnits.value == 0:    # PS4000_FS
            return time.value * 1E-15
        elif timeUnits.value == 1:  # PS4000_PS
            return time.value * 1E-12
        elif timeUnits.value == 2:  # PS4000_NS
            return time.value * 1E-9
        elif timeUnits.value == 3:  # PS4000_US
            return time.value * 1E-6
        elif timeUnits.value == 4:  # PS4000_MS
            return time.value * 1E-3
        elif timeUnits.value == 5:  # PS4000_S
            return time.value * 1E0
        else:
            raise TypeError("Unknown timeUnits %d" % timeUnits.value)

    def _lowLevelMemorySegments(self, nSegments):
        nMaxSamples = c_uint32()

        m = self.lib.ps4000MemorySegments(c_int16(self.handle),
                                          c_uint16(nSegments),
                                          byref(nMaxSamples))
        self.checkResult(m)

        return nMaxSamples.value

    def _lowLevelSetDataBuffers(self, channel, bufferMax, bufferMin,
                                downSampleRatioMode):
        bufferMaxPtr = bufferMax.ctypes.data_as(POINTER(c_int16))
        bufferMinPtr = bufferMin.ctypes.data_as(POINTER(c_int16))
        bufferLth = len(bufferMax)

        m = self.lib.ps4000SetDataBuffers(
            c_int16(self.handle),
            c_enum(channel),
            bufferMaxPtr,
            bufferMinPtr,
            c_uint32(bufferLth))
        self.checkResult(m)

    def _lowLevelClearDataBuffers(self, channel):
        m = self.lib.ps4000SetDataBuffers(
            c_int16(self.handle),
            c_enum(channel),
            c_void_p(),
            c_void_p(),
            c_uint32(0))
        self.checkResult(m)

    # Bulk values.
    # These would be nice, but the user would have to provide us
    # with an array.
    # we would have to make sure that it is contiguous amonts other things
    def _lowLevelGetValuesBulk(self,
                               numSamples,
                               fromSegmentIndex,
                               toSegmentIndex,
                               downSampleRatio,
                               downSampleMode,
                               overflow):
        noOfSamples = c_uint32(numSamples)

        m = self.lib.ps4000GetValuesBulk(
            c_int16(self.handle),
            byref(noOfSamples),
            c_uint16(fromSegmentIndex), c_uint16(toSegmentIndex),
            overflow.ctypes.data_as(POINTER(c_int16)))
        self.checkResult(m)
        return noOfSamples.value

    def _lowLevelSetDataBufferBulk(self, channel, buffer, waveform,
                                   downSampleRatioMode):
        bufferPtr = buffer.ctypes.data_as(POINTER(c_int16))
        bufferLth = len(buffer)

        m = self.lib.ps4000SetDataBufferBulk(
            c_int16(self.handle),
            c_enum(channel),
            bufferPtr,
            c_uint32(bufferLth),
            c_uint16(waveform))
        self.checkResult(m)

    def _lowLevelSetNoOfCaptures(self, nCaptures):
        m = self.lib.ps4000SetNoOfCaptures(
            c_int16(self.handle),
            c_uint16(nCaptures))
        self.checkResult(m)

    # ETS Functions
    def _lowLevelSetEts():
        pass

    def _lowLevelSetEtsTimeBuffer():
        pass

    def _lowLevelSetEtsTimeBuffers():
        pass

    def _lowLevelSetExternalClock():
        pass

    # Complicated triggering
    # need to understand structs for this one to work
    def _lowLevelIsTriggerOrPulseWidthQualifierEnabled():
        pass

    def _lowLevelGetValuesTriggerTimeOffsetBulk():
        pass

    def _lowLevelSetTriggerChannelConditions():
        pass

    def _lowLevelSetTriggerChannelDirections():
        pass

    def _lowLevelSetTriggerChannelProperties():
        pass

    def _lowLevelSetPulseWidthQualifier():
        pass

    def _lowLevelSetTriggerDelay():
        pass

    # Async functions
    # would be nice, but we would have to learn to implement callbacks
    def _lowLevelGetValuesAsync():
        pass

    def _lowLevelGetValuesBulkAsync():
        pass

    # overlapped functions
    def _lowLevelGetValuesOverlapped():
        pass

    def _lowLevelGetValuesOverlappedBulk():
        pass

    # Streaming related functions
    def _lowLevelGetStreamingLatestValues():
        pass

    def _lowLevelNoOfStreamingValues(self):
        noOfValues = c_uint32()

        m = self.lib.ps4000NoOfStreamingValues(
            c_int16(self.handle), byref(noOfValues))
        self.checkResult(m)

        return noOfValues.value

    def _lowLevelRunStreaming():
        pass

    def _lowLevelStreamingReady():
        pass
