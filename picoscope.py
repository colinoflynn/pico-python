# -*- coding: utf-8
# Edited by Mark Harfouche
#
# My idea is that this file should be a python only file with no use of ctypes
# or knowledge that it is being used
# All ctypes stuff should be in the daughter files
#
# I think that the names of the functions should resemple the picoscope function
# names as much as possible
#
# Colin O'Flynn, Copyright (C) 2013. All Rights Reserved. <coflynn@newae.com>
#
# This is a Python 2.7 (or so) library for the Pico Scope. It uses the provided DLL
# for actual communications with the instrument. There have been a few examples around,
# but this one tries to improve on them via:
#  * Subclass instrument-specific stuff, so can support more families
#  * Use exceptions to raise errors, and gives you nice english error messages (copied from PS Manual)
#  * Provide higher-level functions (e.g. just setup timebase, function deals with instrument-specific limitations)
#
# So far INCOMPLETE and tested only with PS6000 scope. May change in the future.
#
#
# Inspired by Patrick Carle's code at http://www.picotech.com/support/topic11239.html
# which was adapted from http://www.picotech.com/support/topic4926.html


import inspect
import time

import numpy as np

class CaseInsensitiveDict(dict):
    def __setitem__(self, key, value):
        super(CaseInsensitiveDict, self).__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super(CaseInsensitiveDict, self).__getitem__(key.lower())

