from machine import Pin, I2C, ADC
from ssd1306 import SSD1306_I2C
import _thread
from fifo import Fifo
from piotimer import Piotimer

class Screen(SSD1306_I2C):
      def __init__(self, da, cl):
            i2c = I2C(1, sda=Pin(da), scl=Pin(cl), freq=400000)
            self.width = 128
            self.heigth = 64
            self.hr_px_coords(0,0)
            self.y_old = 0
            super().__init__(self.width, self.heigth, i2c)
            
      def draw_hr(self):
            self.fill_rect(self.x, 0, 12, 32, 0)
            self.line(self.x-1, self.y_old, self.x, self.y, 1)
            self.y_old = self.y
            return

      def hr_px_coords(self, x, y):
            self.x = x
            self.y = y
            return
      
      def draw_bpm(self, bpm):
            self.fill_rect(0, 32, 128, 32, 0)
            self.text(f"AVG BPM: {bpm:.0f}", 0, 48, 1)
            return
            
class Isr_adc:
      def __init__(self, adc_pin, fifo):
            self.av = ADC(adc_pin)
            self.fifo = fifo
      
      #Piotimer this 250hz
      def handler(self, tid):
            self.fifo.put(self.av.read_u16())
            return

#Core1 refreshes the screen for drawing
def core1_thread():
      while True:
            screen.show()



def calculate_scale_factor(list):
      #Calculate scaling factor
      max_list = max(samples)
      min_list = min(samples)
      scale_fc = (32) / (max_list - min_list)
      return max_list, min_list, scale_fc

def scale(sample, max_list, scale_fc):
      pos = abs((sample - max_list) * scale_fc)
      calc_y = int(round(pos))
      return calc_y

def calculate_ppi(peak_a, peak_b):
      #Calculate interval and conversion to milliseconds
      ppi = (peak_a - peak_b)*4

      if ppi > 2000 or ppi < 250: #Discard if not realistic
            return
      
      PPI.append(ppi)
      if len(PPI) > 10:
            del PPI[0]

      calculate_bpm()
    
def calculate_bpm():
      global avg_bpm
      #Avg bpm calculation
      avg_ppi = sum(PPI) / len(PPI)
      avg_bpm = 60000 / avg_ppi
      return

def find_peaks():
      global sample_num
      global MARGIN
      global edge
      global current_peak
      global previous_peak

      sample_num += 1
      threshold = (sum(samples) / len(samples))*1.05*MARGIN

      #If signal under threshold and no new peak, ignore and get new sample
      if samples[-1] < threshold and not edge:
            return

      #Rising edge detected
      if samples[-1] > threshold and not edge:
            edge = True
            current_peak = sample_num
            MARGIN = 0.9
            return

      #If under threshold and new rise was detected, do calculations and reset
      if samples[-1] < threshold and edge:
            calculate_ppi(current_peak, previous_peak)
            previous_peak = current_peak
            MARGIN = 1
            edge = False
            return


def core0_thread():
      global count
      global x
      global max_list
      global min_list
      global scale_fc
      global sample_num
      global avg_bpm

      #When 250 samples has been read, calculate the new scale factor to draw with the old 250
      if sample_num % 250 == 0:
            max_list, min_list, scale_fc = calculate_scale_factor(samples[:250])

      #Take interval amount of samples, replace old samples to keep the list between 250.
      while count < 5:
            if data.empty():
                  continue
            sample = data.get()
            del samples[0]
            samples.append(sample)
            find_peaks()
            count += 1
      count = 0


      #Calculate and draw every 5th sample and scale to plot
      calc_y = scale(sample, max_list, scale_fc)
      calc_y = min(max(0, calc_y), 31) #Limit y between screen
      
      screen.hr_px_coords(x, calc_y)
      screen.draw_hr()
      screen.draw_bpm(avg_bpm)
      x += 1
      if x > screen.width:
            x = 0

    
data = Fifo(50)
screen = Screen(14, 15)
adc = Isr_adc(26, data)

''' Sample rate is 250 samples per second'''
tmr = Piotimer(mode=Piotimer.PERIODIC, freq=250, callback=adc.handler)

#For drawing the screen
max_list = 0
min_list = 0
scale_fc = 0
sample_num = 0
count = 0
x = 0
avg_bpm = 0

#For drawing and hr reading
samples = []

#For hr reading
MARGIN = 1
sample_num = 0
current_peak = 0
previous_peak = 0
edge = False
PPI = []


#Get 500 samples for the threshold, and also scaling
while len(samples) < 500:
      if data.empty():
            continue
      samples.append(data.get())
      sample_num += 1
      

second_thread = _thread.start_new_thread(core1_thread, ())
while True:
      core0_thread()
