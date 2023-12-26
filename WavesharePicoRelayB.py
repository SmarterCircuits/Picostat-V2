import array, time
from machine import Pin,PWM,ADC
import rp2

adc = ADC(4)
pwm = PWM(Pin(6))
pwm.freq(1000)
color_red = (4,0,0)
color_orange = (2,2,0)
color_blue = (0,0,4)
color_green = (0,4,0)
color_black = (0,0,0)
duty = 0
direction = 1

@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT, autopull=True, pull_thresh=24)
def ws2812():
    T1 = 2
    T2 = 5
    T3 = 3
    wrap_target()
    label("bitloop")
    out(x, 1)               .side(0)    [T3 - 1]
    jmp(not_x, "do_zero")   .side(1)    [T1 - 1]
    jmp("bitloop")          .side(1)    [T2 - 1]
    label("do_zero")
    nop()                   .side(0)    [T2 - 1]
    wrap()

class Device(object):
    def __init__(self):
        self.sm = rp2.StateMachine(0, ws2812, freq=8_000_000, sideset_base=Pin(13))
        self.sm.active(1)

        self.switches = [
            Pin(21,Pin.OUT),
            Pin(20,Pin.OUT),
            Pin(19,Pin.OUT),
            Pin(18,Pin.OUT),
            Pin(17,Pin.OUT),
            Pin(16,Pin.OUT),
            Pin(15,Pin.OUT),
            Pin(14,Pin.OUT)
        ]
        
    def pixel_set(self, color):
        dimmer_color = (color[1] << 16) + (color[0] << 8) + color[2]
        self.sm.put(dimmer_color, 8)
     
    def wheel(self, pos):
        if pos < 0 or pos > 255:
            return (0, 0, 0)
        if pos < 85:
            return (255 - pos * 3, pos * 3, 0)
        if pos < 170:
            pos -= 85
            return (0, 255 - pos * 3,pos * 3)
        pos -= 170
        return (pos * 3, 0, 255 - pos * 3)
     
    def rainbow_cycle(self, wait):
        for j in range(256):
            self.pixel_set(self.wheel(j & 255))
            time.sleep(wait)

    def switch_set(self,n,switch): 
        if switch == 1:
            self.switches[n].high()
        else:
            self.switches[n].low()
    
    def alert_sound(self,a=256,b=255):
        global duty
        global direction
        if b > 255:
           b = 255
        for _ in range(8 * a):
           duty += direction
           if duty > b:
               duty = b
               direction = -1
           elif duty < 0:
               duty = 0
               direction = 1
           pwm.duty_u16(duty * duty)
           time.sleep(0.001)
        duty = 0
        pwm.duty_u16(0)