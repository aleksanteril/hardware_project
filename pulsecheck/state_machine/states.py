from .template_state import State
from .measure import Measure
import time
from lib import utility, analysis # type: ignore


##State machine states start here
class LogoState(State):
      def __enter__(self) -> object:
            self.start_time = time.ticks_ms()
            self.timeout = 2200 #ms
            self.hardware.screen.set_mode(5)
            return super().__enter__()
      
      def run(self, input: int | None) -> object:
            if time.ticks_diff(time.ticks_ms(), self.start_time) > self.timeout:
                  self.state = ConnectState()
            return self.state


class ErrorState(State):
      def __init__(self, message: list):
            self.error = ['ERROR']
            for line in message: #Compile error message
                  self.error.append(line)

      def __enter__(self) -> object:
            self.hardware.screen.items(self.error, offset=0)
            self.hardware.screen.set_mode(3)
            return State.__enter__(self)

      def run(self, input: int | None) -> object:
            if input == self.hardware.ROT_PUSH:
                  self.state = MenuState()
            return self.state


class MeasureHrState(Measure):
      def __enter__(self) -> object:
            self.hardware.screen.set_mode(0)
            self.bpm = 0
            return super().__enter__()

      def display_data(self):
            Measure.display_data(self)
            if self.PPI:
                  self.bpm = round(analysis.mean_hr(self.PPI))
            self.hardware.screen.hr_bpm(self.bpm)
            return

      def run(self, input: int | None) -> object:
            self.measure(10)
            self.display_data()
            if input == self.hardware.ROT_PUSH:
                  self.state = MenuState()
            return self.state

#Special case where init is used to get the data to be uploaded to local server history
class UploadToLocal(State):
      def __init__(self, data: dict):
            self.data = data

      def run(self, input: int | None) -> object:
            try:
                  self.hardware.online.send_local(self.data)
                  self.state = MenuState()
            except:
                  self.state = ErrorState(['Local Upload', 'Fail'])
            return self.state

#Special case where init is used to get the data to be drawn on entry
class ViewAnalysisState(State):
      def __init__(self, data: dict):
            self.data = data

      def __enter__(self) -> object:
            self.hardware.historian.write(self.data)
            data = utility.format_data(self.data)
            self.hardware.screen.items(data, offset=0)
            self.hardware.screen.set_mode(3)
            return State.__enter__(self)

      def run(self, input: int | None) -> object:
            if input == self.hardware.ROT_PUSH:
                  self.state = UploadToLocal(self.data)
            return self.state


class HrvAnalysisState(Measure):
      def __enter__(self) -> object:
            self.start_time = time.ticks_ms()
            self.timeout = 30000 #ms
            self.hardware.screen.set_mode(2)
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
            if input == self.hardware.ROT_PUSH:
                  self.state = MenuState()
            elif time.ticks_diff(time.ticks_ms(), self.start_time) > self.timeout:
                  self.hardware.adc.deinit_timer()
                  self.state = self.analysis()
            return self.state


class KubiosWaitMsgState(State):
      def __enter__(self) -> object:
            self.start_time = time.ticks_ms()
            self.timeout = 10000 #ms
            self.hardware.screen.items(['Waiting', 'for kubios'], offset=0)
            self.hardware.screen.set_mode(4)
            return super().__enter__()
      
      def parse(self, data) -> object:
            try:
                  data = utility.parse_kubios_message(data)
                  self.state = ViewAnalysisState(data)
            except: #If data is invalid or has a problem, error state
                  self.state = ErrorState(['Data could', 'not be parsed'])
            return self.state

      def run(self, input: int | None) -> object:
            data = self.hardware.online.listen_kubios()
            if data != None:
                  self.state = self.parse(data)
            elif time.ticks_diff(time.ticks_ms(), self.start_time) > self.timeout:
                  self.state = ErrorState(['Kubios not', 'reached'])
            return self.state
      

