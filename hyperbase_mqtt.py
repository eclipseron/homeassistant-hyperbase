from paho.mqtt import client
from paho.mqtt.enums import CallbackAPIVersion, MQTTProtocolVersion
from .const import LOGGER

class HyperbaseMQTT():
    mq: client.Client = client.Client(CallbackAPIVersion.VERSION2, protocol=MQTTProtocolVersion.MQTTv5)
    
    def __init__(self, host, port):
        self.host = host
        self.port = port
    
    def connectTCP(self):
        self.mq.transport = "tcp"
        self.mq.username_pw_set("hyperbase", "hyperbase")
        try:
            self.mq.connect(self.host, self.port)
            self.mq.loop_start()
        except ConnectionRefusedError as exc:
            LOGGER.error(f"Failed to connect to Hyperbase MQTT server")
            self.mq.disconnect()
    
    def connectWS(self):
        self.mq.transport = "websockets"
        self.mq.ws_set_options("/mqtt")
        self.mq.connect(self.host, self.port)
        self.mq.loop_start()
    
    @mq.connect_callback()
    def on_connect(client, userdata, connect_flags, reason_code, properties):
        LOGGER.info(f"hyperbase connected succesfully with reason code {reason_code}")
    