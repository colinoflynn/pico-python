"""
Shows a demo of use to use the enumerate devices feature.

By: Mark Harfouche

"""
from __future__ import division
from picoscope import ps6000
import time

if __name__ == "__main__":
    ps = ps6000.PS6000(connect=False)

    allSerialNumbers = ps.enumerateUnits()

    print("Found the following device serial numbers: ")
    for serial in allSerialNumbers:
        print(serial + "\n")

    # you can open devices by serial number
    serial = allSerialNumbers[0]
    ps = ps6000.PS6000(serial)

    # do stuff
    ps.flashLed(10)
    time.sleep(4.0)  # the above flash takes roughly 4 seconds

    ps.close()
