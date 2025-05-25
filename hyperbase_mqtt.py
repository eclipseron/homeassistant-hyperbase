from paho.mqtt import client
from paho.mqtt.enums import CallbackAPIVersion, MQTTProtocolVersion
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.reasoncodes import ReasonCode
from .const import LOGGER

class HyperbaseMQTT():
    mq: client.Client = client.Client(CallbackAPIVersion.VERSION2, protocol=MQTTProtocolVersion.MQTTv5)
    
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.mq.on_connect = self.on_connect
        self.mq.on_disconnect = self.on_disconnect
    
    def pingTCP(self):
        self.mq.transport = "tcp"
        self.mq.username_pw_set("hyperbase", "hyperbase")
        try:
            self.mq.connect(self.host, self.port)
            self.mq.loop_start()
        except ConnectionRefusedError as exc:
            self.mq.disconnect(ReasonCode(packetType=PacketTypes.CONNACK, identifier=136))
            LOGGER.error(f"Failed to connect to Hyperbase MQTT server")
            return {"success": False, "code": 136, "msg": "Connection refused"}
        return {"success": True}
    
    def connectWS(self):
        self.mq.transport = "websockets"
        self.mq.ws_set_options("/mqtt")
        self.mq.connect(self.host, self.port)
        self.mq.loop_start()

    def on_connect(self, client, userdata, connect_flags, reason_code, properties):
        LOGGER.info(f"hyperbase connected succesfully with reason code {reason_code}")
        self.mq.disconnect() # ensure disconnect after connection is established
    
    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        LOGGER.info(f"hyperbase disconnected with reason code {reason_code}")