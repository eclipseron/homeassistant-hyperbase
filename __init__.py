"""
The "hello world" custom component.

This component implements the bare minimum that a component should implement.

Configuration:

To use the hello_world component you will need to add the following to your
configuration.yaml file.

hello_world:
"""

from config.custom_components.hyperbase.registry import remove_registry
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from .const import CONF_MQTT_ADDRESS, CONF_MQTT_PORT, CONF_MQTT_TOPIC, CONF_PROJECT_ID, CONF_PROJECT_NAME, CONF_SERIAL_NUMBER, CONF_USER_COLLECTION_ID, CONF_USER_ID, DOMAIN, HYPERBASE_CONFIG, LOGGER
from .common import HyperbaseCoordinator
from homeassistant.helpers.device_registry import async_get as async_get_device_registry


HyperbaseConfigEntry = ConfigEntry["HyperbaseCoordinator"]

async def async_setup_entry(
    hass: HomeAssistant, entry: HyperbaseConfigEntry
) -> bool:
    """Setup Hyperbase connection from config entry"""
    dr = async_get_device_registry(hass)
    
    hyperbase = dr.async_get_or_create(
        config_entry_id=entry.entry_id,
        manufacturer="Hyperbase",
        identifiers={("hyperbase", entry.data[CONF_PROJECT_ID])},
        name=entry.data[CONF_PROJECT_NAME],
        model="Hyperbase Home Assistant Connector",
    )
    
    mqtt_address = entry.data[CONF_MQTT_ADDRESS]
    mqtt_port = entry.data[CONF_MQTT_PORT]
    mqtt_topic = entry.data[CONF_MQTT_TOPIC]
    project_name = entry.data[CONF_PROJECT_NAME]
    project_id = entry.data[CONF_PROJECT_ID]
    user_id = entry.data[CONF_USER_ID]
    user_collection_id = entry.data[CONF_USER_COLLECTION_ID]
    
    entry.runtime_data = HyperbaseCoordinator(
        hass,
        hyperbase.id,
        mqtt_address,
        mqtt_port,
        mqtt_topic,
        project_id,
        project_name,
        user_id,
        user_collection_id,
    )
    is_succeed = await entry.runtime_data.async_startup()
    
    return is_succeed


async def async_unload_entry(hass: HomeAssistant, entry: HyperbaseConfigEntry) -> bool:
    """Unload Hyperbase connection from config entry."""
    if entry.runtime_data:
        if entry.runtime_data.is_connected:
            await entry.runtime_data.disconnect()
            LOGGER.info("Disconnected from Hyperbase proxy MQTT server")
        entry.runtime_data = None
    return True


async def async_remove_entry(hass: HomeAssistant, entry: HyperbaseConfigEntry):
    """Delete all registered connector by project id"""
    await remove_registry(hass, entry.unique_id)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Initialize Hyperbase connection component."""
    hass.data[HYPERBASE_CONFIG] = config.get(DOMAIN, {})
    return True