"""
This is the low level driver file for a specific Picoscope.

By this, I mean if parameters want to get passed as strings, they should be
handled by PSBase
All functions here should take things as close to integers as possible.
"""

#/usr/bin/env python2.7
# vim: set ts=4 sw=4 tw=0 et :

from __future__ import division

import math

# to load the proper dll
import platform

# Do not import or use ill definied data types
# such as short int or long
# use the values specified in the h file
# float is always defined as 32 bits
# double is defined as 64 bits
from ctypes import byref, POINTER, create_string_buffer, c_float, \
                   c_int16, c_int32, c_uint32, c_void_p
from ctypes import c_int32 as c_enum

from picoscope import PSBase

#### The following are low-level functions which should be reimplemented in all classes
class PS6000(PSBase):
    LIBNAME = "ps6000"

    NUM_CHANNELS = 4
    CHANNELS     = {"A":0, "B":1, "C":2, "D":3,
                    "External":4, "MaxChannels":4, "TriggerAux":5}


    #has_sig_gen = True
    WAVE_TYPES = {"Sine":0, "Square":1, "Triangle":2, "RampUp":3, "RampDown":4,
                  "Sinc":5, "Gaussian":6, "HalfSine":7, "DCVoltage": 8, "WhiteNoise": 9}

    SIGGEN_TRIGGER_TYPES = {"Rising":0, "Falling":1, "GateHigh":2, "GateLow":3}
    SIGGEN_TRIGGER_SOURCES = {"None":0, "ScopeTrig":1, "AuxIn":2, "ExtIn":3, "SoftTrig":4, "TriggerRaw":5}

    # This is actually different depending on the AB/CD models
    # I wonder how we could detect the difference between the oscilloscopes
    # I believe we can obtain this information from the setInfo function
    # by readign the hardware version
    # for the PS6403B version, the hardware version is "1 1",
    # an other possibility is that the PS6403B shows up as 6403 when using
    # VARIANT_INFO and others show up as PS6403X where X = A,C or D


    AWGPhaseAccumulatorSize = 32
    AWGBufferAddressWidth   = 14
    AWGMaxSamples           = 2**AWGBufferAddressWidth

    AWGDACInterval          = 5E-9 # in seconds
    AWGDACFrequency         = 1/AWGDACInterval

    # Note this is NOT what is written in the Programming guide as of version
    # 10_5_0_28
    # NOTE: if these numbers ever end up being negative, you will have to make sure
    # that they sign extend. As well as making sure that the type casting works.
    AWGMaxVal               = 0x0FFF
    AWGMinVal               = 0x0000

    AWG_INDEX_MODES = {"Single":0, "Dual":1, "Quad":2}

    def __init__(self):
        super(PS6000, self).__init__()

        """Load DLL etc"""
        if platform.system() == 'Linux':
            from ctypes import cdll
            self.lib = cdll.LoadLibrary("lib" + self.LIBNAME + ".so")
        else:
            from ctypes import windll
            self.lib = windll.LoadLibrary(self.LIBNAME + ".dll")

    def _lowLevelOpenUnit(self, sn):
        c_handle = c_int16()
        if sn is not None:
            serialNullTermStr = create_string_buffer(sn)
        else:
            serialNullTermStr = None
        # Passing None is the same as passing NULL
        m = self.lib.ps6000OpenUnit(byref(c_handle), serialNullTermStr)
        self.checkResult(m)
        self.handle = c_handle.value

    def _lowLevelCloseUnit(self):
        m = self.lib.ps6000CloseUnit(c_int16(self.handle))
        self.checkResult(m)

    def _lowLevelSetChannel(self, chNum, enabled, coupling, VRange, VOffset, BWLimited):
        m = self.lib.ps6000SetChannel(c_int16(self.handle), c_enum(chNum), c_int16(enabled),
                                      c_enum(coupling), c_enum(VRange), c_float(VOffset),
                                      c_enum(BWLimited))
        self.checkResult(m)

    def _lowLevelStop(self):
        m = self.lib.ps6000Stop(c_int16(self.handle))
        self.checkResult(m)

    def _lowLevelGetUnitInfo(self, info):
        s = create_string_buffer(256)
        requiredSize = c_int16(0);

        m = self.lib.ps6000GetUnitInfo(c_int16(self.handle), byref(s),
                                       c_int16(len(s)), byref(requiredSize),
                                       c_enum(info))
        self.checkResult(m)
        if requiredSize.value > len(s):
            s = create_string_buffer(requiredSize.value + 1)
            m = self.lib.ps6000GetUnitInfo(c_int16(self.handle), byref(s),
                                           c_int16(len(s)), byref(requiredSize),
                                           c_enum(info))
            self.checkResult(m)

        return s.value

    def _lowLevelFlashLed(self, times):
        m = self.lib.ps6000FlashLed(c_int16(self.handle), c_int16(times))
        self.checkResult(m)

    def _lowLevelSetSimpleTrigger(self, enabled, trigsrc, threshold_adc, direction, timeout_ms, auto):
        m = self.lib.ps6000SetSimpleTrigger(c_int16(self.handle), c_int16(enabled),
                                            c_enum(trigsrc), c_int16(threshold_adc),
                                            c_enum(direction), c_uint32(timeout_ms), c_int16(auto))
        self.checkResult(m)

    def _lowLevelRunBlock(self, numPreTrigSamples, numPostTrigSamples, timebase, oversample, segmentIndex):
        timeIndisposedMs = c_int32()
        m = self.lib.ps6000RunBlock(c_int16(self.handle), c_uint32(numPreTrigSamples),
                                    c_uint32(numPostTrigSamples), c_uint32(timebase),
                                    c_int16(oversample), byref(timeIndisposedMs),
                                    c_uint32(segmentIndex), c_void_p(), c_void_p())
        self.checkResult(m)
        return timeIndisposedMs.value

    def _lowLevelIsReady(self):
        ready = c_int16()
        m = self.lib.ps6000IsReady(c_int16(self.handle), byref(ready) )
        self.checkResult(m)
        if ready.value:
            return True
        else:
            return False

    def _lowLevelGetTimebase(self, tb, noSamples, oversample, segmentIndex):
        """ returns (timeIntervalSeconds, maxSamples) """
        maxSamples = c_int32()
        sampleRate = c_float()

        m = self.lib.ps6000GetTimebase2(c_int16(self.handle), c_uint32(tb),
                                        c_uint32(noSamples), byref(sampleRate),
                                        c_int16(oversample), byref(maxSamples),
                                        c_uint32(segmentIndex))
        self.checkResult(m)

        return (sampleRate.value/1.0E9, maxSamples.value)

    def getTimeBaseNum(self, sampleTimeS):
        """Convert sample time in S to something to pass to API Call"""
        maxSampleTime = (((2**32 - 1) - 4) / 156250000)

        if sampleTimeS < 6.4E-9:
            # you had the parameters inverted in the log function
            #if sampleTimeS < 200E-12:
            #    st = 0
            #st = math.floor(1/math.log(2, (sampleTimeS * 5E9)))
            st = math.floor(math.log(sampleTimeS*5E9, 2))
            st = max(st, 0)
        else:
            #Otherwise in range 2^32-1
            if sampleTimeS > maxSampleTime:
                sampleTimeS = maxSampleTime

            st = math.floor((sampleTimeS * 156250000) + 4)

        # is this cast needed?
        st = int(st)
        return st

    def getTimestepFromTimebase(self, timebase):
        if timebase < 5:
            dt = 2.**timebase/5E9
        else:
            dt = (timebase - 4.) / 156250000.
        return dt

    def _lowLevelSetAWGSimpleDeltaPhase(self, waveform, deltaPhase,
            offsetVoltage, pkToPk, indexMode, shots, triggerType, triggerSource):
        """ waveform should be an array of shorts """

        waveformPtr = waveform.ctypes.data_as(POINTER(c_int16))

        m = self.lib.ps6000SetSigGenArbitrary(
                c_int16(self.handle),
                c_uint32(int(offsetVoltage * 1E6)), # offset voltage in microvolts
                c_uint32(int(pkToPk * 1E6)), # pkToPk in microvolts
                c_uint32(int(deltaPhase)), # startDeltaPhase
                c_uint32(int(deltaPhase)), # stopDeltaPhase
                c_uint32(0),          # deltaPhaseIncrement
                c_uint32(0),          # dwellCount
                waveformPtr, # arbitraryWaveform
                c_int32(len(waveform)), # arbitraryWaveformSize
                c_enum(0), # sweepType for deltaPhase
                c_enum(0), # operation (adding random noise and whatnot)
                c_enum(indexMode), # single, dual, quad
                c_uint32(shots),
                c_uint32(0), # sweeps
                c_uint32(triggerType),
                c_uint32(triggerSource),
                c_int16(0)) # extInThreshold
        self.checkResult(m)

    def _lowLevelSetDataBuffer(self, channel, data, downSampleMode):
        """
        data should be a numpy array

        Be sure to call _lowLevelClearDataBuffer
        when you are done with the data array
        or else subsequent calls to GetValue will still use the same array.
        """
        dataPtr = data.ctypes.data_as(POINTER(c_int16))
        numSamples = len(data)

        m = self.lib.ps6000SetDataBuffer(c_int16(self.handle), c_enum(channel), dataPtr,
                                         c_uint32(numSamples), c_enum(downSampleMode))
        self.checkResult(m)

    def _lowLevelClearDataBuffer(self, channel):
        """ data should be a numpy array"""
        m = self.lib.ps6000SetDataBuffer(c_int16(self.handle), c_enum(channel), c_void_p(),
                                         c_uint32(0), c_enum(0))
        self.checkResult(m)

    def _lowLevelGetValues(self,numSamples,startIndex,downSampleRatio,downSampleMode):
        numSamplesReturned = c_uint32()
        numSamplesReturned.value = numSamples
        overflow = c_int16()
        m = self.lib.ps6000GetValues(c_int16(self.handle), c_uint32(startIndex),
                                     byref(numSamplesReturned), c_uint32(downSampleRatio),
                                     c_enum(downSampleMode), c_uint32(self.segmentIndex),
                                     byref(overflow))
        self.checkResult(m)
        return (numSamplesReturned.value, overflow.value)

    def _lowLevelSetSigGenBuiltInSimple(self, offsetVoltage, pkToPk, waveType, frequency, shots,
            triggerType, triggerSource):
        # TODO, I just noticed that V2 exists
        # Maybe change to V2 in the future
        m = self.lib.ps6000SetSigGenBuiltIn(c_int16(self.handle),
                                            c_int32(int(offsetVoltage * 1000000)),
                                            c_int32(int(pkToPk        * 1000000)),
                                            c_int16(waveType),
                                            c_float(frequency), c_float(frequency),
                                            c_float(0), c_float(0), c_enum(0), c_enum(0),
                                            c_uint32(shots), c_uint32(0), c_enum(triggerType), c_enum(triggerSource),
                                            c_int16(0))
        self.checkResult(m)


