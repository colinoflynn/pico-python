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


# Do not import or use ill definied data types
# such as short int or long
# use the values specified in the h file
# float is always defined as 32 bits
# double is defined as 64 bits
from ctypes import byref, POINTER, create_string_buffer, c_float, c_double, \
    c_int16, c_uint16, c_int32, c_uint32, c_uint64, c_void_p, c_int8, \
    CFUNCTYPE
from ctypes import c_int32 as c_enum

from picoscope.picobase import _PicoscopeBase


# Decorators for callback functions. PICO_STATUS is uint32_t.
def blockReady(function):
    """typedef void (*ps4000aBlockReady)
    (
     int16_t         handle,
     PICO_STATUS     status,
     void          * pParameter
    )
    """
    if function is None:
        return None

    callback = CFUNCTYPE(c_void_p, c_int16, c_uint32, c_void_p)
    return callback(function)


def dataReady(function):
    """typedef void (*ps4000aDataReady)
    (
     int16_t         handle,
     PICO_STATUS     status,
     uint32_t        noOfSamples,
     int16_t         overflow,
     void         * pParameter
    )
    """
    callback = CFUNCTYPE(c_void_p,
                         c_int16, c_uint32, c_uint32, c_int16, c_void_p)
    return callback(function)


def streamingReady(function):
    """typedef void (*ps4000aStreamingReady)
    (
        int16_t     handle,
        int32_t     noOfSamples,
        uint32_t    startIndex,
        int16_t     overflow,
        uint32_t    triggerAt,
        int16_t     triggered,
        int16_t     autoStop,
        void      * pParameter
    )
    """
    callback = CFUNCTYPE(c_void_p, c_int16, c_int32, c_uint32, c_int16,
                         c_uint32, c_int16, c_int16, c_void_p)
    return callback(function)


