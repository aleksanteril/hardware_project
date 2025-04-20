import time, _thread
from analysis import mean_hr
from peripherals import Screen, Isr_fifo

lock = _thread.allocate_lock()

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
      return round(pos)

def accept_ppi_to_list(ppi, PPI):
      if 250 < ppi < 2000:
            PPI.append(ppi)
      return

def find_ppi(edge, peak_time, prev_peak_time):
      threshold = (sum(samples) / len(samples))*1.05
      sample = samples[-1]

      #Rising edge detected, appends to PPI list if the value is acceptable
      if sample > threshold and not edge:
            peak_time = time.ticks_ms()
            edge = True
            accept_ppi_to_list(time.ticks_diff(peak_time, prev_peak_time), PPI)
            return edge, peak_time, prev_peak_time
      
      #Falling under threshold with detection flag on, reset.
      elif sample < threshold and edge:
            prev_peak_time = peak_time
            edge = False
            return edge, peak_time, prev_peak_time
      
      return edge, peak_time, prev_peak_time

def read_sample_to_list(adc, samples):
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
      max_list, scale_fc, sample_num, x, bpm = 0, 0, 0, 0, 0

      #Get 500 samples at start for the threshold, and also scaling
      while len(samples) < 500:
            if read_sample_to_list(adc, samples):
                  sample_num += 1

      while meas_hr_active:
            #Read a sample from the fifo, continue back if no sample was read
            if not read_sample_to_list(adc, samples):
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
            if PPI:
                  bpm = round(mean_hr(PPI))

            with lock:
                  screen.hr_plot_pos(x, y)
                  screen.hr_bpm(bpm)

            #Keep x running between 0-127
            x = (x + 1) % screen.width


screen = Screen(14, 15)
adc = Isr_fifo(10, 26)
adc.init_timer(250)


#Samples: for drawing and threshold calculating
samples, PPI = [], []

meas_hr_active = True
second_thread = _thread.start_new_thread(core1_thread, ())
core0_thread()
