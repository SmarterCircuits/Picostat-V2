import machine
from machine import Pin
from WaveshareOLED import OLED
from WavesharePicoRelayB import Device
import dht
import time
import urequests as requests
import network
import json

use_home_assistant = True

# your Home Assistant API Key goes here if you want to use it.
api_key = ''

# Your Home Assistant states URL goes here
states_url = 'http://[YOUR HOME ASSISTANT IP HERE]:8123/api/states/'

# here you can set what your helpers are called for the low and high temperature settings
low_helper = 'input_number.heat_below'
high_helper = 'input_number.cool_above'

# put in your network information here.
ssid = ''
password = ''

color_red = (4,0,0)
color_orange = (2,2,0)
color_purple = (2,0,2)
color_cyan = (0,2,2)
color_blue = (0,0,4)
color_green = (0,4,0)
color_black = (0,0,0)

temp_f = 0
hum = 0
low = 69
high = 73
heat = False
aircon = False
aircirc = False
aircirccycles = 0
stage = 'standby'
button_delay = 0
disabled = False

pins = [2,3,4,5]

buttons = []
states = [False, False, False, False]

def display_status(oled):
    if disabled:
        return
    oled.fill(0x0000)
    oled.text(f"T:{temp_f} H:{hum}%",1,2,oled.white)
    oled.text(f"Low:{low}  High:{high}",1,12,oled.white)
    oled.text(f"Stage: {stage}",1,22,oled.white)  
    oled.show()
        
def start_heat():
    global heat
    global stage
    dev.switch_set(0,1)
    stage = 'heating'
    heat = True
        
def stop_heat():
    global heat
    global stage
    print('stop heat')
    dev.switch_set(0,0)
    stage = 'standby'
    heat = False
    
def start_aircon():
    global aircon
    global stage
    dev.switch_set(2,1)
    stage = 'cooling'
    aircon = True
    
def stop_aircon():
    global stage
    global aircon
    dev.switch_set(2,0)
    stage = 'standby'
    aircon = False

def start_aircirc():
    global aircirc
    global stage
    dev.switch_set(1,1)
    stage = 'circulating'
    aircirc = True

def stop_aircirc():
    global aircirc
    global stage
    dev.switch_set(1,0)
    stage = 'standby'
    aircirc = False

def do_cycle():
    global heat
    global aircirc
    global aircon
    global stage
    global aircirccycles
    try:
        if disabled:
            return
        
        if temp_f == 0:
            return
        need_heat = temp_f < low
        need_aircon = temp_f > high
        need_aircirc = not need_heat and not need_aircon and aircirccycles >= 360
        
        if need_heat and not heat:
            if aircon:
                stop_aircon()
                time.sleep(600)
            if aircirc:
                stop_aircirc()
                time.sleep(300)
            aircirccycles = 0
            start_heat()
            return
        
        if need_aircon and not aircon:
            if heat:
                stop_heat()
                time.sleep(600)
            if aircirc:
                stop_aircirc()
                time.sleep(300)
            aircirccycles = 0
            start_aircon()
            return
        
        if need_aircirc and not aircirc:
            if aircon:
                stop_aircon()
                time.sleep(300)
            if heat:
                stop_heat()
                time.sleep(300)
            aircirccycles = 0
            start_aircon()
            return
        
        if heat and temp_f > low + 0.5: # these should go a little over target to prevent alot of short cycles
            stop_heat()
            aircirccycles = 0
            return
        
        if aircon and temp_f < high - 0.5: # these should go a little over target to prevent alot of short cycles
            stop_aircon()
            aircirccycles = 0
            return
        
        aircirccycles = aircirccycles + 1
    except Exception as e:
        print(e)


def button_released(button):
    global button_delay
    global low
    global high
    global heat
    global aircon
    global aircirc
    global disabled
    global stage
    if button_delay > 0:
        return
    button_delay = 3
    if button == buttons[0]: # red
        low = low + 1
        high = high + 1
        display_status(oled)
    if button == buttons[1]: # blue
        low = low - 1
        high = high - 1
        display_status(oled)
    if button == buttons[2]: # black
        disabled = True
        for i in range(8):
            dev.switch_set(i,0)
        stage = 'standby'
        heat = False
        aircon = False
        aircirc = False
        oled.fill(0x0000)
        oled.text("System disabled",1,2,oled.white)
        oled.show()
    if button == buttons[3]: # white
        disabled = False
        oled.fill(0x0000)
        oled.text("System enabled",1,2,oled.white)
        oled.text("Please wait",1,12,oled.white)
        oled.show()
        
    pass

def get_from_home_assistant(helper:str):
    response = None
    try:
        response = requests.get(f"{states_url}{helper}",headers={
                "Authorization": f"Bearer {api_key}",
                "content-type": "application/json",
            })
        return response.json()['state']
    except Exception as e:
        print(e)
        if response is not None:
            print(response.json())
        return None

def check_home_assistant():
    global low
    global high
    try:
        l = get_from_home_assistant(low_helper)
        h = get_from_home_assistant(high_helper)
        # I want to make sure we have both settings before I set them so the try except can fail without setting only one
        low = l
        high = h
    except:
        pass # could probably error handle here, but what are we gonna do?

if __name__=='__main__':
    dev = Device()
    oled = OLED()
    sensor = dht.DHT22(Pin(22))
        
    oled.fill(0x0000)
    oled.show()
    
    dev.pixel_set(color_black)
    
    dev.alert_sound(32,128)
    
    if use_home_assistant:
        sta_if = network.WLAN(network.STA_IF)
        sta_if.active(True)
        sta_if.connect(ssid, password)
    
        while not sta_if.isconnected():
            time.sleep(1)
            dev.pixel_set(color_blue)
            time.sleep(0.1)
            dev.pixel_set(color_black)

        dev.pixel_set(color_green)
        networked = True
    else:
        dev.pixel_set(color_purple)
            
    for pin in pins:
        switch = machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP)
        switch.irq(trigger = machine.Pin.IRQ_RISING, handler = button_released)
        buttons.append(switch)
        states.append(0)
    
    for i in range(8):
        dev.switch_set(i,0)
    
    ticks = 0
    while True:
        if use_home_assistant:
            if networked and not sta_if.isconnected():
                networked = False
                dev.pixel_set(color_red)
                
            elif not networked and sta_if.isconnected():
                networked = True
                dev.pixel_set(color_green)
                
        if ticks > 50:
            ticks = 0
            sensor.measure() 
            temp = sensor.temperature()
            temp_f = 32 + (1.8 * temp)
            hum = sensor.humidity()
            
            if use_home_assistant:
                check_home_assistant()

            do_cycle()
            display_status(oled)
        
        
        ticks = ticks + 1
        
        if button_delay > 0:
            button_delay = button_delay - 1
        
        time.sleep(0.1)
