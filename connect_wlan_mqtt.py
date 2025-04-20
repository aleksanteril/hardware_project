import network
import mip
from time import sleep
from umqtt.simple import MQTTClient

# Connection class for WLAN and MQTT
class Connection:
    _instance = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
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
