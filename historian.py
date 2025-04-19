
'''This class controls the /history folder and its measurement history contents, 
You can save and read from diffrent files in the folder
The class keeps the folder to a max size. 
All the measurements saved in separate txt files as json objects
The class is also a singleton'''

class History:
      _instance = None

      #When creating an instance this is ran before __init__
      def __new__(cls):
            #If an instance of the class doesn't exist, create one. else return the current.
            if cls._instance is None:
                  cls._instance = super().__new__(cls)
            return cls._instance
      
      def __init__(self):
            pass

      #Create and save a new measurement.txt file
      def write(self):
            pass

      #Read data from a chosen measurement.txt file
      def read(self):
            pass

      #Read contents of the /history folder
      def contents(self):
            pass

      #Keep the size of the /history folder within limits
      #This method is used when saving a new, to check if a old one needs to be deleted
      def _folder_manager(self):
            pass
