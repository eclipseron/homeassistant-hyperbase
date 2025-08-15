from paho.mqtt.enums import CallbackAPIVersion
from homeassistant.core import HomeAssistant
from paho.mqtt import client as mqtt
import asyncio

from homeassistant.helpers.dispatcher import dispatcher_send
from .exceptions import HyperbaseMQTTConnectionError
from .const import LOGGER

MQTT_CONNECTED = "hyperbase_mqtt_connected"
MQTT_DISCONNECTED = "hyperbase_mqtt_disconnected"


class MQTT:
    """Hyperbase MQTT client connection"""
    def __init__(
        self,
        hass: HomeAssistant,
        user_id: str,
        host: str="localhost",
        port: int=1883,
    ) -> None:
        """Initialize Hyperbase MQTT client."""
        self.hass = hass
        self.host = host
        self.port = port
        self.client_id = f"hass_{user_id}"
        self.connected = False
        self._mqttc: mqtt.Client = None
        self._paho_lock = asyncio.Lock()

        self.init_client()

    def init_client(self):
        """Initialize paho client."""
        proto = mqtt.MQTTv5
        self._mqttc = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            protocol=proto,
            client_id=self.client_id
            )

        self._mqttc.on_connect = self._mqtt_on_connect
        self._mqttc.on_disconnect = self._mqtt_on_disconnect

    async def async_publish(
        self, topic: str=None, payload: mqtt.PayloadType=None, qos: int=None, retain: bool=None
    ) -> None:
        """Publish a MQTT message."""
        async with self._paho_lock:
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

    def _mqtt_on_connect(self, client, userdata, connect_flags, reason_code, properties) -> None:
        """
        Connect Callback
        
        Function called when the client connected to the broker.
        """
        LOGGER.info(f"mqtt connected | rc: {reason_code}")
        if reason_code != mqtt.CONNACK_ACCEPTED:
            return reason_code
        self.connected = True
        # dispatcher_send(self.hass, MQTT_CONNECTED)


    def _mqtt_on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        """
        Disconnect Callback
        
        Function called when the client disconnected from the broker.
        """
        LOGGER.info(f"mqtt disconnected | rc: {reason_code}")
        self.connected = False
        # self._mqttc = None
        # dispatcher_send(self.hass, MQTT_DISCONNECTED)