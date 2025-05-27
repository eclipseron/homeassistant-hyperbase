"""
The "hello world" custom component.

This component implements the bare minimum that a component should implement.

Configuration:

To use the hello_world component you will need to add the following to your
configuration.yaml file.

hello_world:
"""

import asyncio
import errno
import json
from typing import Optional
from paho.mqtt.enums import CallbackAPIVersion, MQTTErrorCode, MQTTProtocolVersion
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.exceptions import HomeAssistantError
from paho.mqtt import client as mqtt
from .const import CONF_MQTT_ADDRESS, CONF_MQTT_PORT, CONF_MQTT_TOPIC, DOMAIN, LOGGER

class HyperbaseMQTTConnection:
    client: mqtt.Client
    """MQTT connection for Hyperbase"""
    def __init__(self, host: str, port: int, topic: str):
        self.client = mqtt.Client(CallbackAPIVersion.VERSION2, protocol=MQTTProtocolVersion.MQTTv5)
        self.host = host
        self.port = port
        self.topic = topic
        self.client.on_publish = self.on_publish

    async def async_publish(self, payload: Optional[str] = None):
        for i in range(10):
            self.client.publish(self.topic, json.dumps({"message": "test"}))
            await asyncio.sleep(1)
    
    def connect(self):
        status = self.client.connect(self.host, self.port)
        if status != MQTTErrorCode.MQTT_ERR_SUCCESS:
            raise HyperbaseMQTTConnectionError(f"Failed to connect to MQTT broker at {self.host}:{self.port}, error code: {status}")
    
    def disconnect(self):
        self.client.disconnect()
    
    def on_publish(self, client, userdata, mid, reason_code, properties):
        """Callback for when a message is published."""
        LOGGER.info(f"Message published with mid: {mid}, reason code: {reason_code}")
        if reason_code != mqtt.MQTT_ERR_SUCCESS:
            LOGGER.error(f"Failed to publish message, reason code: {reason_code}")
        else:
            LOGGER.info("Message published successfully")

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Setup Hyperbase connection from config entry"""
    mq = HyperbaseMQTTConnection(
        host=entry.data[CONF_MQTT_ADDRESS],
        port=entry.data[CONF_MQTT_PORT],
        topic=entry.data[CONF_MQTT_TOPIC]
    )
    await hass.async_add_executor_job(mq.connect)
    
    return True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    entry = hass.config_entries.async_entries(DOMAIN)
    # LOGGER.info(entry)
    
    # mq = HyperbaseMQTTConnection(
    #     host=entry[0].data[CONF_MQTT_ADDRESS],
    #     port=entry[0].data[CONF_MQTT_PORT],
    #     topic=entry[0].data[CONF_MQTT_TOPIC]
    # )
    # mq.connect()
    # await mq.publish()
    return True


class HyperbaseMQTTConnectionError(HomeAssistantError):
    """Error to indicate a Hyperbase MQTT connection error."""