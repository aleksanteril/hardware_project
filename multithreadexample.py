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
            
class Isr_fifo(Fifo):
      def __init__(self, size, adc_pin):
            self.av = ADC(adc_pin)
            super().__init__(3)
      
      #Piotimer this 250hz
      def handler(self, tid):
            self.put(self.av.read_u16())
            return


#Core1 draws the values to the framebuffer and then displays on the screen
def core1_thread():
      global meas_hr_active
      while meas_hr_active:
            screen.draw_bpm()
            screen.draw_hr()
            screen.show()


def calculate_plotting_values(list):
      #Calculate scaling factor
      max_list = max(samples)
      min_list = min(samples)
      scale_fc = 32 / (max_list - min_list)
      return max_list, scale_fc

def plot_sample(sample, max_list, scale_fc):
      pos = (sample - max_list) * scale_fc * -1
      y = round(pos)
      return y

def calculate_bpm():
      if len(PPI) < 5:
            return 0
      avg_ppi = sum(PPI) / len(PPI)
      avg_bpm = round(60000 / avg_ppi)
      return avg_bpm

def accept_ppi_to_list(ppi):
      if ppi > 2000 or ppi < 250:
            return
      PPI.append(ppi)
      return

def find_ppi(edge, peak_time, prev_peak_time):
      threshold = (sum(samples) / len(samples))*1.05

      #Rising edge detected, appends to PPI list if the value is acceptable
      if samples[-1] > threshold and not edge:
            peak_time = time.ticks_ms()
            edge = True
            accept_ppi_to_list(time.ticks_diff(peak_time, prev_peak_time))
            return edge, peak_time, prev_peak_time
      
      #Falling under threshold with detection flag on, reset.
      elif samples[-1] < threshold and edge:
            prev_peak_time = peak_time
            edge = False
            return edge, peak_time, prev_peak_time
      else:
            return edge, peak_time, prev_peak_time

def read_sample_to_list():
      if adc.empty():
            return False
      samples.append(adc.get())
      return True

#Core0 does reading values, finding peaks, calculating the plotting scale, calculating avg bpm, sending those values
#To the screen object
def core0_thread(MAX_PPI_SIZE=10):
      global meas_hr_active

      #For peak find algorithm
      edge = False
      peak_time = time.ticks_ms()
      prev_peak_time = time.ticks_ms()

      #For plotting the screen
      max_list = 0
      scale_fc = 0
      sample_num = 0
      x = 0

      #Get 500 samples at start for the threshold, and also scaling
      while len(samples) < 500:
            if not read_sample_to_list():
                  continue
            sample_num += 1

      while meas_hr_active:
            #Read a sample from the fifo, continue back if no sample was read
            if not read_sample_to_list():
                  continue
            sample_num += 1
            del samples[0]

            #Find PPI values from the samples, peak times are counted in ticks, appends to PPI list if values found.
            edge, peak_time, prev_peak_time = find_ppi(edge, peak_time, prev_peak_time)
            if len(PPI) > MAX_PPI_SIZE:
                  del PPI[0]

            #When 250 samples has been read, calculate the new plotting values from previous 250 samples
            if sample_num % 250 == 0:
                  max_list, scale_fc = calculate_plotting_values(samples[:250])

            #Every 5th sample, plot the sample to the screen, calculate bpm, and write the values to screen.
            if sample_num % 5 != 0:
                  continue
            y = plot_sample(samples[-1], max_list, scale_fc)
            y = min(max(0, y), 31)
            avg_bpm = calculate_bpm()

            with lock:
                  screen.hr_plot_pos(x, y)
                  screen.hr_bpm(avg_bpm)

            #Increment the x pos, by 1
            x += 1
            if x > screen.width:
                  x = 0

    
screen = Screen(14, 15)
adc = Isr_fifo(3, 26) #Has an inbuilt fifo
''' Sample rate is 250 samples per second'''
tmr = Piotimer(mode=Piotimer.PERIODIC, freq=250, callback=adc.handler)


#For drawing and peak algorithm threshold 500 len
samples = []
#For the found ppi values
PPI = []

meas_hr_active = True
second_thread = _thread.start_new_thread(core1_thread, ())
core0_thread()
