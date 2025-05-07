from .template_state import State
import time
from lib import utility # type: ignore

#Class for states with measuring functionality
class Measure(State):
      def __init__(self):
            #For peak find algorithm
            self.edge = False
            self.peak_time = time.ticks_ms()
            self.prev_peak_time = time.ticks_ms()
            self.MARGIN = 1.05
            #For plotting the screen
            self.max_list, self.scale_fc, self.sample_num = 0, 0, 0
            #Samples: for drawing and threshold calculating
            self.samples, self.PPI = [], []
            self.x, self.y = 0, 0
            self.got_data = False
            #To calculate the bpm flag
            self.peak_appended = False
            #Start sample reading
            self.hardware.adc.init_timer(250)

      def _read_sample_to_list(self) -> bool:
            if self.hardware.adc.empty():
                  return False
            self.samples.append(self.hardware.adc.get()) #O(1) op
            self.sample_num += 1
            self.got_data = True
            return True

      def measure(self, MAX_PPI_SIZE: int):
            if not self._read_sample_to_list():
                  return
            
            if self.sample_num % 250 == 0:
                  self.max_list, self.scale_fc = utility.calculate_plotting_values(self.samples[:250])
            
            if len(self.samples) < 500:
                  return

            self._find_ppi()
            del self.samples[0] #O(n) op

            if len(self.PPI) > MAX_PPI_SIZE:
                  del self.PPI[0]
            return

      def accept_ppi_to_list(self, ppi: int):
            if 250 < ppi < 2000:
                  self.hardware.screen.ppi()
                  self.PPI.append(ppi)
                  self.peak_appended = True
            return

      def _find_ppi(self):

            #             O(n) op               O(1) op
            threshold = (sum(self.samples) / len(self.samples))*1.04#self.MARGIN

            #Rolling average of 5 last
            data = self.samples[-5:]
            sample = sum(data)/len(data)

            data2 = self.samples[-10:-5]
            sample2 = sum(data2)/len(data2)

            #Rising edge detected, appends to PPI list if the value is acceptable
            if sample > threshold and sample2 - sample <= 0 and not self.edge:
                  self.peak_time = time.ticks_ms()
                  self.edge = True
                  self.accept_ppi_to_list(time.ticks_diff(self.peak_time, self.prev_peak_time))
                  #self.MARGIN = 0.97
                  return
            
            #Falling under threshold with detection flag on, reset.
            elif sample < threshold and self.edge:
                  self.prev_peak_time = self.peak_time
                  self.edge = False
                  #self.MARGIN = 1.05
            return
      
      def display_data(self):
            if self.sample_num < 500 or self.sample_num % 5 != 0 or not self.got_data:
                  return
            self.y = utility.plot_sample(self.samples[-1], self.max_list, self.scale_fc)
            self.y = min(max(0, self.y), 41)
            self.hardware.screen.hr_plot_pos(self.x, self.y)
            self.x = (self.x + 1) % self.hardware.screen.width
            self.got_data = False
            return
      
      def __exit__(self, exc_type, exc_value, traceback):
            self.hardware.screen.hr_plot_pos(-1, 16) #To fix wild pixel upon re-entering measuring
            self.hardware.screen.hr_bpm(0)
            self.hardware.adc.deinit_timer()
            return
