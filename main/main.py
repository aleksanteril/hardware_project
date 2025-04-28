import _thread
from states import PulseCheck, core1_thread

'''Allocate memory for irq handler exceptions'''
import micropython
micropython.alloc_emergency_exception_buf(200)


'''Here is the main program of the PulseCheck, has a simple state machine hopefully :/'''
second_thread = _thread.start_new_thread(core1_thread, ())
machine_ = PulseCheck()
while True:
      machine_.execute()
