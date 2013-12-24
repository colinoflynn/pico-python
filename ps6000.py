#/usr/bin/env python2.7
# vim: set ts=4 sw=4 tw=0 et :

import math
import time
import inspect

# to load the proper dll
import platform

from ctypes import byref, c_long, c_void_p, c_short, c_float, create_string_buffer, c_ulong, POINTER, cdll

from picoscope import PSBase

#### The following are low-level functions which should be reimplemented in all classes
class PS6000(PSBase):
    LIBNAME = "ps6000"

    NUM_CHANNELS = 4
    CHANNELS     = {"A":0, "B":1, "C":2, "D":3,
                    "External":4, "MaxChannels":4, "TriggerAux":5}


    has_sig_gen = True
    WAVE_TYPES = {"Sine":0, "Square":1, "Triangle":2, "RampUp":3, "RampDown":4,
                  "Sinc":5, "Gaussian":6, "HalfSine":7, "DCVoltage": 8, "WhiteNoise": 9}

    SIGGEN_TRIGGER_TYPES = {"Rising":0, "Falling":1, "GateHigh":2, "GateLow":3}
    SIGGEN_TRIGGER_SOURCES = {"None":0, "ScopeTrig":1, "AuxIn":2, "ExtIn":3, "SoftTrig":4, "TriggerRaw":5}

    def __init__(self):
        super(PS6000, self).__init__()

        if platform.system() == 'Linux':
            self.lib = cdll.LoadLibrary("lib" + self.LIBNAME + ".so")
        else:
            """Load DLL etc"""
            # This was windll before, I don't know what the difference is.
            # can't test it now
            self.lib = cdll.LoadLibrary(self.LIBNAME + ".dll")

    def _lowLevelSetChannel(self, chNum, enabled, coupling, VRange, VOffset, BWLimited):
        #VOffset = ctypes.c_float(VOffset)
        m = self.lib.ps6000SetChannel(self.handle, chNum, enabled, coupling, VRange,
                c_float(VOffset), BWLimited)
        self.checkResult(m)

    def _lowLevelOpenUnit(self, sn):
        handlePointer = c_short()
        if sn is not None:
            serialNullTermStr = create_string_buffer(sn)

        # Passing None is the same as passing NULL
        m = self.lib.ps6000OpenUnit(byref(handlePointer), sn)
        self.checkResult(m)
        self.handle = handlePointer

    def _lowLevelCloseUnit(self):
        m = self.lib.ps6000CloseUnit(self.handle)
        self.checkResult(m)

    def _lowLevelStop(self):
        m = self.lib.ps6000Stop(self.handle)
        self.checkResult(m)

    def _lowLevelGetUnitInfo(self, info):
        s = create_string_buffer(256)
        requiredSize = c_short(0);

        m = self.lib.ps6000GetUnitInfo(self.handle, byref(s), len(s), byref(requiredSize), info);
        if requiredSize.value > len(s):
            s = create_string_buffer(requiredSize.value + 1)
            m = self.lib.ps6000GetUnitInfo(self.handle, byref(s), len(s), byref(requiredSize), info);

        self.checkResult(m)
        return s.value

    def _lowLevelFlashLed(self, times):
        m = self.lib.ps6000FlashLed(self.handle, times)
        self.checkResult(m)

    def _lowLevelSetSimpleTrigger(self, enabled, trigsrc, threshold_adc, direction, delay, auto):
        m = self.lib.ps6000SetSimpleTrigger(self.handle, enabled, trigsrc, threshold_adc,
                direction, delay, auto)
        self.checkResult(m)

    def _lowLevelRunBlock(self, numPreTrigSamples, numPostTrigSamples, timebase, oversample, segmentIndex):
        timeIndisposedMs = c_long()
        m = self.lib.ps6000RunBlock( self.handle, numPreTrigSamples, numPostTrigSamples,
                timebase, oversample, byref(timeIndisposedMs), segmentIndex, None, None)
        self.checkResult(m)

    def _lowLevelIsReady(self):
        ready = c_short()
        m = self.lib.ps6000IsReady( self.handle, byref(ready) )
        if ready.value:
            isDone = True
        else:
            isDone = False
        self.checkResult(m)
        return isDone

    def _lowLevelGetTimebase(self, tb, noSamples, oversample, segmentIndex):
        """ returns [timeIntervalSeconds, maxSamples] """
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
            if sampleTimeS < 200E-12:
                st = 0
            else:
                st = math.floor(1/math.log(2, (sampleTimeS * 5E9)))

        else:
            #Otherwise in range 2^32-1
            if sampleTimeS > maxSampleTime:
                sampleTimeS = maxSampleTime

            st = math.floor((sampleTimeS * 156250000) + 4)

        st = int(st)

        if st < 5:
            dt = float(2.**st)/5E9
        else:
            dt = float(st - 4.) / 156250000.

        return (st, dt)

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

    def _lowLevelSetSigGenSimple(self, offsetVoltage, pkToPk, waveType, frequency, shots,
            triggerType, triggerSource):
        if waveType is None:
            waveType = self.WAVE_TYPES["Sine"]
        if triggerType is None:
            triggerType = self.SIGGEN_TRIGGER_TYPES["Rising"]
        if triggerSource is None:
            triggerSource = self.SIGGEN_TRIGGER_SOURCES["None"]

        if not isinstance(waveType, int):
            waveType = self.WAVE_TYPES[waveType]
        if not isinstance(triggerType, int):
            triggerType = self.SIGGEN_TRIGGER_TYPES[triggerType]
        if not isinstance(triggerSource, int):
            triggerSource = self.SIGGEN_TRIGGER_SOURCES[triggerSource]

        m = self.lib.ps6000SetSigGenBuiltIn(self.handle, int(offsetVoltage * 1E6),
                int(pkToPk * 1E6), waveType, c_float(frequency), c_float(frequency),
                0, 0, 0, 0, shots, 0, triggerType, triggerSource, 0)
        self.checkResult(m)

def examplePS6000():
    import textwrap
    print(textwrap.fill("This demo will use the AWG to generate a gaussian pulse and measure " +
    "it on Channel A. To run this demo connect the AWG output of the PS6000 channel A."))

    print("Attempting to open Picoscope 6000...")

    # see page 13 of the manual to understand how to work this beast
    ps = PS6000()
    ps.open()

    ps.printUnitInfo()

    #Use to ID unit
    ps.flashLed(4)
    time.sleep(2)

    (interval, nSamples, maxSamples) = ps.setSamplingInterval(10E-9, 1E-3)
    print("Sampling interval = %f ns"%(interval*1E9));
    print("Taking  samples = %d"%nSamples)
    print("Maximum samples = %d"%maxSamples)

    ps.setChannel('A', 'DC', 50E-3, 0.0, True, False)
    ps.setSimpleTrigger('A', 0.0, 'Rising')


    # Technically, this should generate a a 2.2 V peak to peak waveform, but there is a bug
    # with the picoscope, causing it to only generate a useless waveform....
    ps.setSigGenSimple(0, 2.2, "Square", 10E6)

    ps.runBlock()
    #while(ps.isReady() == False): time.sleep(0.01)
    ps.waitReady()

    # returns a numpy array
    (data, numSamplesReturned, overflow) = ps.getDataV(0, nSamples)

    # call this when you are done taking data
    ps.stop()

    print("We read %d samples from the requested %d"%(numSamplesReturned, nSamples))
    print("Overflow value is %d"%(overflow))
    print("The first 100 datapoints are ")
    print(data[0:100])

    ps.close()

if __name__ == "__main__":
    examplePS6000()