class PS4000a(_PicoscopeBase):
    """The following are low-level functions for the PS4000A."""

    LIBNAME = "ps4000a"

    MAX_VALUE = 32764
    MIN_VALUE = -32764

    # EXT/AUX seems to have an input impedance of 50 ohm (PS6403B)
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
    CHANNELS = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6,
                "H": 7,  "MaxChannels": 8}

    ADC_RESOLUTIONS = {"8": 0, "12": 1, "14": 2, "15": 3, "16": 4}

    CHANNEL_COUPLINGS = {"DC50": 2, "DC": 1, "AC": 0}

    WAVE_TYPES = {"Sine": 0, "Square": 1, "Triangle": 2,
                  "RampUp": 3, "RampDown": 4,
                  "Sinc": 5, "Gaussian": 6, "HalfSine": 7, "DCVoltage": 8,
                  "WhiteNoise": 9}

    SWEEP_TYPES = {"Up": 0, "Down": 1, "UpDown": 2, "DownUp": 3}

    TIME_UNITS = {"femtoseconds": 0,
                  "picoseconds": 1,
                  "nanoseconds": 2,
                  "microseconds": 3,
                  "milliseconds": 4,
                  "seconds": 5}

    SIGGEN_TRIGGER_TYPES = {"Rising": 0, "Falling": 1,
                            "GateHigh": 2, "GateLow": 3}

    SIGGEN_TRIGGER_SOURCES = {"None": 0, "ScopeTrig": 1,
                              "AuxIn": 2, "ExtIn": 3, "SoftTrig": 4}

    AWGPhaseAccumulatorSize = 32
    AWGBufferAddressWidth = 14
    AWGMaxSamples = 2 ** AWGBufferAddressWidth

    AWGDACInterval = 12.5E-9  # in seconds
    AWGDACFrequency = 1 / AWGDACInterval

    # From the programmer's guide, p.99, defined for the PicoScope 4824. Values
    # have been checked against those returned by the
    # ps4000aSigGenArbitraryMinMaxValues function, with a PS4824 device
    # connected.
    AWGMaxVal = 32767
    AWGMinVal = -32768

    AWG_INDEX_MODES = {"Single": 0, "Dual": 1, "Quad": 2}

    def __init__(self, serialNumber=None, connect=True, dllPath=None):
        """Load DLL and setup API.
        
        :param serialNumber: The serial number of the device to connect to.
        :param connect: If True, then connect to the device.
        :param dllPath: The path to the dll if not in standard location.
        """
        self.load_library(self.LIBNAME, dllPath)

        self.resolution = self.ADC_RESOLUTIONS["12"]

        super(PS4000a, self).__init__(serialNumber, connect)

    def _lowLevelOpenUnit(self, serialNumber):
        c_handle = c_int16()
        if serialNumber is not None:
            serialNumberStr = create_string_buffer(bytes(serialNumber,
                                                         encoding='utf-8'))
        else:
            serialNumberStr = None
        # Passing None is the same as passing NULL
        m = self.lib.ps4000aOpenUnit(byref(c_handle), serialNumberStr)
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

        self.model = self.getUnitInfo('VariantInfo')

    def _lowLevelOpenUnitAsync(self, serialNumber):
        c_status = c_int16()
        if serialNumber is not None:
            serialNumberStr = create_string_buffer(bytes(serialNumber,
                                                         encoding='utf-8'))
        else:
            serialNumberStr = None
        # Passing None is the same as passing NULL
        m = self.lib.ps4000aOpenUnitAsync(byref(c_status), serialNumberStr)
        self.checkResult(m)

        # Set the model after completion in _lowLevelOpenUnitProgress.
        return c_status.value

    def _lowLevelOpenUnitProgress(self):
        complete = c_int16()
        progressPercent = c_int16()
        handle = c_int16()

        m = self.lib.ps4000aOpenUnitProgress(byref(handle),
                                             byref(progressPercent),
                                             byref(complete))
        self.checkResult(m)

        if complete.value != 0:
            self.handle = handle.value
            self.model = self.getUnitInfo('VariantInfo')

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

        m = self.lib.ps4000aEnumerateUnits(byref(count), byref(serials),
                                           byref(serialLth))
        self.checkResult(m)
        # a serial number is rouhgly 10 characters
        # an extra character for the comma
        # and an extra one for the space after the comma?
        # the extra two also work for the null termination
        serialLth = c_int16(count.value * (10 + 2))
        serials = create_string_buffer(serialLth.value + 1)

        m = self.lib.ps4000aEnumerateUnits(byref(count), serials,
                                           byref(serialLth))
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
        # Only for model PS4444
        # See discussion: https://github.com/colinoflynn/pico-python/pull/171
        if self.model.startswith('4444'):  # Only for model 4444
            m = self.lib.ps4000aSetBandwidthFilter(c_int16(self.handle),
                                                   c_enum(chNum),
                                                   c_enum(BWLimited))
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
                          timebase, oversample, segmentIndex, callback,
                          pParameter):
        # Hold a reference to the callback so that the Python
        # function pointer doesn't get free'd
        self._c_runBlock_callback = blockReady(callback)
        timeIndisposedMs = c_int32()
        m = self.lib.ps4000aRunBlock(
            c_int16(self.handle), c_int32(numPreTrigSamples),
            c_int32(numPostTrigSamples), c_uint32(timebase),
            byref(timeIndisposedMs), c_uint32(segmentIndex),
            self._c_runBlock_callback, c_void_p())
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

    def _lowLevelGetTimebase(self, timebase, noSamples, oversample,
                             segmentIndex):
        """
        Calculate the sampling interval and maximum number of samples.

        timebase
            Number of the selected timebase.
        noSamples
            Number of required samples.
        oversample
            Not used.
        segmentIndex
            Index of the segment to save samples in

        Return
        -------
        timeIntervalSeconds : float
            Time interval between two samples in s.
        maxSamples : int
            maximum number of samples available depending on channels
            and timebase chosen.
        """
        maxSamples = c_int32()
        timeIntervalSeconds = c_float()

        m = self.lib.ps4000aGetTimebase2(c_int16(self.handle),
                                         c_uint32(timebase),
                                         c_int32(noSamples),
                                         byref(timeIntervalSeconds),
                                         byref(maxSamples),
                                         c_uint32(segmentIndex))
        self.checkResult(m)

        return (timeIntervalSeconds.value / 1.0E9, maxSamples.value)

    def getTimeBaseNum(self, sampleTimeS):
        """
        Convert `sampleTimeS` in s to the integer timebase number.

        See "Timebases" section of the PS4000a programmer's guide
        for more information.
        """
        if self.model == '4444':
            maxSampleTime = (((2 ** 32 - 1) - 2) / 5.0E7)

            if (sampleTimeS <= 2.5E-9 and
                    self.resolution == self.ADC_RESOLUTIONS["12"]):
                timebase = 0
            elif (sampleTimeS <= 20E-9 and
                    self.resolution == self.ADC_RESOLUTIONS["14"]):
                timebase = 3
            else:
                # Otherwise in range 2^32-1
                if sampleTimeS > maxSampleTime:
                    sampleTimeS = maxSampleTime

                timebase = math.floor((sampleTimeS * 5.0E7) + 2)

        else:
            timebase = math.floor(sampleTimeS / 12.5e-9 - 1)
            timebase = max(timebase, 0)
            timebase = min(timebase, 2 ** 32 - 1)

        return timebase

    def getTimestepFromTimebase(self, timebase):
        """
        Convert `timebase` index to sampletime in seconds.

        See "Timebases" section of the PS4000a programmer's guide
        for more information.
        """
        if self.model == '4444':
            if timebase <= 3:
                dt = 2 ** timebase / 4.0E8
            else:
                dt = (timebase - 2) / 5.0E7

        else:
            dt = (timebase + 1) / 8.0E7
        return dt

    def _lowLevelSetAWGSimpleDeltaPhase(self, waveform, deltaPhase,
                                        offsetVoltage, pkToPk, indexMode,
                                        shots, triggerType, triggerSource):
        """Waveform should be an array of shorts."""
        waveformPtr = waveform.ctypes.data_as(POINTER(c_int16))

        m = self.lib.ps4000aSetSigGenArbitrary(
            c_int16(self.handle),
            c_int32(int(offsetVoltage * 1E6)),  # offset voltage in microvolts
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

        m = self.lib.ps4000aSetDataBuffer(c_int16(self.handle),
                                          c_enum(channel),
                                          dataPtr, c_uint32(numSamples),
                                          c_uint32(segmentIndex),
                                          c_uint32(downSampleMode))
        self.checkResult(m)

    def _lowLevelClearDataBuffer(self, channel, segmentIndex):
        m = self.lib.ps4000aSetDataBuffer(c_int16(self.handle),
                                          c_enum(channel),
                                          c_void_p(), c_uint32(0), c_uint32(0),
                                          c_enum(0))
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

    def _lowLevelGetValuesAsync(self, numSamples, startIndex, downSampleRatio,
                                downSampleMode, segmentIndex, callback, pPar):
        self._c_getValues_callback = dataReady(callback)
        m = self.lib.ps4000aGetValuesAsync(c_int16(self.handle),
                                           c_uint32(startIndex),
                                           c_uint32(numSamples),
                                           c_uint32(downSampleRatio),
                                           c_enum(downSampleMode),
                                           c_uint32(segmentIndex),
                                           self._c_getValues_callback,
                                           c_void_p())
        self.checkResult(m)

    def _lowLevelSetDeviceResolution(self, resolution):
        self.resolution = resolution
        m = self.lib.ps4000aSetDeviceResolution(
            c_int16(self.handle),
            c_enum(resolution))
        self.checkResult(m)

    def _lowLevelChangePowerSource(self, powerstate):
        m = self.lib.ps4000aChangePowerSource(
            c_int16(self.handle),
            c_enum(powerstate))
        self.checkResult(m)

    def _lowLevelGetValuesBulk(self, numSamples, fromSegment, toSegment,
                               downSampleRatio, downSampleMode, overflow):
        """Copy data from several memory segments at once."""
        overflowPoint = overflow.ctypes.data_as(POINTER(c_int16))
        m = self.lib.ps4000aGetValuesBulk(
            c_int16(self.handle),
            byref(c_int32(numSamples)),
            c_int32(fromSegment),
            c_int32(toSegment),
            c_int32(downSampleRatio),
            c_enum(downSampleMode),
            overflowPoint
        )
        self.checkResult(m)

    def _lowLevelSetDataBufferBulk(self, channel, data, segmentIndex,
                                   downSampleMode):
        """Just calls setDataBuffer with argument order changed.

        For compatibility with current picobase.py.
        """
        self._lowLevelSetDataBuffer(channel, data, downSampleMode,
                                    segmentIndex)

    def _lowLevelPingUnit(self):
        """Check connection to picoscope and return the error."""
        return self.lib.ps4000aPingUnit(c_int16(self.handle))

    def _lowLevelSetSigGenBuiltInSimple(self, offsetVoltage, pkToPk, waveType,
                                        frequency, shots, triggerType,
                                        triggerSource, stopFreq, increment,
                                        dwellTime, sweepType, numSweeps):
        if stopFreq is None:
            stopFreq = frequency

        m = self.lib.ps4000aSetSigGenBuiltIn(
            c_int16(self.handle),
            c_int32(int(offsetVoltage * 1000000)),
            c_uint32(int(pkToPk * 1000000)),
            c_enum(waveType),
            c_double(frequency), c_double(stopFreq),
            c_double(increment), c_double(dwellTime),
            c_enum(sweepType), c_enum(0),
            c_uint32(shots), c_uint32(numSweeps),
            c_enum(triggerType), c_enum(triggerSource),
            c_int16(0))
        self.checkResult(m)

    def _lowLevelSigGenSoftwareControl(self, state):
        m = self.lib.ps4000aSigGenSoftwareControl(
            c_int16(self.handle),
            c_int16(state))
        self.checkResult(m)

    ####################################################################
    # Untested functions below                                         #
    #                                                                  #
    ####################################################################

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

        m = self.lib.ps4000aGetNoOfCaptures(c_int16(self.handle),
                                            byref(nCaptures))
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

    def _lowLevelSetDataBuffers(self, channel, bufferMax, bufferMin,
                                downSampleRatioMode):
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

    def _lowLevelSetNoOfCaptures(self, nCaptures):
        m = self.lib.ps4000aSetNoOfCaptures(
            c_int16(self.handle),
            c_uint16(nCaptures))
        self.checkResult(m)

    # ETS Functions
    def _lowLevelSetEts(self):
        pass

    def _lowLevelSetEtsTimeBuffer(self):
        pass

    def _lowLevelSetEtsTimeBuffers(self):
        pass

    def _lowLevelSetExternalClock(self):
        pass

    # Complicated triggering
    # need to understand structs for this one to work
    def _lowLevelIsTriggerOrPulseWidthQualifierEnabled(self):
        pass

    def _lowLevelGetValuesTriggerTimeOffsetBulk(self):
        pass

    def _lowLevelSetTriggerChannelConditions(self):
        pass

    def _lowLevelSetTriggerChannelDirections(self):
        pass

    def _lowLevelSetTriggerChannelProperties(self):
        pass

    def _lowLevelSetPulseWidthQualifier(self):
        pass

    def _lowLevelSetTriggerDelay(self):
        pass

    # Async functions
    def _lowLevelGetValuesBulkAsync(self):
        pass

    # overlapped functions
    def _lowLevelGetValuesOverlapped(self):
        pass

    def _lowLevelGetValuesOverlappedBulk(self):
        pass

    # Streaming related functions
    def _lowLevelGetStreamingLatestValues(self, lpPs4000Ready,
                                          pParameter=c_void_p()):
        m = self.lib.ps4000aGetStreamingLatestValues(
            c_uint16(self.handle),
            lpPs4000Ready,
            pParameter)
        self.checkResult(m)

    def _lowLevelNoOfStreamingValues(self):
        noOfValues = c_uint32()

        m = self.lib.ps4000aNoOfStreamingValues(c_int16(self.handle),
                                                byref(noOfValues))
        self.checkResult(m)

        return noOfValues.value

    def _lowLevelRunStreaming(self, sampleInterval, sampleIntervalTimeUnits,
                              maxPreTriggerSamples, maxPostTriggerSamples,
                              autoStop, downSampleRatio, downSampleRatioMode,
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

    def _lowLevelStreamingReady(self):
        pass
