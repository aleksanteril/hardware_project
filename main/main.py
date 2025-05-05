import time, gc, _thread
from lib import analysis, utility
from lib.template_state import State
from hardware import HardwareConfig
'''This file contains the state machine that is running on the PulseCheck'''

'''Allocate memory for irq handler exceptions'''
import micropython
micropython.alloc_emergency_exception_buf(200)

'''Init the hardware objects'''
hardware = HardwareConfig()


#Core1 is used for the slow screen function, to avoid fifo getting full on core0
def core1_thread():
      while True:
            hardware.screen.update()
            gc.collect()


#Class for states with measuring functionality
class Measure(State):
      def __init__(self):
            #For peak find algorithm
            self.edge = False
            self.peak_time = time.ticks_ms()
            self.prev_peak_time = time.ticks_ms()
            self.MARGIN = 1
            #For plotting the screen
            self.max_list, self.scale_fc, self.sample_num = 0, 0, 0
            #Samples: for drawing and threshold calculating
            self.samples, self.PPI = [], []
            self.x, self.y = 0, 0
            self.got_data = False
            #Start sample reading
            hardware.adc.init_timer(250)

      def _read_sample_to_list(self) -> bool:
            if hardware.adc.empty():
                  return False
            self.samples.append(hardware.adc.get())
            return True

      def measure(self, MAX_PPI_SIZE: int):
            if not self._read_sample_to_list():
                  return
            self.sample_num += 1
            if len(self.samples) < 500:
                  self.got_data = True
                  return

            self._find_ppi()

            del self.samples[0]
            if len(self.PPI) > MAX_PPI_SIZE:
                  del self.PPI[0]

            if self.sample_num % 250 == 0:
                  self.max_list, self.scale_fc = utility.calculate_plotting_values(self.samples[:250])
            self.got_data = True
            return

      def accept_ppi_to_list(self, ppi: int):
            if 250 < ppi < 2000:
                  hardware.screen.ppi()
                  self.PPI.append(ppi)
            return

      def _find_ppi(self):
            threshold = (sum(self.samples) / len(self.samples))*1.02*self.MARGIN
            sample = self.samples[-1]

            #Rising edge detected, appends to PPI list if the value is acceptable
            if sample > threshold and not self.edge:
                  self.peak_time = time.ticks_ms()
                  self.edge = True
                  self.accept_ppi_to_list(time.ticks_diff(self.peak_time, self.prev_peak_time))
                  self.MARGIN = 0.97
                  return
            
            #Falling under threshold with detection flag on, reset.
            elif sample < threshold and self.edge:
                  self.prev_peak_time = self.peak_time
                  self.edge = False
                  self.MARGIN = 1
            return
      
      def display_data(self):
            if self.sample_num < 500 or self.sample_num % 5 != 0 or not self.got_data:
                  return
            self.y = utility.plot_sample(self.samples[-1], self.max_list, self.scale_fc)
            self.y = min(max(0, self.y), 41)
            hardware.screen.hr_plot_pos(self.x, self.y)
            self.x = (self.x + 1) % hardware.screen.width
            self.got_data = False
            return
      
      def __exit__(self, exc_type, exc_value, traceback):
            hardware.screen.hr_plot_pos(-1, 16) #To fix wild pixel upon re-entering measuring
            hardware.screen.hr_bpm(0)
            hardware.adc.deinit_timer()
            return


##State machine states start here
class ErrorState(State):
      def __init__(self, message: list):
            self.error = ['ERROR']
            for line in message: #Compile error message
                  self.error.append(line)

      def __enter__(self) -> object:
            hardware.screen.items(self.error, offset=0)
            hardware.screen.set_mode(3)
            return State.__enter__(self)

      def run(self, input: int | None) -> object:
            if input == hardware.ROT_PUSH:
                  self.state = MenuState()
            return self.state


class MeasureHrState(Measure):
      def __enter__(self) -> object:
            hardware.screen.set_mode(0)
            self.bpm = 0
            return super().__enter__()

      def display_data(self):
            Measure.display_data(self)
            if self.PPI:
                  self.bpm = round(analysis.mean_hr(self.PPI))
            hardware.screen.hr_bpm(self.bpm)
            return

      def run(self, input: int | None) -> object:
            self.measure(10)
            self.display_data()
            if input == hardware.ROT_PUSH:
                  self.state = MenuState()
            return self.state

#Special case where init is used to get the data to be uploaded to local server history
class UploadToLocal(State):
      def __init__(self, data: dict):
            self.data = data

      def run(self, input: int | None) -> object:
            try:
                  hardware.online.send_local(self.data)
                  self.state = MenuState()
            except:
                  self.state = ErrorState(['Local Upload', 'Fail'])
            return self.state

#Special case where init is used to get the data to be drawn on entry
class ViewAnalysisState(State):
      def __init__(self, data: dict):
            self.data = data

      def __enter__(self) -> object:
            hardware.historian.write(self.data)
            data = utility.format_data(self.data)
            hardware.screen.items(data, offset=0)
            hardware.screen.set_mode(3)
            return State.__enter__(self)

      def run(self, input: int | None) -> object:
            if input == hardware.ROT_PUSH:
                  self.state = UploadToLocal(self.data)
            return self.state


class HrvAnalysisState(Measure):
      def __enter__(self) -> object:
            self.start_time = time.ticks_ms()
            self.timeout = 30000 #ms
            hardware.screen.set_mode(2)
            return super().__enter__()
      
      def analysis(self) -> object:
            try:
                  data = analysis.full(self.PPI)
                  self.state = ViewAnalysisState(data)
            except:
                  self.state = ErrorState(['Bad Data'])
            return self.state

      def run(self, input: int | None) -> object:
            self.measure(50)
            self.display_data()
            if input == hardware.ROT_PUSH:
                  self.state = MenuState()
            elif time.ticks_diff(time.ticks_ms(), self.start_time) > self.timeout:
                  hardware.adc.deinit_timer()
                  self.state = self.analysis()
            return self.state


