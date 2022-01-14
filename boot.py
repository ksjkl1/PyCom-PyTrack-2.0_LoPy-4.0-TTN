# boot.py -- run on boot-up

import os
import network
import machine
import time
import pycom
from machine import SD
from network import WLAN

from machine import UART
uart = UART(0, 115200)
os.dupterm(uart)

#pycom.bootmgr(safeboot=True)

#
# Set up WLAN
#

wlan = WLAN()

ssid     = 'TMNL-692331_EXT'
password = '46U7HUXXXXXXX'
ip       = '192.168.1.47'
net_mask = '255.255.255.0'
gateway  = '192.168.1.1'
dns      = '192.168.1.1'

pycom.heartbeat(False)
print('led on')
pycom.rgbled(0x7f0000)
time.sleep(1)

print("Configure Network")
print("")

if machine.reset_cause() != machine.SOFT_RESET:
    wlan.init(mode=WLAN.STA)
    wlan.ifconfig(config=(ip, net_mask, gateway, dns))

if not wlan.isconnected():
    wlan.connect(ssid, auth=(WLAN.WPA2, password), timeout=5000)
    while not wlan.isconnected():
        machine.idle()

time.sleep(1)
pycom.rgbled(0x007f00)

print(wlan.ifconfig())
print("")
print("PyCom5_PyTrack_2.0_LoPy_4.0")

#
# Set up server
#

server = network.Server()
server.deinit()
server.init(login=('micro','python'),timeout=600)
