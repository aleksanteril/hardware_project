import os, json
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
      def write(self, file, data):
            self._folder_manager()
            date = mktime(localtime())
            #File name is formatted: name_secondsfrom1stjan2000
            file = f'{file}_{date}'
            with open(f'./{self._dir}/{file}', 'w') as f:
                  json.dump(data, f, (',', ':'))
            return

      #Read data from a chosen measurement.txt file
      def read(self, file):
            with open(f'./{self._dir}/{file}', 'r') as f:
                  data = json.load(f)
            return data


      #Read contents of the /history folder
      def contents(self):
            return os.listdir(f'./{self._dir}')

      #Keep the size of the /history folder within limits
      def _folder_manager(self):
            files = os.listdir(f'./{self._dir}')
            if len(files) < 6:
                  return
            pass
            #Code here to find and delete the oldest file.

