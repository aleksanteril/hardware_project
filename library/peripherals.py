
from fifo import Fifo
from machine import Pin, I2C, ADC
from ssd1306 import SSD1306_I2C
from time import ticks_diff, ticks_ms, sleep_ms
from piotimer import Piotimer
import _thread

'''Lock for multithreading'''
lock = _thread.allocate_lock()

'''This file contains all the I/O hardware peripherals for the project and their interfaces'''
class Screen(SSD1306_I2C):
      def __init__(self, da: int, cl: int):
            i2c = I2C(1, sda=Pin(da), scl=Pin(cl), freq=400000)
            self.width = 128
            self.heigth = 64
            self.empty()
            self.mode = None
            self.hr_plot_pos(-1, 16)
            self.hr_bpm(0)
            self.empty()
            self.ppi_flag = False
            self.items_request = False
            self.cursor_pos(0)
            self.dots_str = ''
            self.y_old = 0
            super().__init__(self.width, self.heigth, i2c)
            
      def _draw_hr(self):
            self.fill_rect(self.x, 0, 12, 42, 0)
            self.line(self.x-1, self.y_old, self.x, self.y, 1)
            self.y_old = self.y
            return

      def _draw_bpm(self):
            self.fill_rect(64, 46, 64, 18, 0)
            self.text(f"avg BPM: {self.bpm}", 0, 56, 1)
            return
      
      def _draw_items(self):
            for i in range(len(self.items_)):
                  self.text(self.items_[i], self.offset, i*10, 1)
            return
      
      def _draw_cursor(self):
            self.fill_rect(0, 0, 10, 64, 0)
            self.text('>', 0, self.pos*10, 1)
            return
      
      def _draw_measure(self):
            self._draw_hr()
            if self.ppi_flag: #For drawing X when a peak detected
                  self.text('X', self.x-6, 12, 1)
                  self.ppi_flag = False
            return

      def _draw_dot_animation(self):
            self.dots_str += '.'
            if len(self.dots_str) > 4:
                  self.fill_rect(0, 46, 128, 18, 0)
                  self.dots_str = ''
            return

      '''This is a method for core1 to loop and draw correct things requested by core0 through flags'''
      def update(self):
            with lock:
                  if self.empty_request:
                        self.fill(0)
                        self.empty_request = False
                  elif self.items_request:
                        self._draw_items()
                        self.items_request = False
                  #Screen modes, 0 = active measuring, 1 = menu mode, 2 = analysis measuring, 3 = static view
                  elif self.mode == 0:
                        self._draw_measure()
                        self._draw_bpm()
                  elif self.mode == 1:
                        self._draw_cursor()
                  elif self.mode == 2:
                        self._draw_measure()
                        self._draw_dot_animation()
                        self.text(f'Analysing {self.dots_str}', 0, 56, 1)
                  elif self.mode == 3:
                        pass
            #Buggy shit, use this to keep from crashing still :(
            try:
                  self.show()
            except:
                  print('Core 1 something happened')
            return
                  

      '''These methods under here are used as a interface for core0 communicating to core1 to draw things'''
      def hr_plot_pos(self, x: int, y: int):
            with lock:
                  self.x = x
                  self.y = y
            return
      
      def hr_bpm(self, bpm: int):
            with lock:  
                  self.bpm = bpm
            return
      
      def cursor_pos(self, pos: int):
            with lock:
                  self.pos = pos
            return
      
      def items(self, items_: list, offset: int = 10):
            with lock:
                  self.items_ = items_
                  self.offset = offset
                  self.items_request = True
            return
      
      def empty(self):
            with lock:
                  self.empty_request = True
            return
      
      def ppi(self):
            with lock:
                  self.ppi_flag = True
            return
      
      
      #Screen modes, 0 = measuring, 1 = menu mode, 2 = static view
      def set_mode(self, mode: int):
            if mode < 0 or mode > 3:
                  raise ValueError('Screen mode not correct, 0 = Measuring, 1 = Menu, 2 = Analysis view, 3 = Static view')
            self.empty()
            with lock:
                  self.mode = mode
            return

            
class Isr_fifo(Fifo):
      def __init__(self, size: int, adc_pin: int):
            self.av = ADC(adc_pin)
            super().__init__(size)
      
      def init_timer(self, hz=250):
            self.tmr = Piotimer(mode=Piotimer.PERIODIC, freq=hz, callback=self._handler)
            return

      def deinit_timer(self):
            self.tmr.deinit()
            return

      #Triggered only by the piotimer irq
      def _handler(self, tid):
            self.put(self.av.read_u16())
            return


class Rotary:
      def __init__(self, clock: int, signal: int, fifo: object):
            self.clock = Pin(clock, Pin.IN)
            self.signal = Pin(signal, Pin.IN)
            self.fifo = fifo
            self.pin_nr = signal
            self.enable()
    
      #Enable irq call function
      def enable(self):
            self.clock.irq(self._handler, Pin.IRQ_FALLING, hard=True)
            return
    
      #Disable irq call function
      def disable(self):
            self.clock.irq(handler=None)
            return

      #Accessed with interrupt request only! 
      def _handler(self, pin):
            self.fifo.put(self.pin_nr) #To mark the next signal (pin_nr),(turn)
            if self.signal():
                  self.fifo.put(1)
            else:
                  self.fifo.put(-1)
            return
      

class Button:
      def __init__(self, id: int, fifo: object, DEBOUNCE: int = 250):
            self.button = Pin(id, Pin.IN, Pin.PULL_UP)
            self.debounce = DEBOUNCE
            self.fifo = fifo
            self.pin_nr = id
            self.tick1, self.tick2 = 0, ticks_ms()
    
      #For polling holding down
      def hold(self):
            return not self.button.value()
    
      #For polling a press once
      def pressed(self):
            if self.button.value():
                  return False
            sleep_ms(50)
            return self.button.value()
    
      #Disable interrupt
      def disable_irq(self):
            self.button.irq(handler=None)
            return
    
      #Enable interrupt
      def enable_irq(self):
            self.button.irq(self._handler, Pin.IRQ_FALLING, hard=True)
            return
    
      #Accessed only through interrupt request!!!
      def _handler(self, pin):
            self.tick1 = ticks_ms()
            if ticks_diff(self.tick1, self.tick2) > self.debounce:
                  self.fifo.put(self.pin_nr)
            self.tick2 = self.tick1
            return
