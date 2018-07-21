from ctypes import c_short, byref, cdll, c_char, create_string_buffer
import time
import platform

if platform.system() == "Windows":
    from ctypes import windll

    lib = windll.LoadLibrary("ps3000a.dll")
elif platform.system() == "Linux":
    lib = cdll.LoadLibrary("libps3000a.so")


# Enumerating units
print("Enumerating units...\n\n")

count = c_short()
serials = (c_char * 100)()
serialLth = c_short()
lib.ps3000aEnumerateUnits(byref(count), byref(serials), byref(serialLth))

print("count:" + str(count))
print("serial numbers: " + str(serials[0:100]))
print("serial string length: " + str(serialLth))

# try connecting
serial_len = serialLth.value
serial_num = serials[0:serial_len]
print("\n\nAttempting to connect to" + str(serial_num) + "\n\n")
handle = c_short()
s = create_string_buffer(serial_num)

m = lib.ps3000aOpenUnit(byref(handle), byref(s))
print("Result code:" + str(m))
print("Scope handle:" + str(handle.value))

try:
    # flash led
    print("\n\nFlashing LED...\n\n")
    start = c_short(10)
    lib.ps3000aFlashLed(handle, start)
    time.sleep(5)
except:  # noqa
    print("led wouldn't flash")
    pass
# close unit
print("\n\nClosing scope...\n\n")
m = lib.ps3000aCloseUnit(handle)
if m == 0:
    print("Unit" + str(serial_num) + "shut down.")
