"""
The "hello world" custom component.

This component implements the bare minimum that a component should implement.

Configuration:

To use the hello_world component you will need to add the following to your
configuration.yaml file.

hello_world:
"""
from __future__ import annotations
import asyncio
import json
import random

from paho.mqtt.enums import CallbackAPIVersion

from homeassistant.const import EVENT_SERVICE_REGISTERED
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from paho.mqtt import client, properties

from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

# The domain of your component. Should be equal to the name of your component.

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    # hass.data.setdefault(DOMAIN, {})
    # hass.data[DOMAIN][entry.entry_id] = entry.data
    # mq = client.Client(CallbackAPIVersion.VERSION2, "ar_hass", transport="websockets")
    # mq.ws_set_options(path="/mqtt")
    # mq.connect("10.42.28.70", 8083)
    # for i in range(20):
    #     data = {
    #         "project_id": "0196a9e5-b702-7e20-b9ef-c6fa4bbce49a",
    #         "token_id": "0196a9e5-bc75-7902-b44d-a64cbdd53074",
    #         "collection_id": "0196d83f-2ee2-7e41-a56f-c76731636a6d", # sensor
    #         "data": {
    #             "instance_id": "device-plug-b1",
    #             "entitiy_id": "sensor.plug_b1_voltage",
    #             "state": float(random.randint(2200,2290)) / 10,
    #         }
    #     }
    #     mq.publish("hyperbase-pg", json.dumps(data))
    #     _LOGGER.info("ping to hyperbase")
    return True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.services.async_services_for_domain("tuya")
    return True