import network
import mip
from time import sleep
from umqtt.simple import MQTTClient

# Connection class for WLAN and MQTT
class Connection:
    '''
    eka vaihtoehto = https://www.youtube.com/watch?v=Awoh5-Yr6SE
    _instance = None

    def __init__(self):
        raise RuntimeError("this is a singleton, invoke get_instance() instead")
    @classmethod
    def get_instance(cls):
        if cls._instance==None:
            cls._instance = cls.__new__(cls)
        return cls._instance
    def log(self, ex: Exception):
        print(ex)

    def log(self,message: str):
        print(message) 
    '''

    '''
    toka vaihtoehto = https://www.geeksforgeeks.org/singleton-pattern-in-python-a-complete-guide/
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Connection, cls).__new__(cls)
    return cls.instance
  
 singleton = Connection()
 new_singleton = Connection()

 print(singleton is new_singleton)

 singleton.singl_variable = "Singleton Variable"
 print(new_singleton.singl_variable)
    '''

    '''
    kolmas vaihtoehto = chatgpt <3
 _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Singleton, cls).__new__(cls)
        return cls._instance

 # Usage
 obj1 = Singleton()
 obj2 = Singleton()
 print(obj1 is obj2)  # Will print True, as both are the same instance
    '''
    def __init__ (self, SSID, PWD, IP):
        self.SSID = SSID
        self.PWD = PWD
        self.IP = IP
    
    def connect_wlan(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.wlan.connect(self.SSID, self.PWD)
        tries = 10
        
        while not self.wlan.isconnected() and tries > 0:
            print("Connecting... ")
            sleep(1)
            tries -= 1
            if tries == 0:
                print("Connection Unsuccessful!")
                return False
        
        print("Connection successful. Pico IP:", self.wlan.ifconfig()[0])
        return True
    
    def install_mqtt(self):
        try:
            mip.install("umqtt.simple")
        except Exception as e:
            print(f"Could not install MQTT: {e}")
    
    def connect_mqtt(self):
        self.mqtt_client = MQTTClient("client_id", self.IP)
        self.mqtt_client.connect(clean_session=True)
        return self.mqtt_client
        
# Creating the connection object
connection = Connection("KMD657_Group_1", "ykasonni123", "192.168.1.253")
connected = False


# Main Program
while True:
    if not connected:
        connected = connection.connect_wlan()
        if not connected:
            break

        connection.install_mqtt()

        try:
            mqtt_client = connection.connect_mqtt()
        except Exception as e:
            print(f"Failed to connect to MQTT: {e}")
            break

        # Send MQTT message
        try:
            while True:
                topic = "pico/test"
                message = "Great job bois!!!"
                mqtt_client.publish(topic, message)
                print(f"Sending to MQTT: {topic} -> {message}")
                sleep(5)
                
        except Exception as e:
            print(f"Failed to send MQTT message: {e}")