class KubiosState(Measure):
      def __enter__(self) -> object:
            self.start_time = time.ticks_ms()
            self.timeout = 30000 #ms
            self.hardware.screen.set_mode(2)
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
                  self.hardware.online.send_kubios(data)
                  self.state = KubiosWaitMsgState()
            except:
                  self.state = ErrorState(['No connection'])
            return self.state

      def run(self, input: int | None) -> object:
            self.measure(50)
            self.display_data()
            if not self.hardware.online.is_connected():
                  self.state = ErrorState(['No connection'])
            elif input == self.hardware.ROT_PUSH:
                  self.state = MenuState()
            elif time.ticks_diff(time.ticks_ms(), self.start_time) > self.timeout:
                  self.hardware.adc.deinit_timer()
                  self.state = self.process_and_send()
            return self.state

#Special case where init is used to get the file to be read
class ReadHistoryState(State):
      def __init__(self, filename: str):
            self.file = filename

      def __enter__(self) -> object:
            data = self.hardware.historian.read(self.file)
            self.data = utility.format_data(data)
            self.hardware.screen.items(self.data, offset=0)
            self.hardware.screen.set_mode(3)
            return State.__enter__(self)

      def run(self, input: int | None) -> object:
            if input == self.hardware.ROT_PUSH:
                  self.state = MenuState()
            return self.state


class HistoryState(State):
      def __enter__(self) -> object:
            self.select = 0
            self.items = self.hardware.historian.contents()
            self.items.reverse()
            self.hardware.screen.items(utility.format_filenames(self.items))
            self.hardware.screen.cursor_pos(self.select)
            self.hardware.screen.set_mode(1)
            return State.__enter__(self)

      def run(self, input: int | None) -> object:
            if not self.items:
                  self.state = ErrorState(['No History'])
            elif input == self.hardware.ROT_PUSH:
                  self.state = ReadHistoryState(self.items[self.select])
            elif input == 1 or input == -1: #Rotary
                  self.select += input
                  self.select = min(max(0, self.select), len(self.items)-1)
                  self.hardware.screen.cursor_pos(self.select)
            return self.state


class MenuState(State):
      def __enter__(self) -> object:
            self.select = 0
            self.items = ['MEASURE HR', 'HRV ANALYSIS', 'KUBIOS', 'HISTORY']
            self.states = [MeasureHrState, HrvAnalysisState, KubiosState, HistoryState]
            self.hardware.screen.items(self.items)
            self.hardware.screen.cursor_pos(self.select)
            self.hardware.screen.set_mode(1)
            if self.hardware.online.is_connected():
                  self.hardware.led1.on()
            else:
                  self.hardware.led1.off()
            return State.__enter__(self)

      def run(self, input: int | None) -> object:
            if input == self.hardware.SW0 and not self.hardware.online.is_connected():
                  self.state = ConnectState()
            elif input == self.hardware.ROT_PUSH:
                  self.state = self.states[self.select]()
            elif input == 1 or input == -1: #Rotary
                  self.select += input
                  self.select = min(max(0, self.select), len(self.items)-1)
                  self.hardware.screen.cursor_pos(self.select)
            return self.state


class ConnectState(State):
      def __enter__(self) -> object:
            self.start_time = time.ticks_ms()
            self.timeout = 15000 #ms
            self.hardware.rotary.disable() #Rotary must be disabled because online contains a sleep for 20ms, to prevent user fking up
            self.hardware.screen.items(['Connecting', 'to cosmos'], offset=0)
            self.hardware.screen.set_mode(4)
            return super().__enter__()
      
      def run(self, input: int | None) -> object:
            if self.hardware.online.connect():
                  self.state = MenuState()
            elif time.ticks_diff(time.ticks_ms(), self.start_time) > self.timeout:
                  self.state = ErrorState(['Wi-Fi not found'])
            return self.state
      
      def __exit__(self, exc_type, exc_value, traceback):
            self.hardware.rotary.enable() #Enable rotary upon exit
            return