class KubiosWaitMsgState(State):
      def __enter__(self) -> object:
            self.start_time = time.ticks_ms()
            self.timeout = 10000 #ms
            hardware.screen.items(['Waiting', 'for kubios'], offset=0)
            hardware.screen.set_mode(4)
            return super().__enter__()
      
      def parse(self, data) -> object:
            try:
                  data = utility.parse_kubios_message(data)
                  self.state = ViewAnalysisState(data)
            except: #If data is invalid or has a problem, error state
                  self.state = ErrorState(['Data could', 'not be parsed'])
            return self.state

      def run(self, input: int | None) -> object:
            data = hardware.online.listen_kubios()
            if data != None:
                  self.state = self.parse(data)
            elif time.ticks_diff(time.ticks_ms(), self.start_time) > self.timeout:
                  self.state = ErrorState(['Kubios not', 'reached'])
            return self.state
      

class KubiosState(Measure):
      def __enter__(self) -> object:
            self.start_time = time.ticks_ms()
            self.timeout = 30000 #ms
            hardware.screen.set_mode(2)
            return super().__enter__()
      
      def process_and_send(self) -> object:
            #Preprocess data for sending
            try:
                  self.PPI = analysis.preprocess_ppi(self.PPI)
                  data = utility.format_kubios_message(self.PPI)
            except:
                  self.state = ErrorState(['Bad data'])
                  return self.state
            #Send data to kubios
            try:
                  hardware.online.send_kubios(data)
                  self.state = KubiosWaitMsgState()
            except:
                  self.state = ErrorState(['No connection'])
            return self.state

      def run(self, input: int | None) -> object:
            self.measure(50)
            self.display_data()
            if not hardware.online.is_connected():
                  self.state = ErrorState(['No connection'])
            elif input == hardware.ROT_PUSH:
                  self.state = MenuState()
            elif time.ticks_diff(time.ticks_ms(), self.start_time) > self.timeout:
                  hardware.adc.deinit_timer()
                  self.state = self.process_and_send()
            return self.state

#Special case where init is used to get the file to be read
class ReadHistoryState(State):
      def __init__(self, filename: str):
            self.file = filename

      def __enter__(self) -> object:
            data = hardware.historian.read(self.file)
            self.data = utility.format_data(data)
            hardware.screen.items(self.data, offset=0)
            hardware.screen.set_mode(3)
            return State.__enter__(self)

      def run(self, input: int | None) -> object:
            if input == hardware.ROT_PUSH:
                  self.state = MenuState()
            return self.state


class HistoryState(State):
      def __enter__(self) -> object:
            self.select = 0
            self.items = hardware.historian.contents()
            self.items.reverse()
            hardware.screen.items(utility.format_filenames(self.items))
            hardware.screen.cursor_pos(self.select)
            hardware.screen.set_mode(1)
            return State.__enter__(self)

      def run(self, input: int | None) -> object:
            if not self.items:
                  self.state = ErrorState(['No History'])
            elif input == hardware.ROT_PUSH:
                  self.state = ReadHistoryState(self.items[self.select])
            elif input == hardware.ROTB:
                  self.select += hardware.fifo.get()
                  self.select = min(max(0, self.select), len(self.items)-1)
                  hardware.screen.cursor_pos(self.select)
            return self.state


class MenuState(State):
      def __enter__(self) -> object:
            self.select = 0
            self.items = ['MEASURE HR', 'HRV ANALYSIS', 'KUBIOS', 'HISTORY']
            self.states = [MeasureHrState, HrvAnalysisState, KubiosState, HistoryState]
            hardware.screen.items(self.items)
            hardware.screen.cursor_pos(self.select)
            hardware.screen.set_mode(1)
            if hardware.online.is_connected():
                  hardware.led1.on()
            else:
                  hardware.led1.off()
            return State.__enter__(self)

      def run(self, input: int | None) -> object:
            if input == hardware.SW0 and not hardware.online.is_connected():
                  self.state = ConnectState()
            elif input == hardware.ROT_PUSH:
                  self.state = self.states[self.select]()
            elif input == hardware.ROTB:
                  self.select += hardware.fifo.get()
                  self.select = min(max(0, self.select), len(self.items)-1)
                  hardware.screen.cursor_pos(self.select)
            return self.state


class ConnectState(State):
      def __enter__(self) -> object:
            self.start_time = time.ticks_ms()
            self.timeout = 15000 #ms
            hardware.rotary.disable() #Rotary must be disabled because online contains a sleep for 20ms, to prevent user fking up
            hardware.screen.items(['Connecting', 'to cosmos'], offset=0)
            hardware.screen.set_mode(4)
            return super().__enter__()
      
      def run(self, input: int | None) -> object:
            if hardware.online.connect():
                  self.state = MenuState()
            elif time.ticks_diff(time.ticks_ms(), self.start_time) > self.timeout:
                  self.state = ErrorState(['Wi-Fi not found'])
            return self.state
      
      def __exit__(self, exc_type, exc_value, traceback):
            hardware.rotary.enable() #Enable rotary upon exit
            return


#The runner
class PulseCheck:
      def __init__(self, fifo=hardware.fifo, initial_state=ConnectState()):
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



'''Here is the main program of the PulseCheck, has a simple state machine hopefully :/'''
second_thread = _thread.start_new_thread(core1_thread, ())
machine_ = PulseCheck()
while True:
      machine_.execute()
