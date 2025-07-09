import os
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from .const import LOGGER, DOMAIN
from homeassistant.helpers.json import save_json
from homeassistant.util.json import load_json_object
from .util import get_model_identity
from homeassistant.helpers.device_registry import async_get as async_get_device_registry

DEFAULT_CONFIG_PATH = "config/.storage/hyperbase.config"


async def async_get_hyperbase_registry(hass: HomeAssistant):
    is_exists = await hass.async_add_executor_job(os.path.exists, DEFAULT_CONFIG_PATH)
    if not is_exists:
        hass.async_add_executor_job(save_json, DEFAULT_CONFIG_PATH, {})
    registry = await hass.async_add_executor_job(load_json_object, DEFAULT_CONFIG_PATH)
    return HyperbaseRegistry(hass, registry)


class HyperbaseConnectorEntry:
    def __init__(self,
        hass: HomeAssistant,
        connector_entity_id: str,
        project_id: str,
        listened_device: str,
        listened_entities: list[str],
        poll_time_s: int,
        ):
        self._connector_entity_id = connector_entity_id
        self._project_id = project_id
        self._listened_device = listened_device
        self._listened_entities = listened_entities
        self._poll_time_s = poll_time_s
        
        dr = async_get_device_registry(hass)
        device = dr.async_get(listened_device)
        self._collection_name = get_model_identity(device)

class HyperbaseRegistry:
    def __init__(self,
        hass: HomeAssistant,
        conf: dict,
        ):
        self.hass = hass
        self._entry_json = conf.copy()
    
    
    def get_connector_entry(self, connector_entity_id):
        entry = self._entry_json.get(connector_entity_id)
        if entry is None:
            return None

        connector = HyperbaseConnectorEntry(
            hass = self.hass,
            connector_entity_id = connector_entity_id,
            project_id = entry.get("project_id"),
            listened_device = entry.get("listened_device"),
            listened_entities = entry.get("listened_entities"),
            poll_time_s = entry.get("poll_time_s"),
        )
        return connector
    
    
    def get_connector_entries(self) -> list[HyperbaseConnectorEntry]:
        entries: list[HyperbaseConnectorEntry] = []
        
        for connector_entity_id in self._entry_json.keys():
            connector = self.get_connector_entry(connector_entity_id)
            entries.append(connector)
        
        return entries
    
    
    async def async_update_connector_entries(
        self,
        connector_entity_id: str,
        listened_entities: str,
        poll_time_s: int
    ) -> HyperbaseConnectorEntry:
        prev_entry = self._entry_json.get(connector_entity_id).copy()
        
        new_entry = {
            "project_id": prev_entry.get("project_id"),
            "listened_device": prev_entry.get("listened_device"),
            "listened_entities": listened_entities,
            "poll_time_s": poll_time_s
        }
        
        self._entry_json[connector_entity_id] = new_entry
        await self.hass.async_add_executor_job(save_json, DEFAULT_CONFIG_PATH, self._entry_json)
        return HyperbaseConnectorEntry(
            hass=self.hass,
            connector_entity_id=connector_entity_id,
            listened_device=prev_entry.get("listened_device"),
            listened_entities=listened_entities,
            poll_time_s=poll_time_s,
            project_id=prev_entry.get("project_id"),
        )
    
    
    def get_connector_entries_for_project(self, project_id: str) -> list[HyperbaseConnectorEntry]:
        entries: list[HyperbaseConnectorEntry] = []
        
        for connector_entity_id in self._entry_json.keys():
            if self._entry_json[connector_entity_id].get("project_id") == project_id:
                connector = self.get_connector_entry(connector_entity_id)
                entries.append(connector)
        
        return entries
    
    async def async_create_connector_entry(
        self,
        connector_entity_id: str,
        listened_device: str,
        listened_entities: list[str],
        project_id: str,
        poll_time_s: int,
    ):
        if self._entry_json.get(connector_entity_id) is not None:
            return self.get_connector_entry(connector_entity_id)
        
        self._entry_json[connector_entity_id] = {
            "project_id": project_id,
            "listened_device": listened_device,
            "listened_entities": listened_entities,
            "poll_time_s": poll_time_s
        }
        await self.hass.async_add_executor_job(save_json, DEFAULT_CONFIG_PATH, self._entry_json)
        
        connector = HyperbaseConnectorEntry(
            hass = self.hass,
            connector_entity_id = connector_entity_id,
            project_id = project_id,
            listened_device = listened_device,
            listened_entities = listened_entities,
            poll_time_s = poll_time_s,
        )
        return connector

    
    async def async_store_connector_entry(self, connector: HyperbaseConnectorEntry):
        if connector._collection_name is None:
            dr = async_get_device_registry(self.hass)
            device = dr.async_get(connector._listened_device)
            connector._collection_name = get_model_identity(device)
        
        self._entry_json[connector._connector_entity_id] = {
            "project_id": connector._project_id,
            "listened_device": connector._listened_device,
            "listened_entities": connector._listened_entities,
            "poll_time_s": connector._poll_time_s
        }
        await self.hass.async_add_executor_job(save_json, DEFAULT_CONFIG_PATH, self._entry_json)
        return connector

    
    async def async_delete_connector_entry(self, connector_entity_id: str):
        if self._entry_json.get(connector_entity_id) is None:
            raise ConnectoryEntryNotExists
        del self._entry_json[connector_entity_id]
        await self.hass.async_add_executor_job(save_json, DEFAULT_CONFIG_PATH, self._entry_json)


class ConnectoryEntryNotExists(HomeAssistantError):
    """Connector entry is not exists in Hyperbase config file."""