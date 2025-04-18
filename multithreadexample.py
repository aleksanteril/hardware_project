from machine import Pin, I2C, ADC
from ssd1306 import SSD1306_I2C
from fifo import Fifo
from piotimer import Piotimer
import time, _thread

lock = _thread.allocate_lock()

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
            
class Isr_adc:
      def __init__(self, adc_pin, fifo):
            self.av = ADC(adc_pin)
            self.fifo = fifo
      
      #Piotimer this 250hz
      def handler(self, tid):
            self.fifo.put(self.av.read_u16())
            return


#Core1 refreshes the screen for drawing, and draws framebuffer
def core1_thread():
      global measuring
      while measuring:
            screen.draw_bpm()
            screen.draw_hr()
            screen.show()


def calculate_scale_factor(list):
      #Calculate scaling factor
      max_list = max(samples)
      min_list = min(samples)
      scale_fc = 32 / (max_list - min_list)
      return max_list, scale_fc

def scale(sample, max_list, scale_fc):
      pos = (sample - max_list) * scale_fc * -1
      y = round(pos)
      return y

def calculate_bpm():
      if len(PPI) < 5:
            return '--'
      #Avg bpm calculation
      avg_ppi = sum(PPI) / len(PPI)
      avg_bpm = 60000 / avg_ppi
      return round(avg_bpm)

def ppi_filter(ppi):
      if ppi > 2000 or ppi < 250:
            return
      PPI.append(ppi)
      if len(PPI) > 10:
            del PPI[0]
      return

def find_ppi(edge, peak_time, prev_peak_time):
      threshold = (sum(samples) / len(samples))*1.05
      #Rising edge detected
      if samples[-1] > threshold and not edge:
            peak_time = time.ticks_ms()
            ppi_filter(time.ticks_diff(peak_time, prev_peak_time))
            edge = True
            return edge, peak_time, prev_peak_time
      #If under threshold and new rise was detected, do calculations and reset
      elif samples[-1] < threshold and edge:
            prev_peak_time = peak_time
            edge = False
            return edge, peak_time, prev_peak_time
      else:
            return edge, peak_time, prev_peak_time

#Core0 does reading values, finding peaks, calculating the plotting scale, calculating avg bpm
def core0_thread():
      global measuring

      #For peak find algorithm
      edge = False
      peak_time = time.ticks_ms()
      prev_peak_time = time.ticks_ms()

      #For plotting the screen
      max_list = 0
      scale_fc = 0
      sample_num = 0
      x = 0

      #Get 500 samples for the threshold, and also scaling
      while len(samples) < 500:
            if data.empty():
                  continue
            samples.append(data.get())
            sample_num += 1

      while measuring:
            #Take interval amount of samples, replace old samples to keep the list between 250.
            if data.empty():
                  continue
            sample = data.get()
            sample_num += 1

            #When 250 samples has been read, calculate the new scale factor to draw with the old 250
            if sample_num % 250 == 0:
                  #gc.collect()
                  max_list, scale_fc = calculate_scale_factor(samples[:250])

            del samples[0]
            samples.append(sample)

            edge, peak_time, prev_peak_time = find_ppi(edge, peak_time, prev_peak_time)

            if sample_num % 5 != 0:
                  continue
            #Calculate and draw every 5th sample and scale to plot
            calc_y = scale(sample, max_list, scale_fc)
            calc_y = min(max(0, calc_y), 31) #Limit y between screen
            avg_bpm = calculate_bpm()

            with lock:
                  screen.hr_plot_pos(x, calc_y)
                  screen.hr_bpm(avg_bpm)

            x += 1
            if x > screen.width:
                  x = 0

    
data = Fifo(30)
screen = Screen(14, 15)
adc = Isr_adc(26, data)

''' Sample rate is 250 samples per second'''
tmr = Piotimer(mode=Piotimer.PERIODIC, freq=250, callback=adc.handler)


#For drawing and peak algorithm threshold 500 len
samples = []
#For the found ppi values, max len 10
PPI = []

measuring = True
second_thread = _thread.start_new_thread(core1_thread, ())
core0_thread()
