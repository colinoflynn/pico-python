

from ctypes import *
import time

lib = windll.LoadLibrary("ps3000a.dll")

# Enumerating units
print "Enumerating units...\n\n"

count = c_short()
serials = (c_char * 100)()
serialLth = c_short()
lib.ps3000aEnumerateUnits(byref(count), byref(serials), byref(serialLth))

print "count:", count
print "serial numbers: ", serials[0:100]
print "serial string length: ", serialLth

# try connecting
serial_len = serialLth.value
serial_num = serials[0:serial_len]
print "\n\nAttempting to connect to", serial_num, "\n\n"
handle = c_short()
s = create_string_buffer(serial_num)

m = lib.ps3000aOpenUnit(byref(handle), byref(s))
print "Result code:", m
print "Scope handle:", handle.value

try:
	# flash led
	print "\n\nFlashing LED...\n\n"
	start = c_short(3)
	lib.ps3000aFlashLed(handle, start)
	time.sleep(5)
except:
	print "led wouldn't flash"
	pass
# close unit
print "/n/nClosing scope.../n/n"
m = lib.ps3000aCloseUnit(handle)
if m == 0:
	print "Unit", serial_num, "shut down."