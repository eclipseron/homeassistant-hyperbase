"""
The "hello world" custom component.

This component implements the bare minimum that a component should implement.

Configuration:

To use the hello_world component you will need to add the following to your
configuration.yaml file.

hello_world:
"""

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.start import async_at_start
from .const import CONF_MQTT_ADDRESS, CONF_MQTT_PORT, CONF_MQTT_TOPIC, CONF_PROJECT_ID, CONF_PROJECT_NAME, DOMAIN, HYPERBASE_CONFIG, LOGGER
from .common import HyperbaseCoordinator, HyperbaseProjectManager
from .exceptions import HyperbaseMQTTConnectionError


HyperbaseConfigEntry = ConfigEntry["HyperbaseCoordinator"]

async def async_setup_entry(
    hass: HomeAssistant, entry: HyperbaseConfigEntry
) -> bool:
    """Setup Hyperbase connection from config entry"""
    config = hass.data[HYPERBASE_CONFIG]
    mqtt_address = entry.data[CONF_MQTT_ADDRESS]
    mqtt_port = entry.data[CONF_MQTT_PORT]
    mqtt_topic = entry.data[CONF_MQTT_TOPIC]
    project_name = entry.data[CONF_PROJECT_NAME]
    
    project_config = HyperbaseProjectManager(
        hass,
        entry.data[CONF_PROJECT_ID],
    )
    # await project_config.async_revalidate_collections()
    
    entry.runtime_data = HyperbaseCoordinator(
        hass,
        mqtt_address,
        mqtt_port,
        mqtt_topic,
        project_name
    )
    await entry.runtime_data.connect()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HyperbaseConfigEntry) -> bool:
    """Unload Hyperbase connection from config entry."""
    if entry.runtime_data:
        if entry.runtime_data.is_connected:
            await entry.runtime_data.disconnect()
            LOGGER.info("Disconnected from Hyperbase proxy MQTT server")
        entry.runtime_data = None
    return True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Initialize Hyperbase connection component."""
    hass.data[HYPERBASE_CONFIG] = config.get(DOMAIN, {})
    return True