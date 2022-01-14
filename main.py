#!/usr/bin/env python
#
# Copyright (c) 2020, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

# PyCom PyTrack 2 LoPy 4 WiPy 2
# May 2021 J.C. Kleijn

import config
from nanogateway import NanoGateway

print("\nSetup LORAWAN gateway\n")

if __name__ == '__main__':
    nanogw = NanoGateway(
        id=config.GATEWAY_ID,
        frequency=config.LORA_FREQUENCY,
        datarate=config.LORA_GW_DR,
        ssid=config.WIFI_SSID,
        password=config.WIFI_PASS,
        server=config.SERVER,
        port=config.PORT,
        ntp_server=config.NTP,
        ntp_period=config.NTP_PERIOD_S
        )

nanogw.start()

print("Main script\n")\

import machine
import math
import network
import os
import time
import utime
import gc
import pycom
import binascii
import config
import struct
import socket
from machine import RTC
from machine import SD
from L76GNSS import L76GNSS
from LIS2HH12 import LIS2HH12
from network import LoRa
from pycoproc_2 import Pycoproc
from CayenneLPP import CayenneLPP
from pytrack import Pytrack

fo = open("/flash/sys/lpwan.mac", "wb")
mac_write=bytes([0x70,0xB3,0xD5,0x7E,0xD0,0x04,0xA6,0xE2])
fo.write(mac_write)
fo.close()



# Initialize LoRa in LORAWAN mode.

#LoRa Cloud recovery code ENGEUGK2749MM7LWHTA4UMQF HQQ333NSHX7XTE24G4BZE24V

lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.EU868)

print("LORAWAN ID",binascii.hexlify(lora.mac()).upper().decode('utf-8'))

# Create an authentication params

dev_eui = binascii.unhexlify('70B3D57ED004900A')
app_eui = binascii.unhexlify('0000000000000000')
app_key = binascii.unhexlify('18996EAD7C46CAE435B185A06737DD86')

print("OTAA settings\n")
print("app_eui " + str(app_eui))
print("app_key " + str(app_key))
print("dev_eui " + str(dev_eui))

dev_addr = struct.unpack(">l", binascii.unhexlify('260B4B7B'))[0]
nwk_swkey = binascii.unhexlify('C463C0FE22EFCD123CBF3892BE8FF5D3')
app_swkey = binascii.unhexlify('9CF8FAA64F4DDB425BC53A4511740608')

print("\nABP settings\n")
print("dev_addr  " + str(dev_addr))
print("nwk_swkey " + str(nwk_swkey))
print("app_swkey " + str(app_swkey))

print("\n*** Init Lora\n")

# Set the 3 default channels to the same frequency (must be before sending the OTAA join request)
lora.add_channel(0, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)
lora.add_channel(1, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)
lora.add_channel(2, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=5)

#Join a network using OTAA
#lora.join(activation=LoRa.OTAA, auth=(app_eui, app_key), timeout=0)
#Join a network using ABP
lora.join(activation=LoRa.ABP, auth=(dev_addr, nwk_swkey, app_swkey))


#Wait until the module has joined the network
while not lora.has_joined():
    pycom.rgbled(0x140000)
    time.sleep(2.5)
    pycom.rgbled(0x000000)
    time.sleep(1.0)
    print('OTAA, not yet joined...')

print('Joined using ABP')
pycom.rgbled(0x001400) # red

# Create a LoRa socket
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

# Set the LoRaWAN data rate
s.setsockopt(socket.SOL_LORA, socket.SO_DR, 5)

pycom.heartbeat(False)
pycom.rgbled(0x0A0A08) # white

time.sleep(2)
gc.enable()

# Setup RTC
print('\n*** Set UTC time')
rtc = machine.RTC()
rtc.ntp_sync("pool.ntp.org")
utime.sleep_ms(750)
print('\nRTC Set from NTP to UTC:', rtc.now())
utime.timezone(7200)
print('Adjusted from UTC to AMS timezone', utime.localtime(), '\n')

# Check if I am a PyTrack
py = Pycoproc()
if py.read_product_id() != Pycoproc.USB_PID_PYTRACK:
    raise Exception('Not a Pytrack')

time.sleep(1)

# GPS fix trying
l76 = L76GNSS(py, timeout=30, buffer=512)

pybytes_enabled = False
if 'pybytes' in globals():
    if(pybytes.isconnected()):
        print('Pybytes is connected, sending signals to Pybytes/n')
        pybytes_enabled = True

# Mount micro sd card
sd = SD()
os.mount(sd, '/sd')

# Main loop

count = 1
while (count < 60):
    #while (True):
    print('Count is', count)
    print('\n*** Main loop\nPyCom PyTrack 2.0 WiPy LoPy 4.0\n')

    coord = l76.coordinates()
    f = open('/sd/gps-record.txt', 'a')
    f.write("{} - {} - {}".format(coord, rtc.now(), gc.mem_free()))
    f.write('\n')
    f.close()

    print('\n*** Sending signals to Pybytes\n')
    print("{} - {} - {}".format(coord, rtc.now(), gc.mem_free()))
    if(pybytes_enabled):
        pybytes.send_signal(1, coord)
    time.sleep(5)

    # Send data to TTN

    lpp = CayenneLPP()
    li = LIS2HH12(py)
    gnss = L76GNSS(py, timeout=120)

    s.setblocking(True)
    pycom.rgbled(0x000014) # blue

    print('\n\n*** 3-Axis Accelerometer (LIS2HH12)')
    print('Acceleration', li.acceleration())
    print('Roll', li.roll())
    print('Pitch', li.pitch())
    lpp.add_accelerometer(1, li.acceleration()[0], li.acceleration()[1], li.acceleration()[2])
    lpp.add_gryrometer(1, li.roll(), li.pitch(), 0)

    print('\n*** GPS (L76GNSS)')
    loc = gnss.coordinates()
    if loc[0] == None or loc[1] == None:
        print('No GPS fix within configured timeout :-(')
    else:
        print('Latitude', loc[0])
        print('Longitude', loc[1])
        lpp.add_gps(1, loc[0], loc[1], 0)

    print('\n*** Sending data to TTN')
    print('Sending data (uplink)...')
    s.send(bytes(lpp.get_buffer()))
    s.setblocking(False)
    data = s.recv(64)
    print('Received data (downlink)', data)
    pycom.rgbled(0x001400) # green
    print('\n*** Sleep 60 sec before returning to main loop\n')

    count = count + 1
    time.sleep(60)

machine.reset()
