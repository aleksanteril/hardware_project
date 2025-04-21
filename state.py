from fifo import Fifo
from peripherals import Button, Rotary, Screen, Isr_fifo
from led import Led
import _thread, time
from historian import History
from utility import format_filenames, format_data

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

#Core1 is used for the slow screen function, to help with fifo getting full on core0
def core1_thread():
      while True:
            screen.show()


class State:
      def __enter__(self):
            pass

      def doSomething(self):
            pass

      def __exit__(self, exc_type, exc_value, traceback):
            pass


class MeasureHrState(State):
      def __enter__(self):
            return self

      def doSomething(self, input):
            print('Measure hr state')
            return MenuState()

      def __exit__(self, exc_type, exc_value, traceback):
            pass


class HrvAnalysisState(State):
      def __enter__(self):
            return self

      def doSomething(self, input):
            print('Hrv analysis state')
            return MenuState()

      def __exit__(self, exc_type, exc_value, traceback):
            pass


class KubiosState(State):
      def __enter__(self):
            return self

      def doSomething(self, input):
            print('Kubios analysis state')
            return MenuState()

      def __exit__(self, exc_type, exc_value, traceback):
            pass


#Special case where init is used to get the file to be read
class ReadHistoryState(State):
      def __init__(self, filename):
            self.file = filename

      def __enter__(self):
            global ROT_PUSH
            self.state = self
            data = historian.read(self.file)
            data = format_data(data)
            screen.draw_items(data, offset=0)
            return self

      def doSomething(self, input):
            if input == ROT_PUSH:
                  self.state = MenuState()
            return self.state

      def __exit__(self, exc_type, exc_value, traceback):
            pass


class HistoryState(State):
      def __enter__(self):
            global ROTB
            global ROT_PUSH
            self.state = self
            self.select = 0
            self.items = historian.contents()
            screen.draw_items(format_filenames(self.items))
            screen.draw_cursor(self.select)
            return self

      def doSomething(self, input):
            
            if input == ROT_PUSH:
                  self.state = ReadHistoryState(self.items[self.select])
            elif input == ROTB:
                  self.select += fifo.get()
                  self.select = min(max(0, self.select), len(self.items)-1)
                  screen.draw_cursor(self.select)
            return self.state

      def __exit__(self, exc_type, exc_value, traceback):
            pass


class MenuState(State):
      def __enter__(self):
            global ROTB
            global ROT_PUSH
            self.state = self
            self.select = 0
            self.items = ['MEASURE HR', 'HRV ANALYSIS', 'KUBIOS', 'HISTORY']
            self.states = [MeasureHrState, HrvAnalysisState, KubiosState, HistoryState]
            screen.draw_items(self.items)
            screen.draw_cursor(self.select)
            return self

      def doSomething(self, input):
            if input == ROT_PUSH:
                  self.state = self.states[self.select]()
            elif input == ROTB:
                  self.select += fifo.get()
                  self.select = min(max(0, self.select), len(self.items)-1)
                  screen.draw_cursor(self.select)
            return self.state

      def __exit__(self, exc_type, exc_value, traceback):
            print('Exiting menu state')




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
                        self.next_state = current_state.doSomething(input)



second_thread = _thread.start_new_thread(core1_thread, ())
machine_ = PulseCheck(MenuState(), fifo)
while True:
      machine_.execute()
            







