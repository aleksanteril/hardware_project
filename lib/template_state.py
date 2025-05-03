'''This file contains template state of the state machine'''

ROTB = 11
ROT_PUSH = 12

#Template state class
class State:
      def __enter__(self) -> object:
            global ROTB
            global ROT_PUSH
            self.state = self
            return self

      def run(self, input: int | None):
            pass

      def __exit__(self, exc_type, exc_value, traceback):
            pass
