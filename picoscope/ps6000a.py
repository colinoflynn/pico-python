# This is the instrument-specific file for the ps6000A series of instruments.
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
from ctypes import byref, POINTER, create_string_buffer, c_float, c_int8, \
    c_double, c_int16, c_uint16, c_int32, c_uint32, c_int64, c_uint64, \
    c_void_p, CFUNCTYPE
from ctypes import c_int32 as c_enum

from picoscope.picobase import _PicoscopeBase


# Decorators for callback functions. PICO_STATUS is uint32_t.
def blockReady(function):
    """typedef void (*ps6000aBlockReady)
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
    """typedef void (*ps6000aDataReady)
    (
     int16_t         handle,
     PICO_STATUS     status,
     uint64_t        noOfSamples,
     int16_t         overflow,
     void         * pParameter
    )
    """
    if function is None:
        return None
    callback = CFUNCTYPE(c_void_p, c_int16, c_uint32, c_uint64, c_int16,
                         c_void_p)
    return callback(function)


def updateFirmwareProgress(function):
    """typedef void (*PicoUpdateFirmwareProgress)
    (
     int16_t    handle,
     uint16_t   progress
    )
    """
    if function is None:
        return None
    callback = CFUNCTYPE(c_void_p, c_int16, c_uint16)
    return callback(function)


class PS6000a(_PicoscopeBase):
    """The following are low-level functions for the ps6000A.

    The 'TriggerAux' channel (trigger input at backside) works with
    setSimpleTrigger.

    Due to the new nature of the setDataBuffer method with actions, you have to
    clear all configured buffers before using a different readout method.
    """

    LIBNAME = "ps6000a"

    # Resolution in bit
    ADC_RESOLUTIONS = {"8": 0, "10": 10, "12": 1}

    NUM_CHANNELS = 4
    CHANNELS = {"A": 0, "B": 1, "C": 2, "D": 3,
                "External": 1000, "MaxChannels": 4, "TriggerAux": 1001}

    CHANNEL_COUPLINGS = {"DC50": 50, "DC": 1, "AC": 0}

    ACTIONS = {  # PICO_ACTION they can be combined with bitwise OR.
        'clear_all': 0x00000001,  # PICO_CLEAR_ALL
        'add': 0x00000002,  # PICO_ADD
        'clear_this': 0x00001000,  # PICO_CLEAR_THIS_DATA_BUFFER
        'clear_waveform': 0x00002000,  # PICO_CLEAR_WAVEFORM_DATA_BUFFERS
        'clear_waveform_read': 0x00004000,
        # PICO_CLEAR_WAVEFORM_READ_DATA_BUFFERS
    }

    DATA_TYPES = {  # PICO_DATA_TYPE
        'int8': 0,  # PICO_INT8_T
        'int16': 1,  # PICO_INT16_T
        'int32': 2,  # PICO_INT32_T
        'uint32': 3,  # PICO_UINT32_T
        'int64': 4,  # PICO_INT64_T
    }

    TIME_UNITS = [  # PICO_TIME_UNITS
        1e-15,  # PICO_FS
        1e-12,  # PICO_PS
        1e-9,  # PICO_NS
        1e-6,  # PICO_US
        1e-3,  # PICO_MS
        1,  # PICO_S
    ]

    # Only at 8 bit, use GetAdcLimits for other resolutions.
    MAX_VALUE = 32512
    MIN_VALUE = -32512

    # 10V and 20V are only allowed in high impedence modes.
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
                     ]

    RATIO_MODE = {"aggregate": 1,  # max and min of every n data.
                  "decimate": 2,  # Take every n data.
                  "average": 4,  # Average of every n data.
                  "trigger": 0x40000000,  # 20 samples either side of the
                  # trigger. This cannot be combined with any other ratio mode
                  "raw": 0x80000000,  # No downsampling
                  "none": 0x80000000,  # for compatibility
                  }

    EXT_MAX_VALUE = 32767
    EXT_MIN_VALUE = -32767
    EXT_RANGE_VOLTS = 5

    # TODO verify AWG values
    WAVE_TYPES = {"Sine": 0, "Square": 1, "Triangle": 2,
                  "RampUp": 3, "RampDown": 4,
                  "Sinc": 5, "Gaussian": 6, "HalfSine": 7, "DCVoltage": 8,
                  "WhiteNoise": 9}

    SWEEP_TYPES = {"Up": 0, "Down": 1, "UpDown": 2, "DownUp": 3}

    SIGGEN_TRIGGER_TYPES = {"Rising": 0, "Falling": 1,
                            "GateHigh": 2, "GateLow": 3}
    SIGGEN_TRIGGER_SOURCES = {"None": 0, "ScopeTrig": 1, "AuxIn": 2,
                              "ExtIn": 3, "SoftTrig": 4, "TriggerRaw": 5}

    AWGPhaseAccumulatorSize = 32
    AWGBufferAddressWidth = 14
    AWGMaxSamples = 2 ** AWGBufferAddressWidth

    AWGDACInterval = 5E-9  # in seconds
    AWGDACFrequency = 1 / AWGDACInterval

    AWGMaxVal = 0x0FFF
    AWGMinVal = 0x0000

    AWG_INDEX_MODES = {"Single": 0, "Dual": 1, "Quad": 2}

    def __init__(self, serialNumber=None, connect=True, resolution="8"):
        """Load DLLs."""
        self.handle = None
        self.resolution = self.ADC_RESOLUTIONS.get(resolution)

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

        super(PS6000a, self).__init__(serialNumber, connect)

    "General unit calls"

    # Open / close unit
    def _lowLevelOpenUnit(self, serialNumber):
        c_handle = c_int16()
        if serialNumber is not None:
            serialNumberStr = create_string_buffer(bytes(serialNumber,
                                                         encoding='utf-8'))
        else:
            serialNumberStr = None
        # Passing None is the same as passing NULL
        m = self.lib.ps6000aOpenUnit(byref(c_handle), serialNumberStr,
                                     self.resolution)
        self.checkResult(m)
        self.handle = c_handle.value
        mi, ma = self._lowLevelGetAdcLimits(self.resolution)
        self.MIN_VALUE, self.MAX_VALUE = mi, ma

    def _lowLevelOpenUnitAsync(self, serialNumber):
        c_status = c_int16()
        if serialNumber is not None:
            serialNumberStr = create_string_buffer(bytes(serialNumber,
                                                         encoding='utf-8'))
        else:
            serialNumberStr = None
        # Passing None is the same as passing NULL
        m = self.lib.ps6000aOpenUnitAsync(byref(c_status), serialNumberStr,
                                          self.resolution)
        self.checkResult(m)
        return c_status.value

    def _lowLevelOpenUnitProgress(self):
        complete = c_int16()
        progressPercent = c_int16()
        handle = c_int16()

        m = self.lib.ps6000aOpenUnitProgress(byref(handle),
                                             byref(progressPercent),
                                             byref(complete))
        self.checkResult(m)
        if complete.value != 0:
            self.handle = handle.value
            mi, ma = self._lowLevelGetAdcLimits(self.resolution)
            self.MIN_VALUE, self.MAX_VALUE = mi, ma
        return (progressPercent.value, complete.value)

    def _lowLevelCloseUnit(self):
        m = self.lib.ps6000aCloseUnit(c_int16(self.handle))
        self.checkResult(m)

    # Misc
    def _lowLevelEnumerateUnits(self):
        count = c_int16(0)
        serials = c_int8(0)
        serialLth = c_int16(0)
        m = self.lib.ps6000aEnumerateUnits(byref(count), byref(serials),
                                           byref(serialLth))
        self.checkResult(m)
        # a serial number is rouhgly 8 characters
        # an extra character for the comma
        # and an extra one for the space after the comma?
        # the extra two also work for the null termination
        serialLth = c_int16(count.value * (8 + 2))
        serials = create_string_buffer(serialLth.value + 1)

        m = self.lib.ps6000aEnumerateUnits(byref(count), serials,
                                           byref(serialLth))
        self.checkResult(m)

        serialList = str(serials.value.decode('utf-8')).split(',')

        serialList = [x.strip() for x in serialList]

        return serialList

    def _lowLevelFlashLed(self, times):
        # TODO verify as it does not work
        m = self.lib.ps6000aFlashLed(c_int16(self.handle), c_int16(times))
        self.checkResult(m)

    def _lowLevelGetUnitInfo(self, info):
        s = create_string_buffer(256)
        requiredSize = c_int16(0)

        m = self.lib.ps6000aGetUnitInfo(c_int16(self.handle), byref(s),
                                        c_int16(len(s)), byref(requiredSize),
                                        c_enum(info))
        self.checkResult(m)
        if requiredSize.value > len(s):
            s = create_string_buffer(requiredSize.value + 1)
            m = self.lib.ps6000aGetUnitInfo(c_int16(self.handle), byref(s),
                                            c_int16(len(s)),
                                            byref(requiredSize), c_enum(info))
            self.checkResult(m)

        # should this be ascii instead?
        # I think they are equivalent...
        return s.value.decode('utf-8')

    def _lowLevelPingUnit(self):
        """Check connection to picoscope and return the error."""
        return self.lib.ps6000aPingUnit(c_int16(self.handle))

    "Measurement"

    # Timebase
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
        maxSamples = c_uint64()
        timeIntervalNanoSeconds = c_double()

        m = self.lib.ps6000aGetTimebase(c_int16(self.handle),
                                        c_uint32(timebase),
                                        c_uint64(noSamples),
                                        byref(timeIntervalNanoSeconds),
                                        byref(maxSamples),
                                        c_uint64(segmentIndex))
        self.checkResult(m)

        return (timeIntervalNanoSeconds.value / 1.0e9, maxSamples.value)

    @staticmethod
    def getTimeBaseNum(sampleTimeS):
        """Convert `sampleTimeS` in s to the integer timebase number."""
        maxSampleTime = (((2 ** 32 - 1) - 4) / 156250000)

        if sampleTimeS < 6.4E-9:
            timebase = math.floor(math.log(sampleTimeS * 5E9, 2))
            timebase = max(timebase, 0)
        else:
            # Otherwise in range 2^32-1
            if sampleTimeS > maxSampleTime:
                sampleTimeS = maxSampleTime

            timebase = math.floor((sampleTimeS * 156250000) + 4)

        return timebase

    @staticmethod
    def getTimestepFromTimebase(timebase):
        """Convert `timebase` index to sampletime in seconds."""
        if timebase < 5:
            dt = 2 ** timebase / 5E9
        else:
            dt = (timebase - 4) / 156250000.
        return dt

    # Device resolution
    def _lowLevelGetDeviceResolution(self):
        """Return the vertical resolution of the oscilloscope."""
        resolution = c_uint32()
        m = self.lib.ps6000aGetDeviceResolution(c_int16(self.handle),
                                                byref(resolution))
        self.checkResult(m)
        self.resolution = resolution.value
        for key, value in self.ADC_RESOLUTIONS.items():
            if value == self.resolution:
                return key
        raise TypeError("Unknown resolution {}.".format(resolution))

    def _lowLevelSetDeviceResolution(self, resolution):
        """
        Set the sampling resolution of the device.

        At 10-bit and higher resolutions, the maximum capture buffer length is
        half that of 8-bit mode. When using 12-bit resolution only 2 channels
        can be enabled to capture data.
        """
        if type(resolution) is str:
            resolution = self.ADC_RESOLUTIONS[resolution]
        m = self.lib.ps6000aSetDeviceResolution(c_int16(self.handle),
                                                resolution)
        self.checkResult(m)
        self.resolution = resolution
        self.MIN_VALUE, self.MAX_VALUE = self._lowLevelGetAdcLimits(resolution)

    def _lowLevelGetAdcLimits(self, resolution):
        """
        This function gets the maximum and minimum sample values that the ADC
        can produce at a given resolution.
        """
        if type(resolution) is str:
            resolution = self.ADC_RESOLUTIONS[resolution]
        minimum = c_int16()
        maximum = c_int16()
        m = self.lib.ps6000aGetAdcLimits(c_int16(self.handle),
                                         resolution,
                                         byref(minimum),
                                         byref(maximum))
        self.checkResult(m)
        return minimum.value, maximum.value

    # Channel
    def _lowLevelSetChannel(self, chNum, enabled, coupling, VRange, VOffset,
                            BWLimited):
        if enabled:
            m = self.lib.ps6000aSetChannelOn(c_int16(self.handle),
                                             c_enum(chNum), c_enum(coupling),
                                             c_enum(VRange), c_double(VOffset),
                                             c_enum(BWLimited))
        else:
            m = self.lib.ps6000aSetChannelOff(c_int16(self.handle),
                                              c_enum(chNum))
        self.checkResult(m)

    # Trigger
    def _lowLevelSetSimpleTrigger(self, enabled, trigsrc, threshold_adc,
                                  direction, delay, timeout_ms):
        m = self.lib.ps6000aSetSimpleTrigger(c_int16(self.handle),
                                             c_int16(enabled),
                                             c_enum(trigsrc),
                                             c_int16(threshold_adc),
                                             c_enum(direction),
                                             c_uint64(delay),
                                             c_uint32(timeout_ms * 1000))
        self.checkResult(m)

    # Start / stop measurement
    def _lowLevelStop(self):
        m = self.lib.ps6000aStop(c_int16(self.handle))
        self.checkResult(m)

    def _lowLevelRunBlock(self, numPreTrigSamples, numPostTrigSamples,
                          timebase, oversample, segmentIndex, callback,
                          pParameter):
        # Hold a reference to the callback so that the Python
        # function pointer doesn't get free'd.
        self._c_runBlock_callback = blockReady(callback)
        timeIndisposedMs = c_int32()
        m = self.lib.ps6000aRunBlock(c_int16(self.handle),
                                     c_uint64(numPreTrigSamples),
                                     c_uint64(numPostTrigSamples),
                                     c_uint32(timebase),
                                     byref(timeIndisposedMs),
                                     c_uint64(segmentIndex),
                                     self._c_runBlock_callback,
                                     c_void_p())
        self.checkResult(m)
        return timeIndisposedMs.value

    def _lowLevelIsReady(self):
        ready = c_int16()
        m = self.lib.ps6000aIsReady(c_int16(self.handle), byref(ready))
        self.checkResult(m)
        if ready.value:
            return True
        else:
            return False

    # Setup data acquisition.
    def _lowLevelMemorySegments(self, nSegments):
        nMaxSamples = c_uint64()
        m = self.lib.ps6000aMemorySegments(c_int16(self.handle),
                                           c_uint64(nSegments),
                                           byref(nMaxSamples))
        self.checkResult(m)
        return nMaxSamples.value

    def _lowLevelSetDataBuffer(self, channel, data, downSampleMode,
                               segmentIndex):
        """Set the data buffer.

        Be sure to call _lowLevelClearDataBuffer
        when you are done with the data array
        or else subsequent calls to GetValue will still use the same array.

        action
            the method to use when creating the buffer. The buffers are added
            to a unique list for the channel, data type and segment. Therefore
            you must use PICO_CLEAR_ALL to remove all buffers already written.
            PICO_ACTION values can be ORed together to allow clearing and
            adding in one call.
        """
        if downSampleMode == 0:
            downSampleMode = self.RATIO_MODE['raw']
        dataPtr = data.ctypes.data_as(POINTER(c_int16))
        numSamples = len(data)

        m = self.lib.ps6000aSetDataBuffer(c_int16(self.handle),
                                          c_enum(channel),
                                          dataPtr,
                                          c_int32(numSamples),
                                          self.DATA_TYPES['int16'],
                                          c_uint64(segmentIndex),
                                          c_enum(downSampleMode),
                                          self.ACTIONS['add'])
        self.checkResult(m)

    def _lowLevelClearDataBuffer(self, channel, segmentIndex,
                                 downSampleMode=0):
        """Clear the buffer for the chosen channel, segment, downSampleMode."""
        if downSampleMode == 0:
            downSampleMode = self.RATIO_MODE['raw']
        m = self.lib.ps6000aSetDataBuffer(c_int16(self.handle),
                                          c_enum(channel),
                                          c_void_p(),
                                          c_int32(0),
                                          self.DATA_TYPES['int16'],
                                          c_uint64(segmentIndex),
                                          c_enum(downSampleMode),
                                          self.ACTIONS['clear_this'])
        self.checkResult(m)

    def _lowLevelClearDataBufferAll(self, channel=1, segmentIndex=0):
        """Clear all the stored buffers for all channels."""
        m = self.lib.ps6000aSetDataBuffer(c_int16(self.handle),
                                          c_enum(channel),
                                          c_void_p(),
                                          c_int32(0),
                                          self.DATA_TYPES['int16'],
                                          c_uint64(segmentIndex),
                                          c_enum(0),
                                          self.ACTIONS['clear_all'])
        self.checkResult(m)

    def _lowLevelSetDataBufferBulk(self, channel, data, segmentIndex,
                                   downSampleMode):
        """Just calls setDataBuffer with argument order changed.

        For compatibility with current picobase.py.
        """
        self._lowLevelSetDataBuffer(channel, data, downSampleMode,
                                    segmentIndex)

    # Acquire data.
    def _lowLevelGetValues(self, numSamples, startIndex, downSampleRatio,
                           downSampleMode, segmentIndex):
        if downSampleMode == 0:
            downSampleMode = self.RATIO_MODE['raw']
        numSamplesReturned = c_uint64()
        numSamplesReturned.value = numSamples
        overflow = c_int16()
        m = self.lib.ps6000aGetValues(c_int16(self.handle),
                                      c_uint64(startIndex),
                                      byref(numSamplesReturned),
                                      c_uint64(downSampleRatio),
                                      c_enum(downSampleMode),
                                      c_uint64(segmentIndex),
                                      byref(overflow))
        self.checkResult(m)
        return (numSamplesReturned.value, overflow.value)

    def _lowLevelGetValuesBulk(self, numSamples, fromSegmentIndex,
                               toSegmentIndex, downSampleRatio, downSampleMode,
                               overflow):
        if downSampleMode == 0:
            downSampleMode = self.RATIO_MODE['raw']
        overflowPoint = overflow.ctypes.data_as(POINTER(c_int16))
        m = self.lib.ps6000aGetValuesBulk(
            c_int16(self.handle),
            c_uint64(0),  # startIndex
            byref(c_int64(numSamples)),
            c_int64(fromSegmentIndex),
            c_int64(toSegmentIndex),
            c_int64(downSampleRatio),
            c_enum(downSampleMode),
            overflowPoint
        )
        self.checkResult(m)

    def _lowLevelGetValuesAsync(self, numSamples, startIndex, downSampleRatio,
                                downSampleMode, segmentIndex, callback, pPar):
        if downSampleMode == 0:
            downSampleMode = self.RATIO_MODE['raw']
        self._c_getValues_callback = dataReady(callback)
        m = self.lib.ps6000aGetValuesAsync(c_int16(self.handle),
                                           c_uint64(startIndex),
                                           c_uint64(numSamples),
                                           c_uint64(downSampleRatio),
                                           c_enum(downSampleMode),
                                           c_uint64(segmentIndex),
                                           self._c_getValues_callback,
                                           c_void_p())
        self.checkResult(m)

    # Misc
    def _lowLevelGetTriggerTimeOffset(self, segmentIndex):
        time = c_int64()
        timeUnits = c_enum()

        m = self.lib.ps6000aGetTriggerTimeOffset(c_int16(self.handle),
                                                 byref(time),
                                                 byref(timeUnits),
                                                 c_uint64(segmentIndex))
        self.checkResult(m)

        try:
            return time.value * self.TIME_UNITS[timeUnits.value]
        except KeyError:
            raise TypeError("Unknown timeUnits %d" % timeUnits.value)

    ###########################
    # TODO test functions below
    ###########################

    "Updates"

    def _lowLevelCheckForUpdate(self):
        """
        Check whether a firmware update for the device is available.

        Returns
        -------
        firmwareInfos : None
            not implemented: A struct with information.
        number : int
            Number of elements in the structure.
        required : bool
            Whether an update is required or not.
        """
        # TODO raises PICO_STRING_BUFFER_TOO_SMALL
        firmware_info = create_string_buffer(25600000)
        number = c_int16()
        required = c_uint16()
        m = self.lib.ps6000aCheckForUpdate(c_int16(self.handle),
                                           byref(firmware_info),
                                           byref(number), byref(required))
        self.checkResult(m)
        return firmware_info, number, required

    def _lowLevelStartFirmwareUpdate(self, function):
        # Hold a reference to the callback so that the Python
        # function pointer doesn't get free'd.
        self._c_updateFirmware_callback = updateFirmwareProgress(function)
        m = self.lib.ps6000aStartFirmwareUpdate(
            c_int16(self.handle),
            self._c_updateFirmware_callback)
        self.checkResult(m)

    "Misc"

    ##################################
    # TODO verify functions below here in the manual
    # TODO ensure all relevant functions are in here
    ##################################

    "Measurement"

    # Complicated triggering
    # need to understand structs for some of this to work
    def _lowLevelGetValuesTriggerTimeOffsetBulk():
        raise NotImplementedError()

    def _lowLevelSetTriggerChannelConditions():
        raise NotImplementedError()

    def _lowLevelSetTriggerChannelDirections():
        raise NotImplementedError()

    def _lowLevelSetTriggerChannelProperties():
        raise NotImplementedError()

    def _lowLevelSetTriggerDelay():
        raise NotImplementedError()

    def _lowLevelSetTriggerDigitalPortProperties(self):
        raise NotImplementedError()

    # Optional input triggering: PulseWidthQualifier
    def _lowLevelSetPulseWidthQualifierConditions(self):
        raise NotImplementedError()

    def _lowLevelSetPulseWidthQualifierDirections(self):
        raise NotImplementedError()

    def _lowLevelSetPulseWidthQualifierProperties(self):
        raise NotImplementedError()

    def _lowLevelTriggerWithinPreTriggerSamples(self):
        raise NotImplementedError()

    # Data acquisition
    def _lowLevelSetDataBuffers(self, channel, bufferMax, bufferMin,
                                downSampleMode):
        if downSampleMode == 0:
            downSampleMode = self.RATIO_MODE['raw']
        raise NotImplementedError()
        bufferMaxPtr = bufferMax.ctypes.data_as(POINTER(c_int16))
        bufferMinPtr = bufferMin.ctypes.data_as(POINTER(c_int16))
        bufferLth = len(bufferMax)

        m = self.lib.ps6000aSetDataBuffers(c_int16(self.handle),
                                           c_enum(channel),
                                           bufferMaxPtr, bufferMinPtr,
                                           c_uint32(bufferLth),
                                           c_enum(downSampleMode))
        self.checkResult(m)

    def _lowLevelClearDataBuffers(self, channel):
        raise NotImplementedError()
        m = self.lib.ps6000aSetDataBuffers(
            c_int16(self.handle), c_enum(channel),
            c_void_p(), c_void_p(), c_uint32(0), c_enum(0))
        self.checkResult(m)

    # Bulk values.
    # These would be nice, but the user would have to provide us
    # with an array.
    # we would have to make sure that it is contiguous amonts other things
    def _lowLevelSetNoOfCaptures(self, nCaptures):
        m = self.lib.ps6000aSetNoOfCaptures(c_int16(self.handle),
                                            c_uint32(nCaptures))
        self.checkResult(m)

    # Async functions
    def _lowLevelGetValuesBulkAsync():
        raise NotImplementedError()

    # overlapped functions
    def _lowLevelGetValuesOverlapped():
        raise NotImplementedError()

    # Streaming related functions
    def _lowLevelGetStreamingLatestValues():
        raise NotImplementedError()

    def _lowLevelNoOfStreamingValues(self):
        raise NotImplementedError()
        noOfValues = c_uint32()

        m = self.lib.ps6000aNoOfStreamingValues(c_int16(self.handle),
                                                byref(noOfValues))
        self.checkResult(m)

        return noOfValues.value

    def _lowLevelRunStreaming():
        raise NotImplementedError()

    "alphabetically"

    def _lowLevelChannelCombinationsStateless(self, resolution, timebase):
        """
        Return a list of the possible channel combinations given a proposed
        configuration (`resolution` and `timebase` number) of the oscilloscope.
        It does not change the configuration of the oscilloscope.

        Bit values of the different flags in a channel combination:
            PICO_CHANNEL_A_FLAGS = 1,
            PICO_CHANNEL_B_FLAGS = 2,
            PICO_CHANNEL_C_FLAGS = 4,
            PICO_CHANNEL_D_FLAGS = 8,
            PICO_CHANNEL_E_FLAGS = 16,
            PICO_CHANNEL_F_FLAGS = 32,
            PICO_CHANNEL_G_FLAGS = 64,
            PICO_CHANNEL_H_FLAGS = 128,
            PICO_PORT0_FLAGS = 65536,
            PICO_PORT1_FLAGS = 131072,
            PICO_PORT2_FLAGS = 262144,
            PICO_PORT3_FLAGS = 524288,
        """
        # TODO raises PICO_CHANNELFLAGSCOMBINATIONS_ARRAY_SIZE_TOO_SMALL
        ChannelCombinations = create_string_buffer(b"", 100000)
        nChannelCombinations = c_uint32()
        if isinstance(resolution, str):
            resolution = self.ADC_RESOLUTIONS[resolution]
        m = self.lib.ps6000aChannelCombinationsStateless(c_int16(self.handle),
                                                         ChannelCombinations,
                                                         nChannelCombinations,
                                                         c_uint32(resolution),
                                                         c_uint32(timebase),
                                                         )
        self.checkResult(m)
        return ChannelCombinations

    def _lowLevelGetAnalogueOffsetLimits(self, range, coupling):
        raise NotImplementedError()
        # TODO, populate properties with this function
        maximumVoltage = c_float()
        minimumVoltage = c_float()

        m = self.lib.ps6000aGetAnalogueOffsetLimits(
            c_int16(self.handle), c_enum(range), c_enum(coupling),
            byref(maximumVoltage), byref(minimumVoltage))
        self.checkResult(m)

        return (maximumVoltage.value, minimumVoltage.value)

    def _lowLevelGetMaximumAvailableMemory(self):
        raise NotImplementedError()

    def _lowLevelMinimumTimebaseStateless(self):
        raise NotImplementedError()

    def _lowLevelGetNoOfCaptures(self):
        raise NotImplementedError()
        nCaptures = c_uint32()

        m = self.lib.ps6000aGetNoOfCaptures(c_int16(self.handle),
                                            byref(nCaptures))
        self.checkResult(m)

        return nCaptures.value

    def _lowLevelGetNoOfProcessedCaptures(self):
        raise NotImplementedError()

    def _lowLevelGetTriggerInfo(self):
        raise NotImplementedError()

    def _lowLevelMemorySegmentsBySamples(self):
        raise NotImplementedError()

    def _lowLevelNearestSampleIntervalStateless(self):
        raise NotImplementedError()

    def _lowLevelQueryMaxSegmentsBySamples(self):
        raise NotImplementedError()

    def _lowLevelQueryOutputEdgeDetect(self):
        raise NotImplementedError()

    def _lowLevelSetDigitalPortOff(self):
        raise NotImplementedError()

    def _lowLevelSetDigitalPortOn(self):
        raise NotImplementedError()

    def _lowLevelSetOutputEdgeDetect(self):
        raise NotImplementedError()

    # Signal Generator
    # TODO add signal generator, at least in a simple version.
    def _lowLevelSigGenApply(self):
        raise NotImplementedError()

    def _lowLevelSigGenClockManual(self):
        raise NotImplementedError()

    def _lowLevelSigGenFilter(self):
        raise NotImplementedError()

    def _lowLevelSigGenFrequency(self):
        raise NotImplementedError()

    def _lowLevelSigGenFrequencyLimits(self):
        raise NotImplementedError()

    def _lowLevelSigGenFrequencySweep(self):
        raise NotImplementedError()

    def _lowLevelSigGenLimits(self):
        raise NotImplementedError()

    def _lowLevelSigGenPause(self):
        raise NotImplementedError()

    def _lowLevelSigGenPhase(self):
        raise NotImplementedError()

    def _lowLevelSigGenPhaseSweep(self):
        raise NotImplementedError()

    def _lowLevelSigGenRange(self):
        raise NotImplementedError()

    def _lowLevelSigGenRestart(self):
        raise NotImplementedError()

    def _lowLevelSigGenSoftwareTriggerControl(self):
        raise NotImplementedError()

    def _lowLevelSigGenTrigger(self):
        raise NotImplementedError()

    def _lowLevelSigGenWaveform(self):
        raise NotImplementedError()

    def _lowLevelSigGenWaveformDutyCycle(self):
        raise NotImplementedError()
