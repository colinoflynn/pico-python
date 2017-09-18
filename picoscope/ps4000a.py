# This is the instrument-specific file for the PS4000A series of instruments.
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
import os
import pdb

# to load the proper dll
import platform

# Do not import or use ill definied data types
# such as short int or long
# use the values specified in the h file
# float is always defined as 32 bits
# double is defined as 64 bits
from ctypes import byref, POINTER, create_string_buffer, c_float, \
    c_int16, c_uint16, c_int32, c_uint32, c_uint64, c_void_p, c_int8
from ctypes import c_int32 as c_enum

from picoscope.picobase import _PicoscopeBase

class PS4000a(_PicoscopeBase):
    """The following are low-level functions for the PS4000A."""

    LIBNAME = "ps4000a"

    MAX_VALUE = 32764
    MIN_VALUE = -32764

    # EXT/AUX seems to have an imput impedence of 50 ohm (PS6403B)
    EXT_MAX_VALUE = 32767
    EXT_MIN_VALUE = -32767
    EXT_RANGE_VOLTS = 1

    # I don't think that the 50V range is allowed, but I left it there anyway
    # The 10V and 20V ranges are only allowed in high impedence modes
    CHANNEL_RANGE = [{"rangeV": 20E-3, "apivalue": 1, "rangeStr": "20 mV"},
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

    NUM_CHANNELS = 8
    CHANNELS = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6, "H": 7,  "MaxChannels": 8}

    CHANNEL_COUPLINGS = {"DC50": 2, "DC": 1, "AC": 0}

    WAVE_TYPES = {"Sine": 0, "Square": 1, "Triangle": 2,
                  "RampUp": 3, "RampDown": 4,
                  "Sinc": 5, "Gaussian": 6, "HalfSine": 7, "DCVoltage": 8,
                  "WhiteNoise": 9}

    SWEEP_TYPES = {"Up": 0, "Down": 1, "UpDown": 2, "DownUp": 3}

    TIME_UNITS = {"femtoseconds": 0,
                  "picoseconds": 1,
                  "nanoseconds": 2,
                  "microseconds":3,
                  "milliseconds":4,
                  "seconds":5}

    def __init__(self, serialNumber=None, connect=True):
        """ Load DLLs. """
        self.handle = None

        if platform.system() == 'Linux' :
            from ctypes import cdll
            # ok I don't know what is wrong with my installer, but I need to include
            # .so.2
            self.lib = cdll.LoadLibrary("lib" + self.LIBNAME + ".so.2")
        elif platform.system() == 'Darwin':
            from ctypes import cdll
            self.lib = cdll.LoadLibrary("lib" + self.LIBNAME + ".dylib")
        else:
            from ctypes import windll
            self.lib = windll.LoadLibrary(str(self.LIBNAME + ".dll"))

        super(PS4000a, self).__init__(serialNumber, connect)

    def _lowLevelOpenUnit(self, sn):
        c_handle = c_int16()
        if sn is not None:
            serialNullTermStr = create_string_buffer(str(sn))
        else:
            serialNullTermStr = None
        # Passing None is the same as passing NULL
        m = self.lib.ps4000aOpenUnit(byref(c_handle), serialNullTermStr)
        self.checkResult(m)
        self.handle = c_handle.value

    def _lowLevelOpenUnitAsync(self, sn):
        c_status = c_int16()
        if sn is not None:
            serialNullTermStr = create_string_buffer(sn)
        else:
            serialNullTermStr = None

        # Passing None is the same as passing NULL
        m = self.lib.ps4000aOpenUnitAsync(byref(c_status), serialNullTermStr)
        self.checkResult(m)

        return c_status.value

    def _lowLevelOpenUnitProgress(self):
        complete = c_int16()
        progressPercent = c_int16()
        handle = c_int16()

        m = self.lib.ps4000aOpenUnitProgress(byref(handle), byref(progressPercent), byref(complete))
        self.checkResult(m)

        if complete.value != 0:
            self.handle = handle.value

        # if we only wanted to return one value, we could do somethign like
        # progressPercent = progressPercent * (1 - 0.1 * complete)
        return (progressPercent.value, complete.value)

    def _lowLevelCloseUnit(self):
        m = self.lib.ps4000aCloseUnit(c_int16(self.handle))
        self.checkResult(m)

    def _lowLevelEnumerateUnits(self):
        count = c_int16(0)
        serials = c_int8(0)
        serialLth = c_int16(0)

        m = self.lib.ps4000aEnumerateUnits(byref(count), byref(serials), byref(serialLth))
        self.checkResult(m)
        # a serial number is rouhgly 8 characters
        # an extra character for the comma
        # and an extra one for the space after the comma?
        # the extra two also work for the null termination
        serialLth = c_int16(count.value * (8 + 2))
        serials = create_string_buffer(serialLth.value + 1)

        m = self.lib.ps4000aEnumerateUnits(byref(count), serials, byref(serialLth))
        self.checkResult(m)

        serialList = str(serials.value.decode('utf-8')).split(',')

        serialList = [x.strip() for x in serialList]

        return serialList

    def _lowLevelSetChannel(self, chNum, enabled, coupling, VRange, VOffset,
                            BWLimited):
        m = self.lib.ps4000aSetChannel(c_int16(self.handle), c_enum(chNum),
                                      c_int16(enabled), c_enum(coupling),
                                      c_enum(VRange), c_float(VOffset))
        self.checkResult(m)

    def _lowLevelStop(self):
        m = self.lib.ps4000aStop(c_int16(self.handle))
        self.checkResult(m)

    def _lowLevelGetUnitInfo(self, info):
        s = create_string_buffer(256)
        requiredSize = c_int16(0)

        m = self.lib.ps4000aGetUnitInfo(c_int16(self.handle), byref(s),
                                       c_int16(len(s)), byref(requiredSize),
                                       c_enum(info))
        self.checkResult(m)
        if requiredSize.value > len(s):
            s = create_string_buffer(requiredSize.value + 1)
            m = self.lib.ps4000aGetUnitInfo(c_int16(self.handle), byref(s),
                                           c_int16(len(s)),
                                           byref(requiredSize), c_enum(info))
            self.checkResult(m)

        # should this bee ascii instead?
        # I think they are equivalent...
        return s.value.decode('utf-8')

    def _lowLevelFlashLed(self, times):
        m = self.lib.ps4000aFlashLed(c_int16(self.handle), c_int16(times))
        self.checkResult(m)

    def _lowLevelSetSimpleTrigger(self, enabled, trigsrc, threshold_adc,
                                  direction, delay, timeout_ms):
        m = self.lib.ps4000aSetSimpleTrigger(
            c_int16(self.handle), c_int16(enabled),
            c_enum(trigsrc), c_int16(threshold_adc),
            c_enum(direction), c_uint32(delay), c_int16(timeout_ms))
        self.checkResult(m)

    def _lowLevelRunBlock(self, numPreTrigSamples, numPostTrigSamples,
                          timebase, oversample, segmentIndex):
        timeIndisposedMs = c_int32()
        m = self.lib.ps4000aRunBlock(
            c_int16(self.handle), c_int32(numPreTrigSamples),
            c_int32(numPostTrigSamples), c_uint32(timebase),
            byref(timeIndisposedMs),
            c_uint32(segmentIndex), c_void_p(), c_void_p())
        self.checkResult(m)
        return timeIndisposedMs.value

    def _lowLevelIsReady(self):
        ready = c_int16()
        m = self.lib.ps4000aIsReady(c_int16(self.handle), byref(ready))
        self.checkResult(m)
        if ready.value:
            return True
        else:
            return False

    def _lowLevelGetTimebase(self, tb, noSamples, oversample, segmentIndex):
        """ return (timeIntervalSeconds, maxSamples). """
        maxSamples = c_int32()
        sampleRate = c_float()

        m = self.lib.ps4000aGetTimebase2(c_int16(self.handle), c_uint32(tb),
                                        c_int32(noSamples), byref(sampleRate),
                                        byref(maxSamples), c_uint32(segmentIndex))
        self.checkResult(m)

        return (sampleRate.value / 1.0E9, maxSamples.value)

    def getTimeBaseNum(self, sampleTimeS):
        """ Return sample time in seconds to timebase as int for API calls. """

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

    def getTimestepFromTimebase(self, timebase):
        """ Return timebase to sampletime as seconds. """
        if timebase < 3:
            dt = 2. ** timebase / 8e7
        else:
            dt = (timebase - 1) / 2e7
        return dt

    def _lowLevelSetDataBuffer(self, channel, data, downSampleMode, segmentIndex):
        """
        data should be a numpy array.

        Be sure to call _lowLevelClearDataBuffer
        when you are done with the data array
        or else subsequent calls to GetValue will still use the same array.

        segmentIndex is unused, but required by other versions of the API (eg PS5000a)

        """
        numSamples = len(data)

        m = self.lib.ps4000aSetDataBuffer(c_int16(self.handle), c_enum(channel),
                                          byref(data), c_uint32(numSamples),
                                          c_uint32(segmentIndex), c_uint32(downSampleMode))
        self.checkResult(m)

    def _lowLevelClearDataBuffer(self, channel, segmentIndex):
        """data should be a numpy array."""
        m = self.lib.ps4000aSetDataBuffer(c_int16(self.handle), c_enum(channel),
                                         c_void_p(), c_uint32(0), c_uint32(0), c_enum(0))
        self.checkResult(m)

    def _lowLevelGetValues(self, numSamples, startIndex, downSampleRatio,
                           downSampleMode, segmentIndex):
        numSamplesReturned = c_uint32()
        numSamplesReturned.value = numSamples
        overflow = c_int16()
        m = self.lib.ps4000aGetValues(
            c_int16(self.handle), c_uint32(startIndex),
            byref(numSamplesReturned), c_uint32(downSampleRatio),
            c_enum(downSampleMode), c_uint16(segmentIndex),
            byref(overflow))
        self.checkResult(m)
        return (numSamplesReturned.value, overflow.value)

    ####################################################################
    # Untested functions below                                         #
    #                                                                  #
    ####################################################################
    def _lowLevelSetSigGenBuiltInSimple(self, offsetVoltage, pkToPk, waveType,
                                        frequency, shots, triggerType,
                                        triggerSource, stopFreq, increment,
                                        dwellTime, sweepType, numSweeps):
        if stopFreq is None:
            stopFreq = frequency

        m = self.lib.ps4000aSetSigGenBuiltIn(
            c_int16(self.handle),
            c_int32(int(offsetVoltage * 1000000)),
            c_int32(int(pkToPk * 1000000)),
            c_int16(waveType),
            c_float(frequency), c_float(stopFreq),
            c_float(increment), c_float(dwellTime), c_enum(sweepType), c_enum(0),
            c_uint32(shots), c_uint32(numSweeps),
            c_enum(triggerType), c_enum(triggerSource),
            c_int16(0))
        self.checkResult(m)

    def _lowLevelGetMaxDownSampleRatio(self, noOfUnaggregatedSamples,
                                       downSampleRatioMode, segmentIndex):
        maxDownSampleRatio = c_uint32()

        m = self.lib.ps4000aGetMaxDownSampleRatio(
            c_int16(self.handle),
            c_uint32(noOfUnaggregatedSamples),
            byref(maxDownSampleRatio),
            c_enum(downSampleRatioMode),
            c_uint16(segmentIndex))
        self.checkResult(m)

        return maxDownSampleRatio.value

    def _lowLevelGetNoOfCaptures(self):
        nCaptures = c_uint32()

        m = self.lib.ps4000aGetNoOfCaptures(c_int16(self.handle), byref(nCaptures))
        self.checkResult(m)

        return nCaptures.value

    def _lowLevelGetTriggerTimeOffset(self, segmentIndex):
        time = c_uint64()
        timeUnits = c_enum()

        m = self.lib.ps4000aGetTriggerTimeOffset64(
            c_int16(self.handle),
            byref(time),
            byref(timeUnits),
            c_uint16(segmentIndex))

        self.checkResult(m)

        if timeUnits.value == 0:  # PS4000a_FS
            return time.value * 1E-15
        elif timeUnits.value == 1:  # PS4000a_PS
            return time.value * 1E-12
        elif timeUnits.value == 2:  # PS4000a_NS
            return time.value * 1E-9
        elif timeUnits.value == 3:  # PS4000a_US
            return time.value * 1E-6
        elif timeUnits.value == 4:  # PS4000a_MS
            return time.value * 1E-3
        elif timeUnits.value == 5:  # PS4000a_S
            return time.value * 1E0
        else:
            raise TypeError("Unknown timeUnits %d" % timeUnits.value)

    def _lowLevelMemorySegments(self, nSegments):
        nMaxSamples = c_uint32()

        m = self.lib.ps4000aMemorySegments(c_int16(self.handle),
                                          c_uint16(nSegments),
                                          byref(nMaxSamples))
        self.checkResult(m)

        return nMaxSamples.value

    def _lowLevelSetDataBuffers(self, channel, bufferMax, bufferMin, downSampleRatioMode):
        bufferMaxPtr = bufferMax.ctypes.data_as(POINTER(c_int16))
        bufferMinPtr = bufferMin.ctypes.data_as(POINTER(c_int16))
        bufferLth = len(bufferMax)

        m = self.lib.ps4000aSetDataBuffers(
            c_int16(self.handle),
            c_enum(channel),
            bufferMaxPtr,
            bufferMinPtr,
            c_uint32(bufferLth))
        self.checkResult(m)

    def _lowLevelClearDataBuffers(self, channel):
        m = self.lib.ps4000aSetDataBuffers(
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

        m = self.lib.ps4000aGetValuesBulk(
            c_int16(self.handle),
            byref(noOfSamples),
            c_uint16(fromSegmentIndex), c_uint16(toSegmentIndex),
            overflow.ctypes.data_as(POINTER(c_int16)))
        self.checkResult(m)
        return noOfSamples.value

    def _lowLevelSetDataBufferBulk(self, channel, buffer, waveform, downSampleRatioMode):
        bufferPtr = buffer.ctypes.data_as(POINTER(c_int16))
        bufferLth = len(buffer)

        m = self.lib.ps4000aSetDataBufferBulk(
            c_int16(self.handle),
            c_enum(channel),
            bufferPtr,
            c_uint32(bufferLth),
            c_uint16(waveform))
        self.checkResult(m)

    def _lowLevelSetNoOfCaptures(self, nCaptures):
        m = self.lib.ps4000aSetNoOfCaptures(
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
    def _lowLevelGetStreamingLatestValues(self, lpPs4000Ready, pParameter = c_void_p()):
        m = self.lib.ps4000aGetStreamingLatestValues(
            c_uint16(self.handle),
            lpPs4000Ready,
            pParameter)
        self.checkResult(m)

    def _lowLevelNoOfStreamingValues(self):
        noOfValues = c_uint32()

        m = self.lib.ps4000aNoOfStreamingValues(c_int16(self.handle), byref(noOfValues))
        self.checkResult(m)

        return noOfValues.value

    def _lowLevelRunStreaming(self, sampleInterval, sampleIntervalTimeUnits, maxPreTriggerSamples,
                              maxPostTriggerSamples, autoStop, downSampleRatio, downSampleRatioMode,
                              overviewBufferSize):
        m = self.lib.ps4000aRunStreaming(
            c_int16(self.handle),
            byref(c_uint32(sampleInterval)),
            c_enum(sampleIntervalTimeUnits),
            c_uint32(maxPreTriggerSamples),
            c_uint32(maxPostTriggerSamples),
            c_int16(autoStop),
            c_uint32(downSampleRatio),
            c_enum(downSampleRatioMode),
            c_uint32(overviewBufferSize))

        self.checkResult(m)

    def _lowLevelStreamingReady():
        pass
