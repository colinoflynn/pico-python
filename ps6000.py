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
                    "EXTERNAL":4, "MAX_CHANNELS":4, "TRIGGER_AUX":5, "MAX_TRIGGER_SOURCES":6}

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
        pParameter = c_void_p()
        m = self.lib.ps6000RunBlock( self.handle, numPreTrigSamples, numPostTrigSamples,
                timebase, oversample, byref(timeIndisposedMs), segmentIndex, None, byref(pParameter) )
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

        return int(st)

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

    ps.setChannel(0, 'DC', 2.0)

    #Example of simple capture
    #res = ps.setSampling(100E6, 1000)
    #print("Sampling @ %f MHz, maximum samples = %d"%(res[0]/1E6, res[1]))
    #print("Sampling delta = %f ns"%(1/res[0]*1E9))
    res = ps.setSamplingInterval(10E-9, 1000)
    print("Sampling @ %f MHz, maximum samples = %d"%(1/res[0]/1E6, res[1]))
    print("Sampling delta = %f ns"%(res[0]*1E9))

    ps.setSimpleTrigger('A', 1.0, 'Rising')

    ps.runBlock()
    while(ps.isReady() == False): time.sleep(0.01)

    #TODO: Doesn't work on larger arrays
    (data, numSamplesReturned, overflow) = ps.getDataV(0, 4096)

    print("We read %d samples from the requested %d"%(numSamplesReturned, 4096))
    print("Overflow value is %d"%(overflow))
    print("The first 100 datapoints are ")
    print(data[0:100])

    ps.close()

if __name__ == "__main__":
    examplePS6000()
