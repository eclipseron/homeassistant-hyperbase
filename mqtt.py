import logging
from homeassistant.core import HomeAssistant
from paho.mqtt import client as mqtt
import asyncio

from homeassistant.helpers.dispatcher import dispatcher_send
from .exceptions import HyperbaseMQTTConnectionError


MQTT_CONNECTED = "hyperbase_mqtt_connected"
MQTT_DISCONNECTED = "hyperbase_mqtt_disconnected"

_LOGGER = logging.getLogger(__name__)

class MQTT:
    """Hyperbase MQTT client connection"""
    def __init__(
        self,
        hass: HomeAssistant,
        host: str="localhost",
        port: int=1883,
    ) -> None:
        """Initialize Hyperbase MQTT client."""
        self.hass = hass
        self.host = host
        self.port = port
        self.connected = False
        self._mqttc: mqtt.Client = None
        self._paho_lock = asyncio.Lock()

        self.init_client()

    def init_client(self):
        """Initialize paho client."""
        proto = mqtt.MQTTv311
        self._mqttc = mqtt.Client(protocol=proto)

        self._mqttc.on_connect = self._mqtt_on_connect
        self._mqttc.on_disconnect = self._mqtt_on_disconnect

    async def async_publish(
        self, topic: str, payload: mqtt.PayloadType, qos: int, retain: bool
    ) -> None:
        """Publish a MQTT message."""
        async with self._paho_lock:
            _LOGGER.info("Transmitting message on %s: %s", topic, payload)
            await self.hass.async_add_executor_job(
                self._mqttc.publish, topic, payload, qos, retain
            )

    async def async_connect(self) -> str:
        """Initiate MQTT connection to host"""
        result: int = None
        try:
            result = await self.hass.async_add_executor_job(
                self._mqttc.connect, self.host, self.port,
            )
        except OSError as err:
            raise HyperbaseMQTTConnectionError(err)

        if result is not None and result != 0:
            raise HyperbaseMQTTConnectionError(mqtt.error_string(result))
        self._mqttc.loop_start()
        return result

    async def async_disconnect(self):
        """Disconnect from the MQTT host."""
        await self.hass.async_add_executor_job(self.__mqtt_close)
    
    
    def __mqtt_close(self):
        if self._mqttc is not None:
            self._mqttc.disconnect()
            self._mqttc.loop_stop()

    def _mqtt_on_connect(self, _mqttc, _userdata, _flags, result_code: int) -> None:
        """
        Connect Callback
        
        Function called when the client connected to the broker.
        """
        if result_code != mqtt.CONNACK_ACCEPTED:
            return
        self.connected = True
        dispatcher_send(self.hass, MQTT_CONNECTED)


    def _mqtt_on_disconnect(self, _mqttc, _userdata, result_code: int) -> None:
        """
        Disconnect Callback
        
        Function called when the client disconnected from the broker.
        """
        self.connected = False
        self._mqttc = None
        dispatcher_send(self.hass, MQTT_DISCONNECTED)