from peripherals import Button, Rotary, Screen, Isr_fifo
import time, analysis, utility, _thread

#Pin declarations
ROTA = 10
ROTB = 11
ROT_PUSH = 12
OLED_DA = 14
OLED_CLK = 15
LED1 = 22
LED2 = 21
LED3 = 20
ADC = 26

screen = Screen(OLED_DA, OLED_CLK)
adc = Isr_fifo(10, ADC)

#Core1 is used for the slow screen function, to avoid fifo getting full on core0
def core1_thread():
      while True:
            screen.show()

#Template state class
class State:
      def __enter__(self):
            global ROTB
            global ROT_PUSH
            self.state = self
            return self

      def run(self):
            pass

      def __exit__(self, exc_type, exc_value, traceback):
            pass

#Class for states with measuring functionality
class Measure:
      def __init__(self):
            #For peak find algorithm
            self.edge = False
            self.peak_time = time.ticks_ms()
            self.prev_peak_time = time.ticks_ms()
            #For plotting the screen
            self.max_list, self.scale_fc, self.sample_num = 0, 0, 0
            #Samples: for drawing and threshold calculating
            self.samples, self.PPI = [], []
            self.x, self.y = 0, 0
            #Start sample reading
            adc.init_timer(250)

      def read_sample_to_list(self) -> bool:
            if adc.empty():
                  return False
            self.samples.append(adc.get())
            return True

      def measure(self, MAX_PPI_SIZE):
            if not self.read_sample_to_list():
                  return
            self.sample_num += 1
            if len(self.samples) < 500:
                  return

            if len(self.samples) > 500:
                  del self.samples[0]

            self.find_ppi()
            if len(self.PPI) > MAX_PPI_SIZE:
                  del self.PPI[0]

            if self.sample_num % 250 == 0:
                  self.max_list, self.scale_fc = utility.calculate_plotting_values(self.samples[:250])
            return

      def accept_ppi_to_list(self, ppi: int):
            if 250 < ppi < 2000:
                  screen.text('X', self.x, 12, 1)
                  self.PPI.append(ppi)
            return

      def find_ppi(self):
            threshold = (sum(self.samples) / len(self.samples))*1.02
            sample = self.samples[-1]

            #Rising edge detected, appends to PPI list if the value is acceptable
            if sample > threshold and not self.edge:
                  self.peak_time = time.ticks_ms()
                  self.edge = True
                  self.accept_ppi_to_list(time.ticks_diff(self.peak_time, self.prev_peak_time))
                  return
            
            #Falling under threshold with detection flag on, reset.
            elif sample < threshold and self.edge:
                  self.prev_peak_time = self.peak_time
                  self.edge = False
                  return
            return


##State machine states start here
class MeasureHrState(State, Measure):
      def __enter__(self):
            screen.fill(0)
            self.bpm = 0
            return State.__enter__(self)

      def display_data(self):
            self.y = utility.plot_sample(self.samples[-1], self.max_list, self.scale_fc)
            self.y = min(max(0, self.y), 31)
            if self.PPI:
                  self.bpm = round(analysis.mean_hr(self.PPI))
            screen.hr_plot_pos(self.x, self.y)
            screen.draw_hr()
            screen.hr_bpm(self.bpm)
            screen.draw_bpm()
            self.x = (self.x + 1) % screen.width

      def run(self, input):
            self.measure(10)
            if len(self.samples) > 250 and self.sample_num % 8 == 0:
                  self.display_data()
            #if input == ROT_PUSH:
                  #self.state = MenuState()
            return self.state

      def __exit__(self, exc_type, exc_value, traceback):
            adc.deinit_timer()
            return
      


#The runner
class PulseCheck:
      def __init__(self): #fifo=fifo, initial_state=MenuState()):
            self.next_state = MeasureHrState()
            #self.fifo = fifo

      #def get_input(self):
      #      if self.fifo.empty():
      #            return None
      #      return self.fifo.get()

      def execute(self):
            with self.next_state as current_state:
                  while self.next_state == current_state:
                        input = None #self.get_input()
                        self.next_state = current_state.run(input)


second_thread = _thread.start_new_thread(core1_thread, ())
machine_ = PulseCheck()
while True:
      machine_.execute()
