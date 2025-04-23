from fifo import Fifo
from peripherals import Button, Rotary, Screen, Isr_fifo
from led import Led
import time, analysis, utility, gc
from historian import History
from template_state import State
'''This file contains the state machines nodes that are running on the PulseCheck'''


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


#Core1 is used for the slow screen function, to avoid fifo getting full on core0
def core1_thread():
      while True:
            screen.update()
            gc.collect()


#Class for states with measuring functionality
class Measure(State):
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
            self.got_data = False
            #Start sample reading
            adc.init_timer(250)

      def _read_sample_to_list(self) -> bool:
            if adc.empty():
                  return False
            self.samples.append(adc.get())
            return True

      def measure(self, MAX_PPI_SIZE: int):
            if not self._read_sample_to_list():
                  return
            self.sample_num += 1
            if len(self.samples) <= 500:
                  self.got_data = True
                  return

            del self.samples[0]
            self._find_ppi()
            if len(self.PPI) > MAX_PPI_SIZE:
                  del self.PPI[0]

            if self.sample_num % 250 == 0:
                  self.max_list, self.scale_fc = utility.calculate_plotting_values(self.samples[:250])
            self.got_data = True
            return

      def accept_ppi_to_list(self, ppi: int):
            if 250 < ppi < 2000:
                  screen.ppi()
                  self.PPI.append(ppi)
            return

      def _find_ppi(self):
            threshold = (sum(self.samples) / len(self.samples))*1.025
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
      
      def display_data(self):
            if self.sample_num < 750 or self.sample_num % 5 != 0 or not self.got_data:
                  return
            self.y = utility.plot_sample(self.samples[-1], self.max_list, self.scale_fc)
            self.y = min(max(0, self.y), 41)
            screen.hr_plot_pos(self.x, self.y)
            self.x = (self.x + 1) % screen.width
            self.got_data = False
            return
      
      def __exit__(self, exc_type, exc_value, traceback):
            screen.hr_plot_pos(-1, 16) #To fix wild pixel upon re-entering measuring
            screen.hr_bpm(0)
            adc.deinit_timer()
            return


##State machine states start here
class ErrorState(State):
      def __init__(self, message):
            self.error = ['ERROR', message]

      def __enter__(self) -> object:
            screen.items(self.error, offset=0)
            screen.set_mode(3)
            return State.__enter__(self)

      def run(self, input: int | None) -> object:
            if input == ROT_PUSH:
                  self.state = MenuState()
            return self.state


class MeasureHrState(Measure):
      def __enter__(self) -> object:
            screen.set_mode(0)
            self.bpm = 0
            return super().__enter__()

      def display_data(self):
            Measure.display_data(self)
            if self.PPI:
                  self.bpm = round(analysis.mean_hr(self.PPI))
            screen.hr_bpm(self.bpm)
            return

      def run(self, input: int | None) -> object:
            self.measure(10)
            self.display_data()
            if input == ROT_PUSH:
                  self.state = MenuState()
            return self.state


#Special case where init is used to get the data to be drawn on entry
class ViewAnalysisState(State):
      def __init__(self, data: dict):
            self.data = data

      def __enter__(self) -> object:
            data = utility.format_data(self.data)
            screen.items(data, offset=0)
            screen.set_mode(3)
            return State.__enter__(self)

      def run(self, input: int | None) -> object:
            if input == ROT_PUSH:
                  self.state = MenuState()
            return self.state


class HrvAnalysisState(Measure):
      def __enter__(self) -> object:
            self.start_time = time.ticks_ms()
            self.timeout = 30000 #ms
            screen.set_mode(2)
            return super().__enter__()
      

      def run(self, input: int | None) -> object:
            self.measure(30)
            self.display_data()
            if input == ROT_PUSH:
                  self.state = MenuState()
            elif time.ticks_diff(time.ticks_ms(), self.start_time) > self.timeout:
                  adc.deinit_timer()
                  try:
                        data = analysis.full(self.PPI)
                        historian.write(data)
                        self.state = ViewAnalysisState(data)
                  except:
                        self.state = ErrorState('Bad data')
            return self.state


class KubiosState(Measure):
      def __enter__(self) -> object:
            self.start_time = time.ticks_ms()
            self.timeout = 30000 #ms
            screen.set_mode(2)
            return super().__enter__()

      def run(self, input: int | None) -> object:
            self.measure(30)
            self.display_data()
            if input == ROT_PUSH:
                  self.state = MenuState()
            elif time.ticks_diff(time.ticks_ms(), self.start_time) > self.timeout:
                  adc.deinit_timer()
                  try:
                        data = utility.format_kubios_message(self.PPI)
                        #data = send_kubios(data)
                        #historian.write(data)
                        self.state = ViewAnalysisState(data)
                        pass
                  except:
                        self.state = ErrorState('Upload failed!')
            return self.state

#Special case where init is used to get the file to be read
class ReadHistoryState(State):
      def __init__(self, filename: str):
            self.file = filename

      def __enter__(self) -> object:
            data = historian.read(self.file)
            self.data = utility.format_data(data)
            screen.items(self.data, offset=0)
            screen.set_mode(3)
            return State.__enter__(self)

      def run(self, input: int | None) -> object:
            if input == ROT_PUSH:
                  self.state = MenuState()
            return self.state


class HistoryState(State):
      def __enter__(self) -> object:
            self.select = 0
            self.items = historian.contents()
            self.items.reverse()
            screen.items(utility.format_filenames(self.items))
            screen.cursor_pos(self.select)
            screen.set_mode(1)
            return State.__enter__(self)

      def run(self, input: int | None) -> object:
            if not self.items:
                  self.state = ErrorState('No History')
            elif input == ROT_PUSH:
                  self.state = ReadHistoryState(self.items[self.select])
            elif input == ROTB:
                  self.select += fifo.get()
                  self.select = min(max(0, self.select), len(self.items)-1)
                  screen.cursor_pos(self.select)
            return self.state


class MenuState(State):
      def __enter__(self) -> object:
            self.select = 0
            self.items = ['MEASURE HR', 'HRV ANALYSIS', 'KUBIOS', 'HISTORY']
            self.states = [MeasureHrState, HrvAnalysisState, KubiosState, HistoryState]
            screen.items(self.items)
            screen.cursor_pos(self.select)
            screen.set_mode(1)
            return State.__enter__(self)

      def run(self, input: int | None) -> object:
            if input == ROT_PUSH:
                  self.state = self.states[self.select]()
            elif input == ROTB:
                  self.select += fifo.get()
                  self.select = min(max(0, self.select), len(self.items)-1)
                  screen.cursor_pos(self.select)
            return self.state


#The runner
class PulseCheck:
      def __init__(self, fifo=fifo, initial_state=MenuState()):
            self.next_state = initial_state
            self.fifo = fifo

      def get_input(self) -> int | None:
            if self.fifo.empty():
                  return None
            return self.fifo.get()

      def execute(self):
            with self.next_state as current_state:
                  while self.next_state == current_state:
                        input = self.get_input()
                        self.next_state = current_state.run(input)
