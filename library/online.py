import network
import ntptime
import time
from umqtt.simple import MQTTClient

# Connection class for WLAN and MQTT
class Online:
    _instance = None

    def new(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().new(cls)
        return cls._instance
    
    def __init__(self, SSID, PWD, IP):
        self.SSID = SSID
        self.PWD = PWD
        self.IP = IP
        self.connected = False
        self.mqtt_client = None
        
        # Connect to WLAN and MQTT automatically on object creation
        if self.connect_wlan():
            ntptime.host = "fi.pool.ntp.org"
            ntptime.settime()
            self.connect_mqtt()
        print(time.localtime())

    def connect_wlan(self):  # Connect to WLAN method, try 10 times.
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.wlan.connect(self.SSID, self.PWD)
        tries = 10
        
        while not self.wlan.isconnected() and tries > 0:
            print("Connecting to WLAN... ")
            time.sleep(1)
            tries -= 1
            if tries == 0:
                print("WLAN Connection Unsuccessful!")
                return False
        
        print("WLAN connection successful. IP:", self.wlan.ifconfig()[0])
        return True
    
    def connect_mqtt(self):  # Connect to MQTT
        try:
            self.mqtt_client = MQTTClient("client_id", self.IP)
            self.mqtt_client.connect(clean_session=True)
            print("MQTT connection successful!")
            self.connected = True
        except Exception as e:
            print(f"Failed to connect to MQTT: {e}")
            self.mqtt_client = None

    def send_mqtt_message(self, topic, message):  # Try sending a message when method is called upon. If no connection, give error.
        if self.mqtt_client is not None:
            try:
                self.mqtt_client.publish(topic, message)
                print(f"Sending to MQTT: {topic} -> {message}")
            except Exception as e:
                print(f"Failed to send MQTT message: {e}")
        else:
            print("MQTT client not connected!")
            
    def is_connected(self):
        return self.connected

connect = Online("KMD657_Group_1", "ykasonni123", "192.168.1.253")