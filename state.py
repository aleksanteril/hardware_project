from fifo import Fifo
from peripherals import Button, Rotary, Screen, Isr_fifo
from led import Led
import _thread, time, analysis, utility
from historian import History

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

#Create fifo for input events, signed short needed for rotary
fifo = Fifo(50, 'h')

#Create the historian for local saving
historian = History()

#Create hardware objects
button = Button(ROT_PUSH, fifo)
button.enable_irq()
rotary = Rotary(ROTA, ROTB, fifo)
screen = Screen(OLED_DA, OLED_CLK)
led1 = Led(LED1)
adc = Isr_fifo(10, ADC)

#Lock for multicore writing
lock = _thread.allocate_lock()

#Core1 is used for the slow screen function, to avoid fifo getting full on core0
def core1_thread():
      while True:
            screen.show()


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
                  self.PPI.append(ppi)
            return

      def find_ppi(self):
            threshold = (sum(self.samples) / len(self.samples))*1.05
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
            self.x, self.y = 0, 0
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
            if input == ROT_PUSH:
                  self.state = MenuState()
            return self.state

      def __exit__(self, exc_type, exc_value, traceback):
            adc.deinit_timer()
            return


class HrvAnalysisState(State, Measure):
      def __enter__(self):
            return State.__enter__(self)

      def run(self, input):
            print('Hrv analysis state')
            return MenuState()

      def __exit__(self, exc_type, exc_value, traceback):
            adc.deinit_timer()
            pass


class KubiosState(State, Measure):
      def __enter__(self):
            return State.__enter__(self)

      def run(self, input):
            print('Kubios analysis state')
            return MenuState()

      def __exit__(self, exc_type, exc_value, traceback):
            adc.deinit_timer()
            pass

#Special case where init is used to get the file to be read
class ReadHistoryState(State):
      def __init__(self, filename):
            self.file = filename

      def __enter__(self):
            data = historian.read(self.file)
            data = utility.format_data(data)
            screen.draw_items(data, offset=0)
            return State.__enter__(self)

      def run(self, input):
            if input == ROT_PUSH:
                  self.state = MenuState()
            return self.state


class HistoryState(State):
      def __enter__(self):
            self.select = 0
            self.items = historian.contents()
            screen.draw_items(utility.format_filenames(self.items))
            screen.draw_cursor(self.select)
            return State.__enter__(self)

      def run(self, input):
            if input == ROT_PUSH:
                  self.state = ReadHistoryState(self.items[self.select])
            elif input == ROTB:
                  self.select += fifo.get()
                  self.select = min(max(0, self.select), len(self.items)-1)
                  screen.draw_cursor(self.select)
            return self.state


class MenuState(State):
      def __enter__(self):
            self.select = 0
            self.items = ['MEASURE HR', 'HRV ANALYSIS', 'KUBIOS', 'HISTORY']
            self.states = [MeasureHrState, HrvAnalysisState, KubiosState, HistoryState]
            screen.draw_items(self.items)
            screen.draw_cursor(self.select)
            return State.__enter__(self)

      def run(self, input):
            if input == ROT_PUSH:
                  self.state = self.states[self.select]()
            elif input == ROTB:
                  self.select += fifo.get()
                  self.select = min(max(0, self.select), len(self.items)-1)
                  screen.draw_cursor(self.select)
            return self.state


#The runner
class PulseCheck:
      def __init__(self, initial_state, fifo):
            self.next_state = initial_state
            self.fifo = fifo


      def execute(self):
            with self.next_state as current_state:
                  while self.next_state == current_state:
                        if fifo.empty():
                              input = None
                        else:
                              input = fifo.get()
                        self.next_state = current_state.run(input)



second_thread = _thread.start_new_thread(core1_thread, ())
machine_ = PulseCheck(MenuState(), fifo)
while True:
      machine_.execute()
