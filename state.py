from fifo import Fifo
from peripherals import Button, Rotary, Screen, Isr_fifo
from led import Led

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

#Create hardware objects
button = Button(ROT_PUSH, fifo)
button.enable_irq()
rotary = Rotary(ROTA, ROTB, fifo)
screen = Screen(OLED_DA, OLED_CLK)
led1 = Led(LED1)

class State:
      def __enter__(self):
            pass

      def doSomething(self):
            pass

      def __exit__(self, exc_type, exc_value, traceback):
            pass


class MenuState(State):
      def __enter__(self):
            global ROTB
            global ROT_PUSH
            self.state = self
            self.select = 0
            self.items = ['MEASURE HR', 'HRV ANALYSIS', 'KUBIOS', 'HISTORY']
            #self.states = [MeasureHr, HrvAnalysis, Kubios, History]
            screen.draw_menu(self.items)
            screen.draw_cursor(self.select)
            screen.show()
            return self

      def doSomething(self, input):
            #if input == ROT_PUSH:
                  #self.state = self.states[self.select]()
            if input == ROTB:
                  self.select += fifo.get()
                  self.select = min(max(0, self.select), len(self.items))
                  screen.draw_cursor(self.select)
                  screen.show()
            return self.state

      def __exit__(self, exc_type, exc_value, traceback):
            print('Exiting menu state')




class PulseCheck:
      def __init__(self, initial_state, fifo):
            self.next_state = initial_state
            self.fifo = fifo

      def execute(self):
            with self.next_state as state:
                  while self.next_state == state:
                        self.next_state = state.doSomething(fifo.get())



machine_ = PulseCheck(MenuState(), fifo)
while True:
      machine_.execute()
            