class PSBase(object):
    #Specify Library
    LIBNAME = "ps6000"

    ###You must reimplement this in device specific classes
    #Maximum Limits
    MAX_VALUE = 32764
    MIN_VALUE = -32764
    EXT_MAX_VALUE = 32767
    EXT_MIN_VALUE = -32767
    EXT_RANGE_VOLTS = 20

    ###You must reimplement this in device specific classes
    CHANNEL_RANGE = [{"rangeV":20E-3, "apivalue":1, "rangeStr":"20 mV"},
                     {"rangeV":50E-3, "apivalue":2, "rangeStr":"50 mV"},
                     {"rangeV":100E-3, "apivalue":3, "rangeStr":"100 mV"},
                     {"rangeV":200E-3, "apivalue":4, "rangeStr":"200 mV"},
                     {"rangeV":500E-3, "apivalue":5, "rangeStr":"500 mV"},
                     {"rangeV":1.0, "apivalue":6, "rangeStr":"1 V"},
                     {"rangeV":2.0, "apivalue":7, "rangeStr":"2 V"},
                     {"rangeV":5.0, "apivalue":8, "rangeStr":"5 V"},
                     ]

    ###You must reimplement this in device specific classes
    NUM_CHANNELS = 2
    CHANNELS = {"A":0, "B":1}

    ###You must reimplement this in device specific classes
    CHANNEL_COUPLINGS = {"DC50": 2, "DC":1, "AC":0}
    has_sig_gen = False


    # If we don't get this CaseInsentiveDict working, I would prefer to stick
    # with their spelling of archaic C all caps for this. I know it is silly,
    # but it removes confusion for certain things like
    # DC_VOLTAGE = DCVoltage or DcVoltage or DC_Voltage
    # or even better
    # SOFT_TRIG = SoftwareTrigger vs SoftTrig

    # For some reason this isn't working with me :S
    #THRESHOLD_TYPE = CaseInsensitiveDict(
    THRESHOLD_TYPE = {"Above":0,
                      "Below":1,
                      "Rising":2,
                      "Falling":3,
                      "RiseOrFall":4}

    ### getUnitInfo parameter types
    UNIT_INFO_TYPES = { "DRIVER_VERSION"           : 0,
                        "USB_VERSION"              : 1,
                        "HARDWARE_VERSION"         : 2,
                        "VARIANT_INFO"             : 3,
                        "BATCH_AND_SERIAL"         : 4,
                        "CAL_DATE"                 : 5,
                        "KERNEL_VERSION"           : 6,
                        "DIGITAL_HARDWARE_VERSION" : 7,
                        "ANALOGUE_HARDWARE_VERSION": 8}

    def __init__(self):
        # Should be defined in child
        self.lib = None
        self.handle = None

        self.CHRange = [None]*self.NUM_CHANNELS
        self.CHOffset = [None]*self.NUM_CHANNELS

    def checkResult(self, ec):
        """Check result of function calls, raise exception if not 0"""
        if ec == 0:
            return

        else:
            ecName = self.errorNumToName(ec)
            ecDesc = self.errorNumToDesc(ec)
            raise IOError('Error calling %s: %s (%s)'%(inspect.stack()[1][3], ecName, ecDesc))

    def errorNumToName(self, num):
        """Convert error number to name"""
        for t in self.ERROR_CODES:
            if t[0] == num:
                return t[1]

    def errorNumToDesc(self, num):
        """Convert error number to description"""
        for t in self.ERROR_CODES:
            if t[0] == num:
                try:
                    return t[2]
                except IndexError:
                    return ""

    def getUnitInfo(self, info):
        """ returns a string containing the requested information """
        if not isinstance(info, int):
            info = self.UNIT_INFO_TYPES[info]
        return self._lowLevelGetUnitInfo(info)

    def printUnitInfo(self):
        """ Prints the unit information in a human readible way """
        print("Driver version   " + self.getUnitInfo("DRIVER_VERSION"))
        print("USB version      " + self.getUnitInfo("USB_VERSION"))
        print("Hardware version " + self.getUnitInfo("HARDWARE_VERSION"))
        print("Found Picoscope  " + self.getUnitInfo("VARIANT_INFO"))
        print("Serial number    " + self.getUnitInfo("BATCH_AND_SERIAL"))
        print("Calibrated on    " + self.getUnitInfo("CAL_DATE"))
        print("Kernel version   " + self.getUnitInfo("KERNEL_VERSION"))
        print("Digital version  " + self.getUnitInfo("DIGITAL_HARDWARE_VERSION"))
        print("Analog version   " + self.getUnitInfo("ANALOGUE_HARDWARE_VERSION"))


    def setChannel(self, channel='A', coupling="AC", VRange=2.0, VOffset=0.0, enabled=True, BWLimited=False):
        """ Sets up a specific channel """
        if enabled:
            enabled = 1
        else:
            enabled = 0

        if not isinstance(channel, int):
            chNum = self.CHANNELS[channel]
        else:
            chNum = channel

        coupling = self.CHANNEL_COUPLINGS[coupling]

        # I don't know if I like the fact that you are comparing floating points
        # I think this should just be a string, because then we know the user is
        # in charge of properly formatting it
        try:
            VRangeAPI = (item for item in self.CHANNEL_RANGE if item["rangeV"] == VRange).next()
            VRangeAPI = VRangeAPI["apivalue"]
        except StopIteration:
            rstr = ""
            for t in self.CHANNEL_RANGE: rstr += "%f (%s), "%(t["rangeV"], t["rangeStr"])
            raise ValueError("%f is invalid range. Valid ranges: %s"%(VRange, rstr))

        if BWLimited:
            BWLimited = 1
        else:
            BWLimited = 0

        self._lowLevelSetChannel(chNum, enabled, coupling, VRangeAPI, VOffset, BWLimited)

        # if all was successful, save the parameters
        self.CHRange[chNum] = VRange
        self.CHOffset[chNum] = VOffset

    def runBlock(self, pretrig=0.0):
        """Runs a single block, must have already called setSampling for proper setup"""

        # getting max samples is riddiculous. 1GS buffer means it will take so long
        nSamples = min(self.noSamples, self.maxSamples)

        self._lowLevelRunBlock(int(nSamples*pretrig), int(nSamples*(1-pretrig)), self.timebase,
                self.oversample, self.segmentIndex)

    def isReady(self):
        """Check if scope done"""
        return self._lowLevelIsReady()

    def waitReady(self):
        while(self.isReady() == False): time.sleep(0.01)


    def setSamplingInterval(self, sampleInterval, duration, oversample=0, segmentIndex=0):
        """Returns [actualSampleInterval, noSamples, maxSamples]"""
        self.oversample = oversample
        self.segmentIndex = segmentIndex
        (self.timebase, timebase_dt) = self.getTimeBaseNum(sampleInterval)
        print timebase_dt

        noSamples = int(round(duration / timebase_dt))

        m = self._lowLevelGetTimebase(self.timebase, noSamples, oversample, segmentIndex)

        self.sampleInterval = m[0]
        self.sampleRate = 1.0/m[0]
        self.maxSamples = m[1]
        self.noSamples = noSamples
        return (self.sampleInterval, self.noSamples, self.maxSamples)

    def setSamplingFrequency(self, sampleFreq, noSamples, oversample=0, segmentIndex=0):
        """Returns [actualSampleFreq, maxSamples]"""
        sampleInterval = 1.0 * sampleFreq
        duration = noSamples * sampleInterval
        self.setSamplingInterval(sampleInterval, duration, oversample, segmentIndex)
        return (self.sampleRate, self.maxSamples)

    def setSampling(self, sampleFreq, noSamples, oversample=0, segmentIndex=0):
        """Kept for backwards compatibilit, use setSamplingInterval or
           setSamplingFrequency instead"""
        return self.setSamplingFrequency(sampleFreq, noSamples, oversample, segmentIndex)



    def setSimpleTrigger(self, trigSrc, threshold_V=0, direction="Rising", delay=0, timeoutms=100, enabled=True):
        """Simple trigger setup, only allows level"""

        if enabled:
            enabled = 1
        else:
            enabled = 0


        direction = self.THRESHOLD_TYPE[direction]
        if not isinstance(trigSrc, int):
            trigSrc = self.CHANNELS[trigSrc]

        if trigSrc >= self.NUM_CHANNELS:
            print("We do not support AUX triggering yet...")
            return -1

        a2v = self.CHRange[trigSrc] / self.MAX_VALUE
        threshold_adc = int(threshold_V / a2v)

        self._lowLevelSetSimpleTrigger(enabled, trigSrc, threshold_adc, direction, delay, timeoutms)


    def flashLed(self, times=5, start=False, stop=False):
        """Flash the front panel LEDs"""

        if start:
            times = -1

        if stop:
            times = 0

        self._lowLevelFlashLed(times)

    def getData(self, channel, numSamples=0, startIndex=0, downSampleRatio=1, downSampleMode=0):
        return self.getDataV(channel, numSamples, startIndex, downSampleRatio, downSampleMode)

    def getDataV(self, channel, numSamples=0, startIndex=0, downSampleRatio=1, downSampleMode=0):
        (data, numSamplesReturned, overflow) = self.getDataRaw(channel, numSamples, startIndex, downSampleRatio, downSampleMode)

        a2v = self.CHRange[channel] / float(self.MAX_VALUE)
        data = data * a2v + self.CHOffset[channel]
        return (data, numSamplesReturned, overflow)

    def getDataRaw(self, channel, numSamples=0, startIndex=0, downSampleRatio=1, downSampleMode=0):

        if not isinstance(channel, int):
            channel = self.CHANNELS[channel]

        if numSamples == 0:
            # maxSamples is probably huge, 1Gig Sample can be HUGE....
            numSamples = min(self.maxSamples, 4096)

        data = np.empty(numSamples, dtype=np.int16)

        self._lowLevelSetDataBuffer(channel, data, downSampleMode)
        (numSamplesReturned, overflow) = self._lowLevelGetValues(numSamples, startIndex, downSampleRatio, downSampleMode)

        # No we should not warn about this.
        # I'm going to assume the user is advanced and knows to check this himself
        # if things are weird with data.
        #if overflow != 0:
            #print "WARNING: Overflow detected. Should we raise exception?"

        return (data, numSamplesReturned, overflow)

    def setSigGenSimple(self, offsetVoltage=0, pkToPk=2, waveType=None, frequency=1E6,
            shots=1, triggerType=None, triggerSource=None):
        """ I don't expose all the options from setSigGenBuiltIn so I'm not
            calling it that. Their signal generator can actually do quite fancy
            things that I don't care for"""
        if self.has_sig_gen == False:
            raise NotImplementedError()
        self._lowLevelSetSigGenSimple(offsetVoltage, pkToPk, waveType, frequency,
                shots, triggerType, triggerSource)

    def open(self, sn=None):
        """Open the scope, if sn is None just opens first one found"""

        self._lowLevelOpenUnit(sn)

    def close(self):
        """Close the scope"""
        self._lowLevelCloseUnit()
    def stop(self):
        self._lowLevelStop()

    def __del__(self):
        self.close()

    ###Error codes - copied from PS6000 programmers manual. I think they are fairly unviersal though, just ignore ref to 'PS6000'...
    #To get formatting correct do following copy-replace in Programmers Notepad
    #1. Copy/replace ' - ' with '", "'
    #2. Copy/replace '\r' with '"],\r' (enable slash expressions when doing this)
    #3. Copy/replace '^([0-9A-F]{2} ){1}' with '0x\1, "' (enable regex when doing this)
    #4. Copy/replace '^([0-9A-F]{3} ){1}' with '0x\1, "' (enable regex when doing this)
    #5. Copy/repplace '0x' with '[0x'

    ERROR_CODES = [[0x00 , "PICO_OK", "The PicoScope 6000 is functioning correctly."],
        [0x01 , "PICO_MAX_UNITS_OPENED", "An attempt has been made to open more than PS6000_MAX_UNITS."],
        [0x02 , "PICO_MEMORY_FAIL", "Not enough memory could be allocated on the host machine."],
        [0x03 , "PICO_NOT_FOUND", "No PicoScope 6000 could be found."],
        [0x04 , "PICO_FW_FAIL", "Unable to download firmware."],
        [0x05 , "PICO_OPEN_OPERATION_IN_PROGRESS"],
        [0x06 , "PICO_OPERATION_FAILED"],
        [0x07 , "PICO_NOT_RESPONDING", "The PicoScope 6000 is not responding to commands from the PC."],
        [0x08 , "PICO_CONFIG_FAIL", "The configuration information in the PicoScope 6000 has become corrupt or is missing."],
        [0x09 , "PICO_KERNEL_DRIVER_TOO_OLD", "The picopp.sys file is too old to be used with the device driver."],
        [0x0A , "PICO_EEPROM_CORRUPT", "The EEPROM has become corrupt, so the device will use a default setting."],
        [0x0B , "PICO_OS_NOT_SUPPORTED", "The operating system on the PC is not supported by this driver."],
        [0x0C , "PICO_INVALID_HANDLE", "There is no device with the handle value passed."],
        [0x0D , "PICO_INVALID_PARAMETER", "A parameter value is not valid."],
        [0x0E , "PICO_INVALID_TIMEBASE", "The timebase is not supported or is invalid."],
        [0x0F , "PICO_INVALID_VOLTAGE_RANGE", "The voltage range is not supported or is invalid."],
        [0x10 , "PICO_INVALID_CHANNEL", "The channel number is not valid on this device or no channels have been set."],
        [0x11 , "PICO_INVALID_TRIGGER_CHANNEL", "The channel set for a trigger is not available on this device."],
        [0x12 , "PICO_INVALID_CONDITION_CHANNEL", "The channel set for a condition is not available on this device."],
        [0x13 , "PICO_NO_SIGNAL_GENERATOR", "The device does not have a signal generator."],
        [0x14 , "PICO_STREAMING_FAILED", "Streaming has failed to start or has stopped without user request."],
        [0x15 , "PICO_BLOCK_MODE_FAILED", "Block failed to start", "a parameter may have been set wrongly."],
        [0x16 , "PICO_NULL_PARAMETER", "A parameter that was required is NULL."],
        [0x18 , "PICO_DATA_NOT_AVAILABLE", "No data is available from a run block call."],
        [0x19 , "PICO_STRING_BUFFER_TOO_SMALL", "The buffer passed for the information was too small."],
        [0x1A , "PICO_ETS_NOT_SUPPORTED", "ETS is not supported on this device."],
        [0x1B , "PICO_AUTO_TRIGGER_TIME_TOO_SHORT", "The auto trigger time is less than the time it will take to collect the pre-trigger data."],
        [0x1C , "PICO_BUFFER_STALL", "The collection of data has stalled as unread data would be overwritten."],
        [0x1D , "PICO_TOO_MANY_SAMPLES", "Number of samples requested is more than available in the current memory segment."],
        [0x1E , "PICO_TOO_MANY_SEGMENTS", "Not possible to create number of segments requested."],
        [0x1F , "PICO_PULSE_WIDTH_QUALIFIER", "A null pointer has been passed in the trigger function or one of the parameters is out of range."],
        [0x20 , "PICO_DELAY", "One or more of the hold-off parameters are out of range."],
        [0x21 , "PICO_SOURCE_DETAILS", "One or more of the source details are incorrect."],
        [0x22 , "PICO_CONDITIONS", "One or more of the conditions are incorrect."],
        [0x23 , "PICO_USER_CALLBACK", "The driver's thread is currently in the ps6000BlockReady callback function and therefore the action cannot be carried out."],
        [0x24 , "PICO_DEVICE_SAMPLING", "An attempt is being made to get stored data while streaming. Either stop streaming by calling ps6000Stop, or use ps6000GetStreamingLatestValues."],
        [0x25 , "PICO_NO_SAMPLES_AVAILABLE", "because a run has not been completed."],
        [0x26 , "PICO_SEGMENT_OUT_OF_RANGE", "The memory index is out of range."],
        [0x27 , "PICO_BUSY", "Data cannot be returned yet."],
        [0x28 , "PICO_STARTINDEX_INVALID", "The start time to get stored data is out of range."],
        [0x29 , "PICO_INVALID_INFO", "The information number requested is not a valid number."],
        [0x2A , "PICO_INFO_UNAVAILABLE", "The handle is invalid so no information is available about the device. Only PICO_DRIVER_VERSION is available."],
        [0x2B , "PICO_INVALID_SAMPLE_INTERVAL", "The sample interval selected for streaming is out of range."],
        [0x2D , "PICO_MEMORY", "Driver cannot allocate memory."],
        [0x2E , "PICO_SIG_GEN_PARAM", "Incorrect parameter passed to signal generator."],
        [0x34 , "PICO_WARNING_AUX_OUTPUT_CONFLICT", "AUX cannot be used as input and output at the same time."],
        [0x35 , "PICO_SIGGEN_OUTPUT_OVER_VOLTAGE", "The combined peak to peak voltage and the analog offset voltage exceed the allowable voltage the signal generator can produce."],
        [0x36 , "PICO_DELAY_NULL", "NULL pointer passed as delay parameter."],
        [0x37 , "PICO_INVALID_BUFFER", "The buffers for overview data have not been set while streaming."],
        [0x38 , "PICO_SIGGEN_OFFSET_VOLTAGE", "The analog offset voltage is out of range."],
        [0x39 , "PICO_SIGGEN_PK_TO_PK", "The analog peak to peak voltage is out of range."],
        [0x3A , "PICO_CANCELLED", "A block collection has been cancelled."],
        [0x3B , "PICO_SEGMENT_NOT_USED", "The segment index is not currently being used."],
        [0x3C , "PICO_INVALID_CALL", "The wrong GetValues function has been called for the collection mode in use."],
        [0x3F , "PICO_NOT_USED", "The function is not available."],
        [0x40 , "PICO_INVALID_SAMPLERATIO", "The aggregation ratio requested is out of range."],
        [0x41 , "PICO_INVALID_STATE", "Device is in an invalid state."],
        [0x42 , "PICO_NOT_ENOUGH_SEGMENTS", "The number of segments allocated is fewer than the number of captures requested."],
        [0x43 , "PICO_DRIVER_FUNCTION", "You called a driver function while another driver function was still being processed."],
        [0x45 , "PICO_INVALID_COUPLING", "An invalid coupling type was specified in ps6000SetChannel."],
        [0x46 , "PICO_BUFFERS_NOT_SET", "An attempt was made to get data before a data buffer was defined."],
        [0x47 , "PICO_RATIO_MODE_NOT_SUPPORTED", "The selected downsampling mode (used for data reduction) is not allowed."],
        [0x49 , "PICO_INVALID_TRIGGER_PROPERTY", "An invalid parameter was passed to ps6000SetTriggerChannelProperties."],
        [0x4A , "PICO_INTERFACE_NOT_CONNECTED", "The driver was unable to contact the oscilloscope."],
        [0x4D , "PICO_SIGGEN_WAVEFORM_SETUP_FAILED", "A problem occurred in ps6000SetSigGenBuiltIn or ps6000SetSigGenArbitrary."],
        [0x4E , "PICO_FPGA_FAIL"],
        [0x4F , "PICO_POWER_MANAGER"],
        [0x50 , "PICO_INVALID_ANALOGUE_OFFSET", "An impossible analogue offset value was specified in ps6000SetChannel."],
        [0x51 , "PICO_PLL_LOCK_FAILED", "Unable to configure the PicoScope 6000."],
        [0x52 , "PICO_ANALOG_BOARD", "The oscilloscope's analog board is not detected, or is not connected to the digital board."],
        [0x53 , "PICO_CONFIG_FAIL_AWG", "Unable to configure the signal generator."],
        [0x54 , "PICO_INITIALISE_FPGA", "The FPGA cannot be initialized, so unit cannot be opened."],
        [0x56 , "PICO_EXTERNAL_FREQUENCY_INVALID", "The frequency for the external clock is not within ±5% of the stated value."],
        [0x57 , "PICO_CLOCK_CHANGE_ERROR", "The FPGA could not lock the clock signal."],
        [0x58 , "PICO_TRIGGER_AND_EXTERNAL_CLOCK_CLASH", "You are trying to configure the AUX input as both a trigger and a reference clock."],
        [0x59 , "PICO_PWQ_AND_EXTERNAL_CLOCK_CLASH", "You are trying to configure the AUX input as both a pulse width qualifier and a reference clock."],
        [0x5A , "PICO_UNABLE_TO_OPEN_SCALING_FILE", "The scaling file set can not be opened."],
        [0x5B , "PICO_MEMORY_CLOCK_FREQUENCY", "The frequency of the memory is reporting incorrectly."],
        [0x5C , "PICO_I2C_NOT_RESPONDING", "The I2C that is being actioned is not responding to requests."],
        [0x5D , "PICO_NO_CAPTURES_AVAILABLE", "There are no captures available and therefore no data can be returned."],
        [0x5E , "PICO_NOT_USED_IN_THIS_CAPTURE_MODE", "The capture mode the device is currently running in does not support the current request."],
        [0x103 , "PICO_GET_DATA_ACTIVE", "Reserved"],
        [0x104 , "PICO_IP_NETWORKED", "The device is currently connected via the IP Network socket and thus the call made is not supported."],
        [0x105 , "PICO_INVALID_IP_ADDRESS", "An IP address that is not correct has been passed to the driver."],
        [0x106 , "PICO_IPSOCKET_FAILED", "The IP socket has failed."],
        [0x107 , "PICO_IPSOCKET_TIMEDOUT", "The IP socket has timed out."],
        [0x108 , "PICO_SETTINGS_FAILED", "The settings requested have failed to be set."],
        [0x109 , "PICO_NETWORK_FAILED", "The network connection has failed."],
        [0x10A , "PICO_WS2_32_DLL_NOT_LOADED", "Unable to load the WS2 dll."],
        [0x10B , "PICO_INVALID_IP_PORT", "The IP port is invalid."],
        [0x10C , "PICO_COUPLING_NOT_SUPPORTED", "The type of coupling requested is not supported on the opened device."],
        [0x10D , "PICO_BANDWIDTH_NOT_SUPPORTED", "Bandwidth limit is not supported on the opened device."],
        [0x10E , "PICO_INVALID_BANDWIDTH", "The value requested for the bandwidth limit is out of range."],
        [0x10F , "PICO_AWG_NOT_SUPPORTED", "The device does not have an arbitrary waveform generator."],
        [0x110 , "PICO_ETS_NOT_RUNNING", "Data has been requested with ETS mode set but run block has not been called, or stop has been called."],
        [0x111 , "PICO_SIG_GEN_WHITENOISE_NOT_SUPPORTED", "White noise is not supported on the opened device."],
        [0x112 , "PICO_SIG_GEN_WAVETYPE_NOT_SUPPORTED", "The wave type requested is not supported by the opened device."],
        [0x116 , "PICO_SIG_GEN_PRBS_NOT_SUPPORTED", "Siggen does not generate pseudorandom bit stream."],
        [0x117 , "PICO_ETS_NOT_AVAILABLE_WITH_LOGIC_CHANNELS", "When a digital port is enabled, ETS sample mode is not available for use."],
        [0x118 , "PICO_WARNING_REPEAT_VALUE", "Not applicable to this device."],
        [0x119 , "PICO_POWER_SUPPLY_CONNECTED", "The DC power supply is connected."],
        [0x11A , "PICO_POWER_SUPPLY_NOT_CONNECTED", "The DC power supply isn’t connected."],
        [0x11B , "PICO_POWER_SUPPLY_REQUEST_INVALID", "Incorrect power mode passed for current power source."],
        [0x11C , "PICO_POWER_SUPPLY_UNDERVOLTAGE", "The supply voltage from the USB source is too low."],
        [0x11D , "PICO_CAPTURING_DATA", "The device is currently busy capturing data."],
        [0x11F , "PICO_NOT_SUPPORTED_BY_THIS_DEVICE", "A function has been called that is not supported by the current device variant."],
        [0x120 , "PICO_INVALID_DEVICE_RESOLUTION", "The device resolution is invalid (out of range)."],
        [0x121 , "PICO_INVALID_NUMBER_CHANNELS_FOR_RESOLUTION", "The number of channels which can be enabled is limited in 15 and 16-bit modes"],
        [0x122 , "PICO_CHANNEL_DISABLED_DUE_TO_USB_POWERED", "USB Power not sufficient to power all channels."],
        ]

