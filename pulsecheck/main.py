import gc, _thread
from state_machine.states import LogoState
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



#The runner
class PulseCheck:
      def __init__(self, fifo=hardware.fifo, initial_state=LogoState()):
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
