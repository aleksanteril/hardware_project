from fifo import Fifo
from peripherals import Button, Rotary, Screen, Isr_fifo
from led import Led
import utility
from historian import History
from online import Online
'''This file contains the hardware object and the initizaliati'''

class HardwareConfig:
      _instance = None
      _initted = False

      def __new__(cls):
            if cls._instance is None:
                  cls._instance = super().__new__(cls)
            return cls._instance

      def __init__(self):
            if self._initted: #Init only once if called multiple times
                  return
            self._initted = True

            #Pin declarations
            self.ROTA = 10
            self.ROTB = 11
            self.ROT_PUSH = 12
            self.OLED_DA = 14
            self.OLED_CLK = 15
            self.LED1 = 22
            self.LED2 = 21
            self.LED3 = 20
            self.ADC = 26
            self.SW0 = 7

            #Create fifo for input events, signed short needed for rotary
            self.fifo = Fifo(50, 'h')

            #Create the historian for local saving
            self.historian = History()

            #Create online communications object
            settings = utility.read_wifi_file()
            self.online = Online(settings['SSID'], settings['PASSWORD'], settings['MQTTBROKER'], settings['TOPIC'], settings['PORT'])

            #Create hardware objects
            self.switch = Button(self.SW0, self.fifo)
            self.button = Button(self.ROT_PUSH, self.fifo)
            self.rotary = Rotary(self.ROTA, self.ROTB, self.fifo)
            self.screen = Screen(self.OLED_DA, self.OLED_CLK)
            self.led1 = Led(self.LED1)
            self.adc = Isr_fifo(10, self.ADC)
