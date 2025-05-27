from datetime import timedelta
import time
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval
from .mqtt import MQTT
from .const import (
    LOGGER,
    MQTT_CONNECTED,
    MQTT_DISCONNECTED,
)
from .exceptions import HyperbaseMQTTConnectionError

class HyperbaseCoordinator:
    def __init__(
        self,
        hass: HomeAssistant,
        hyperbase_mqtt_host: str,
        hyperbase_mqtt_port: int,
        hyperbase_mqtt_topic: str,
        hyperbase_project_name: str,
        server_stats: bool | None = False,
    ):
        """Initialize."""
        self.hass = hass
        self.server_stats = server_stats
        self.devices = []
        self.on_tick_callbacks = []
        self._disconnect_callbacks = []
        self.unloading = False
        self.__mqtt_topic = hyperbase_mqtt_topic
        self.__project_name = hyperbase_project_name

        self.mqtt_client = MQTT(
            hass,
            hyperbase_mqtt_host,
            hyperbase_mqtt_port,
        )

        self._disconnect_callbacks.append(
            async_dispatcher_connect(
                self.hass, MQTT_CONNECTED, self._on_connection_change
            )
        )
        self._disconnect_callbacks.append(
            async_dispatcher_connect(
                self.hass, MQTT_DISCONNECTED, self._on_connection_change
            )
        )

    @callback
    def _on_connection_change(self, *args, **kwargs):
        pass


    async def connect(self):
        try:
            _ = await self.mqtt_client.async_connect()
        except HyperbaseMQTTConnectionError as exc:
            LOGGER.error(f"({self.__project_name}) MQTT connection failed: {exc}")
            return
        
        # add publish job only on successful connection
        LOGGER.info(f"({self.__project_name}) MQTT connection established")
        self._disconnect_callbacks.append(
            async_track_time_interval(self.hass, self.__async_publish_on_tick, timedelta(seconds=1))
        )

    async def disconnect(self):
        self.unloading = True
        await self.mqtt_client.async_disconnect()
        for cb in self._disconnect_callbacks:
            cb()


    def register_publisher(self, sensor):
        """Register new entity publisher to Hyperbase"""
        # self.register_on_tick(sensor.tick)

    def register_on_tick(self, on_tick_cb):
        self.on_tick_callbacks.append(on_tick_cb)

    @property
    def is_connected(self):
        return self.mqtt_client.connected

    async def __async_publish_on_tick(self, *args):
        await self.mqtt_client.async_publish(
            self.__mqtt_topic,
            "tick",
            qos=0,
            retain=False,
        )
