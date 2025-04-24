import network
import ntptime
import time
import ujson
from umqtt.simple import MQTTClient

# Connection class for WLAN and MQTT
class Online:
    _instance = None

    def new(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().new(cls)
        return cls._instance
    
    def __init__(self, SSID: str, PWD: str, IP: str):
        self.SSID = SSID
        self.PWD = PWD
        self.IP = IP
        self.connected = False
        self.local_mqtt = None
        self.kubios_mqtt = None
        self.last_kubios_msg = None # Storing the last message here
        
        # Connect to WLAN and MQTT automatically on object creation
        if self.connect_wlan():
            ntptime.host = "fi.pool.ntp.org"
            ntptime.settime()
            self.local_mqtt = self.connect_mqtt('local', 1883)
            self.kubios_mqtt = self.connect_mqtt('kubios', 21883)
            
            if self.kubios_mqtt: # If connected subscribe to correct topic early
                self.kubios_mqtt.set_callback(self._kubios_callback) # Calling the class method for callback
                self.kubios_mqtt.subscribe('kubios-response')
            
        print(time.localtime())

    def connect_wlan(self) -> bool:  # Connect to WLAN method, try 10 times.
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
    
    # 21883 is the kubios port, and 1883 is the local port for HR-data
    def connect_mqtt(self, id, port):  # Connect to MQTT
        try:
            client = MQTTClient(id, self.IP, port)
            client.connect(clean_session=True)
            print(f"MQTT connection to {port} successful!")
            self.connected = True
            return client
        except Exception as e:
            print(f"Failed to connect to MQTT: {e}")
            return None

    # Send MQTT message method
    def send_mqtt_message(self, client, topic, data: list):  # Try sending a message when method is called upon. If no connection, give error.
        if client is not None:
            try:
                client.publish(topic, data)
                print(f"Sending to MQTT: {topic} -> {data}")
            except Exception as e:
                print(f"Failed to send MQTT message: {e}")
        else:
            print("MQTT client not connected!")
            
    def is_connected(self) -> bool:
        return self.connected

    # Method for listening and awaiting a response from kubios
    def listen_kubios(self, timeout=5):
        print("Awaiting kubios response...")
        start = time.time()
        while time.time() - start < timeout:
            self.kubios_mqtt.check_msg()
            time.sleep(0.1)

    def _kubios_callback(self, topic, msg):
        print(f"[Callback] Topic: {topic.decode()}, Message: {msg.decode()}")
        try:
            self.last_kubios_msg = ujson.loads(msg)
        except Exception as e:
            print(f"Failed to parse message: {e}")
            self.last_kubios_msg = None

    # Send HRV data to kubios and receive the data message returned by kubios
    def send_kubios(self, data: dict) -> dict:
        data = ujson.dumps(data)
        self.send_mqtt_message(self.kubios_mqtt,'kubios-request', data)
        self.listen_kubios()
        return self.last_kubios_msg
    
    # Send data locally to hr-data topic
    def send_local(self, data: dict):
        data = ujson.dumps(data)
        self.send_mqtt_message(self.kubios_mqtt,'hr-data', data)

# Kubios test data
k_data = {
    "id": 787,
    "type": "RRI",
    "data": [828, 836, 852, 760, 800, 796, 856, 824, 808, 776, 724, 816, 800, 812, 812, 812, 756, 820, 812, 800],
    "analysis": { "type": "readiness"}
  }

# Local HR test data
hr_data = {
    "id": 123,
    "timestamp": 123456789,
    "mean_hr": 78
  }

# Object creation
connect = Online("KMD657_Group_1", "ykasonni123", "192.168.1.253")


response = connect.send_kubios(k_data)
print("Kubios Analysis:", response)
