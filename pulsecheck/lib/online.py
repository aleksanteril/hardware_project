import network
import ntptime
from time import sleep_ms
import ujson
from utility import set_timezone
from umqtt.simple import MQTTClient

'''This file contains the Online object, no sleeps or loops are used to keep the state machine running'''

'''Connection is established through
    polling the connect method
    online.connect()
                    '''

'''When sending kubios message, response must be polled
    throught the use of listen_kubios method

    online.send_kubios(data)
    online.listen_kubios()
                            '''

class Online:
    _instance = None

    def new(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().new(cls)
        return cls._instance
    
    def __init__(self, SSID: str, PWD: str, IP: str, TOPIC: str, PORT: str):
        self.SSID = SSID
        self.PWD = PWD
        self.IP = IP
        self.TOPIC = TOPIC
        self.PORT = int(PORT)
        self.connected = False
        self.received = False
        self.local_mqtt = None
        self.docker_mqtt = None
        self.kubios_msg = None # Storing the last message here
        
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.wlan.connect(self.SSID, self.PWD)
        
    
    def connect(self) -> bool:
        if not self.wlan.isconnected():
            sleep_ms(50) #Must sleep to await response
            return False
        
        #Time server
        try:
            ntptime.host = "fi.pool.ntp.org"
            ntptime.settime()
            set_timezone(3)
        except:
            print('Time server not reached, time not in sync')
        
        #Disconnect in case of re-connect press when connection was lost mid machine running
        try:
            self.local_mqtt.disconnect()
            self.docker_mqtt.disconnect()
        except:
            print('MQTT connections already disconnected')


        #MQTT Establish
        self.local_mqtt = self._connect_mqtt('local', self.PORT)
        self.docker_mqtt = self._connect_mqtt('kubios', 21883)
        if self.docker_mqtt: # If connected subscribe to correct topic early
            self.docker_mqtt.set_callback(self._kubios_callback) # Calling the class method for callback
            self.docker_mqtt.subscribe('kubios-response')
            
        self.connected = True
        return True
        
        
    # 21883 is the kubios port, and 1883 is the local port for HR-data
    def _connect_mqtt(self, id: str, port: int) -> object | None:  # Connect to MQTT
        try:
            client = MQTTClient(id, self.IP, port)
            client.connect(clean_session=True)
            print(f"MQTT connection to {port} successful!")
            return client
        except Exception as e:
            raise Exception(f"Failed to connect to MQTT: {e}")

    # Send MQTT message method
    def send_mqtt_message(self, client: object | None, topic: str, data: list):  # Try sending a message when method is called upon. If no connection, give error.
        if client is None:
            raise Exception("MQTT client not connected!")
        try:
            client.publish(topic, data)
        except Exception as e:
            self.connected = False
            raise Exception(f"Failed to send MQTT message: {e}")
    
    #*TODO* This method needs to ping and confirm that connection is ok *TODO*
    def is_connected(self) -> bool:
        return self.connected

    # Method for listening and awaiting a response from kubios
    def listen_kubios(self) -> dict | None:
        try: #To avoid crash if MQTT broker was down and came up again!
            self.docker_mqtt.check_msg()
        except:
            self.connected = False
            return None
        if not self.received:
            return None
        self.received = False
        return self.kubios_msg

    def _kubios_callback(self, topic, msg):
        self.received = True
        try:
            self.kubios_msg = ujson.loads(msg)
        except Exception as e:
            self.kubios_msg = None
            raise Exception(f"Failed to parse message: {e}")
        return

    # Send HRV data to kubios and receive the data message returned by kubios
    def send_kubios(self, data: dict) -> dict:
        data = ujson.dumps(data)
        self.send_mqtt_message(self.docker_mqtt, 'kubios-request', data)
        return
    
    # Send data locally to hr-data topic
    def send_local(self, data: dict):
        data = ujson.dumps(data)
        self.send_mqtt_message(self.local_mqtt, self.TOPIC, data)
        self.send_mqtt_message(self.docker_mqtt, 'hr-data', data)
        return
