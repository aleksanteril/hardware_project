'''This file contains all the I/O hardware peripherals for the project'''
from fifo import Fifo
from machine import Pin, I2C, ADC
from ssd1306 import SSD1306_I2C
import time


class Screen(SSD1306_I2C):
      def __init__(self, da, cl):
            i2c = I2C(1, sda=Pin(da), scl=Pin(cl), freq=400000)
            self.width = 128
            self.heigth = 64
            self.hr_plot_pos(0,0)
            self.hr_bpm(0)
            self.y_old = 0
            super().__init__(self.width, self.heigth, i2c)
            
      def draw_hr(self):
            self.fill_rect(self.x, 0, 12, 32, 0)
            self.line(self.x-1, self.y_old, self.x, self.y, 1)
            self.y_old = self.y
            return

      def hr_plot_pos(self, x, y):
            self.x = x
            self.y = y
            return
      
      def hr_bpm(self, bpm):
            self.bpm = bpm
            return
      
      def draw_bpm(self):
            self.fill_rect(0, 32, 128, 32, 0)
            self.text(f"avg BPM: {self.bpm}", 0, 48, 1)
            return
            

class Isr_fifo(Fifo):
      def __init__(self, size, adc_pin):
            self.av = ADC(adc_pin)
            super().__init__(size)
      
      #Piotimer this 250hz
      def handler(self, tid):
            self.put(self.av.read_u16())
            return


class Rotary:
      def __init__(self, clock, signal, fifo):
            self.clock = Pin(clock, Pin.IN)
            self.signal = Pin(signal, Pin.IN)
            self.fifo = fifo
            self.pin_nr = signal
            self.enable()
    
    #Enable irq call function
      def enable(self):
            self.clock.irq(self.handler, Pin.IRQ_FALLING, hard = True)
            self.enabled = True
            return
    
    #Disable irq call function
      def disable(self):
            self.clock.irq(handler=None)
            self.enabled = False
            return
        
    #Toggle between irq on/off
      def toggle(self):
            if self.enabled:
                  self.disable()
            else:
                  self.enable()
            return

    #Accessed with interrupt request only! 
      def handler(self, pin):
            self.fifo.put(self.pin_nr) #To mark the next signal (pin_nr),(turn)
            if self.signal():
                  self.fifo.put(1)
            else:
                  self.fifo.put(-1)
            return
      

class Button:
    def __init__(self, id, fifo, DEBOUNCE=200):
        self.button = Pin(id, Pin.IN, Pin.PULL_UP)
        self.debounce = DEBOUNCE
        self.fifo = fifo
        self.pin_nr = id
        self.enable()
        self.tick2 = time.ticks_ms()
        self.diff = 0
    
    #For polling holding down
    def hold(self):
        return not self.button.value()
    
    #For polling a press once
    def pressed(self):
        if self.button.value():
            return False
        time.sleep_ms(50)
        return self.button.value()
    
    #Disable interrupt
    def disable(self):
        self.button.irq(handler=None)
        return
    
    #Enable interrupt
    def enable(self):
        self.button.irq(self.handler, Pin.IRQ_FALLING, hard=True)
        return
    
    #Accessed only through interrupt request!!!
    def handler(self, pin):
        if time.ticks_diff(time.ticks_ms(), self.tick2) > self.debounce:
            self.fifo.put(self.pin_nr)
        self.tick2 = time.ticks_ms()
