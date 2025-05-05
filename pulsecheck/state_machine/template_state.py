from hardware import HardwareConfig
'''This file contains template state of the state machine'''

#Template state class
class State:
      
      #Used for the states to get pin num refrences, object refrences etc.
      hardware = HardwareConfig()

      def __enter__(self) -> object:
            self.state = self
            return self

      def run(self, input: int | None):
            pass

      def __exit__(self, exc_type, exc_value, traceback):
            pass
