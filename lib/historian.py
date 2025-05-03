import os, ujson
from time import localtime, mktime

'''This class controls the /history folder and its measurement history contents, 
You can save and read from diffrent files in the folder
The class keeps the folder to a max size. 
All the measurements saved in separate txt files as json objects
The class is a singleton'''

class History:
      _instance = None
      _dir = 'hist'

      #When creating an instance this is ran before __init__
      def __new__(cls):
            #If an instance of the class doesn't exist, create one. else return the current.
            if cls._instance is None:
                  cls._instance = super().__new__(cls)
            return cls._instance
      
      def __init__(self):
            if self._dir not in os.listdir():
                  os.mkdir(self._dir)
            return

      #Create and save a new measurement.txt file
      def write(self, data: dict):
            self._folder_manager()
            date = mktime(localtime())
            #File name is formatted: name_secondsfrom1stjan2000
            file = f'meas_{date}'
            try:
                  with open(f'./{self._dir}/{file}', 'x') as f:
                        ujson.dump(data, f)
            except OSError or FileExistsError:
                  print('File already exists')
            return

      #Read data from a chosen measurement.txt file
      def read(self, file: str) -> dict:
            try:
                  with open(f'./{self._dir}/{file}', 'r') as f:
                        data = ujson.load(f)
            except OSError:
                  print('File not found')
            except ValueError:
                  print('Can not read data')
            return data

      #Read contents of the /history folder
      def contents(self) -> list:
            return os.listdir(f'./{self._dir}')

      #Keep the size of the /history folder within limits
      def _folder_manager(self):
            files = os.listdir(f'./{self._dir}')
            if len(files) > 6:
                  files.sort()
                  os.remove(f'./{self._dir}/{files[0]}')
            return
      
      #Empty the folder
      def empty(self):
            files = os.listdir(f'./{self._dir}')
            for file in files:
                  os.remove(f'./{self._dir}/{file}')
            return
