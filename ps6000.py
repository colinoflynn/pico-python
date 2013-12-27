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

from ctypes import byref, c_long, c_short, c_float, create_string_buffer, POINTER, c_uint32

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
        handlePointer = c_short()
        if sn is not None:
            serialNullTermStr = create_string_buffer(sn)
        else:
            serialNullTermStr = None

        # Passing None is the same as passing NULL
        m = self.lib.ps6000OpenUnit(byref(handlePointer), serialNullTermStr)
        self.checkResult(m)
        self.handle = handlePointer
    def _lowLevelCloseUnit(self):
        m = self.lib.ps6000CloseUnit(self.handle)
        self.checkResult(m)
        self.handle = None

    def _lowLevelSetChannel(self, chNum, enabled, coupling, VRange, VOffset, BWLimited):
        m = self.lib.ps6000SetChannel(self.handle, chNum, enabled, coupling, VRange,
                c_float(VOffset), BWLimited)
        self.checkResult(m)


    def _lowLevelStop(self):
        m = self.lib.ps6000Stop(self.handle)
        self.checkResult(m)

    def _lowLevelGetUnitInfo(self, info):
        s = create_string_buffer(256)
        requiredSize = c_short(0);

        m = self.lib.ps6000GetUnitInfo(self.handle, byref(s), len(s), byref(requiredSize), info);
        self.checkResult(m)
        if requiredSize.value > len(s):
            s = create_string_buffer(requiredSize.value + 1)
            m = self.lib.ps6000GetUnitInfo(self.handle, byref(s), len(s), byref(requiredSize), info);
            self.checkResult(m)

        return s.value

    def _lowLevelFlashLed(self, times):
        m = self.lib.ps6000FlashLed(self.handle, times)
        self.checkResult(m)

    def _lowLevelSetSimpleTrigger(self, enabled, trigsrc, threshold_adc, direction, timeout_ms, auto):
        m = self.lib.ps6000SetSimpleTrigger(self.handle, enabled, trigsrc, threshold_adc,
                direction, timeout_ms, auto)
        self.checkResult(m)

    def _lowLevelRunBlock(self, numPreTrigSamples, numPostTrigSamples, timebase, oversample, segmentIndex):
        timeIndisposedMs = c_long()
        m = self.lib.ps6000RunBlock( self.handle, numPreTrigSamples, numPostTrigSamples,
                timebase, oversample, byref(timeIndisposedMs), segmentIndex, None, None)
        self.checkResult(m)
        return timeIndisposedMs.value

    def _lowLevelIsReady(self):
        ready = c_short()
        m = self.lib.ps6000IsReady( self.handle, byref(ready) )
        self.checkResult(m)
        if ready.value:
            return True
        else:
            return False

    def _lowLevelGetTimebase(self, tb, noSamples, oversample, segmentIndex):
        """ returns (timeIntervalSeconds, maxSamples) """
        maxSamples = c_long()
        sampleRate = c_float()

        m = self.lib.ps6000GetTimebase2(self.handle, tb, noSamples, byref(sampleRate),
                oversample, byref(maxSamples), segmentIndex)
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

        waveformPtr = waveform.ctypes.data_as(POINTER(c_short))

        m = self.lib.ps6000SetSigGenArbitrary(
                self.handle,
                c_uint32(int(offsetVoltage * 1E6)), # offset voltage in microvolts
                c_uint32(int(pkToPk * 1E6)), # pkToPk in microvolts
                c_uint32(int(deltaPhase)), # startDeltaPhase
                c_uint32(int(deltaPhase)), # stopDeltaPhase
                0,          # deltaPhaseIncrement
                0,          # dwellCount
                waveformPtr, # arbitraryWaveform
                len(waveform), # arbitraryWaveformSize
                0, # sweepType for deltaPhase
                0, # operation (adding random noise and whatnot)
                indexMode, # single, dual, quad
                shots,
                0, # sweeps
                triggerType,
                triggerSource,
                0) # extInThreshold
        self.checkResult(m)

    def _lowLevelSetDataBuffer(self, channel, data, downSampleMode):
        """ data should be a numpy array"""
        dataPtr = data.ctypes.data_as(POINTER(c_short))
        numSamples = len(data)
        m = self.lib.ps6000SetDataBuffer( self.handle, channel, dataPtr,
                numSamples, downSampleMode )
        self.checkResult(m)

    def _lowLevelGetValues(self,numSamples,startIndex,downSampleRatio,downSampleMode):
        numSamplesReturned = c_long()
        numSamplesReturned.value = numSamples
        overflow = c_short()
        m = self.lib.ps6000GetValues( self.handle, startIndex, byref(numSamplesReturned),
                downSampleRatio, downSampleMode, self.segmentIndex, byref(overflow) )
        self.checkResult(m)
        return (numSamplesReturned.value, overflow.value)

    def _lowLevelSetSigGenBuiltInSimple(self, offsetVoltage, pkToPk, waveType, frequency, shots,
            triggerType, triggerSource):
        m = self.lib.ps6000SetSigGenBuiltIn(self.handle, int(offsetVoltage * 1E6),
                int(pkToPk * 1E6), waveType, c_float(frequency), c_float(frequency),
                0, 0, 0, 0, shots, 0, triggerType, triggerSource, 0)
        self.checkResult(m)


