import asyncio
from datetime import timedelta
import datetime
import json
import time
from typing import Any
import uuid

import httpx

from homeassistant.helpers.entity import Entity
from .util import format_device_name
from homeassistant.components.sensor import SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback, State
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval, async_call_later
from homeassistant.helpers.aiohttp_client import async_create_clientsession
# from homeassistant.helpers.
from homeassistant.components.alarm_control_panel import AlarmControlPanelState
from .mqtt import MQTT
from .const import (
    CONF_PROJECT_NAME,
    CONF_REST_TOKEN,
    DOMAIN,
    HYPERBASE_RESPONSE_CODE,
    HYPERBASE_RESPONSE_MSG,
    HYPERBASE_RESPONSE_SUCCESS,
    CONF_BASE_URL,
    LOGGER,
    MQTT_CONNECTED,
    MQTT_DISCONNECTED,
)
from .models.sensor import SensorModel
from enum import StrEnum
from .exceptions import HyperbaseMQTTConnectionError, HyperbaseRESTConnectionError
from homeassistant.helpers.device_registry import DeviceEntry, DeviceEntryType, async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry, async_entries_for_device

# er.async_get_or_create(
#                 domain="notify",
#                 platform="hyperbase",
#                 unique_id=f"{format_device_name(registering_device.name)}_binding",
#                 has_entity_name=True,
#                 config_entry=self.config_entry,
#                 get_initial_options=None,
#                 capabilities={
#                     "device": new_device.device,
#                     "entities": new_device.entities,
#                     "poll_time_s": new_device.poll_time_s,
#                 }
#             )

class ListenedDeviceEntry:
    def __init__(self, device: DeviceEntry, entities: list[str], poll_time_s: int):
        self.unique_id = f"{format_device_name(device.name)}_binding"
        self.original_name = f"Hyperbase {device.name} Data Collecting"
        self.capabilities = {
            "listened_device": device.id,
            "listened_entities": entities,
            "poll_time_s": poll_time_s
        }


class HyperbaseCoordinator:
    
    def __init__(
        self,
        hass: HomeAssistant,
        hyperbase_mqtt_host: str,
        hyperbase_mqtt_port: int,
        hyperbase_mqtt_topic: str,
        hyperbase_project_name: str,
        hyperbase_project_id: str,
        server_stats: bool | None = False,
    ):
        """Initialize."""
        self.hass = hass
        self.server_stats = server_stats
        self.on_tick_callbacks = []
        self._disconnect_callbacks = []
        self.unloading = False
        self.__mqtt_topic = hyperbase_mqtt_topic
        self.__project_name = hyperbase_project_name
        
        self.devices: list[str] = [
            "424d2d933ce25eb5b17d074cc9202452", #SEMB2
            "45798051e676abc0bf932198f17f2dbc", #SEMB1
        ]
        
        
        self.manager = HyperbaseProjectManager(
            hass,
            hyperbase_project_id,
        )

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

    def verify_device_platform(self):
        er = async_get_entity_registry(self.hass)
        configured_platforms = []
        for device in self.devices:
            entries = async_entries_for_device(er, device)
            for e in entries:
                try:
                    configured_platforms.index(e.domain)
                except ValueError:
                    configured_platforms.append(e.domain)
        self.hass.async_create_task(self.revalidate_collections())

    @callback
    def _on_connection_change(self, *args, **kwargs):
        pass


    async def revalidate_collections(self):
        await self.manager.async_revalidate_collections()


    async def connect(self):
        try:
            _ = await self.mqtt_client.async_connect()
        except HyperbaseMQTTConnectionError as exc:
            LOGGER.error(f"({self.__project_name}) MQTT connection failed: {exc}")
            return
        
        # add publish job only on successful connection
        LOGGER.info(f"({self.__project_name}) MQTT connection established")
        self.on_tick_callbacks.append(
            async_track_time_interval(self.hass, self.__async_publish_on_tick, timedelta(seconds=2))
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

    @property
    def new_registered_devices(self):
        return self.__new_registered_devices

    async def __async_publish_on_tick(self, *args):
        dr = async_get_device_registry(self.hass)
        er = async_get_entity_registry(self.hass)
        for id in dr.devices:
            entry = async_entries_for_device(er, id)
            device = dr.async_get(id)
            dict_repr = device.dict_repr
            for e in entry:
                    
                state = self.hass.states.get(e.entity_id)
                if state is None:
                    continue
                if state.domain == "sensor":
                    json_data = {
                        "integration_id": f"ZaBfXcDe{self.__project_name}",
                        "entity_id": e.entity_id,
                        "hass_device_id": dict_repr["id"],
                        "domain": dict_repr["identifiers"][0][0],
                        "product_id": dict_repr["identifiers"][0][1],
                        "manufacturer": dict_repr["manufacturer"],
                        "model_name": dict_repr["model"],
                        "model_id": dict_repr["model_id"],
                        "name_default": dict_repr["name"],
                        "name_by_user": dict_repr["name_by_user"],
                        "device_class": state.attributes.get("device_class", None),
                        "last_reset": state.last_reported.isoformat(),
                        "unit_of_measurement": e.unit_of_measurement,
                    }
                    if state.state == "unknown" or state.state == "unavailable":
                        continue
                    try:
                        _ = datetime.datetime.fromisoformat(state.state)
                        json_data["value_datetime"] = state.state
                    except:
                        try:
                            json_data["value_numeric"] = float(state.state)
                        except:
                            json_data["value_str"] = state.state
                    
                    try:
                        json_data["state_class"] = state.attributes["state_class"].name
                    except AttributeError:
                        json_data["state_class"] = state.attributes["state_class"]
                    except KeyError:
                        pass
                    # await self.mqtt_client.async_publish(
                    #     self.__mqtt_topic,
                    #     json.dumps({
                    #         "project_id": "0196a9e5-b702-7e20-b9ef-c6fa4bbce49a",
                    #         "collection_id": "019717a8-e86e-75e3-903b-464fb141bbdd",
                    #         "token_id": "0196a9e5-bc75-7902-b44d-a64cbdd53074",
                    #         "data": json_data
                    #     }),
                    #     qos=0,
                    #     retain=False,
                    # )
    
    # async def update_entity_list(self):
    #     _device_registry = async_get_device_registry(self.hass)
    #     _entity_registry = async_get_entity_registry(self.hass)
    #     async def entry_devices():
    #         for device in _device_registry.devices:
    #             for entity in async_entries_for_device(_entity_registry, device):
    #                 LOGGER.info(self.hass.states.get(entity.entity_id).as_dict())
    #                 await asyncio.sleep(1)
    #     entry = self.hass.async_create_task(entry_devices())
    #     await entry
        



class HyperbaseCollection:
    def __init__(
        self,
        id: str,
        name: str,
    ):
        """Initialize Hyperbase collection."""
        self.id = id
        self.name = name

from homeassistant.const import BASE_PLATFORMS



class HyperbaseProjectManager:
    def __init__(
        self,
        hass: HomeAssistant,
        hyperbase_project_id: str,
    ):
        """Initialize Hyperbase project manager."""
        self.hass = hass
        self.__hyperbase_project_id = hyperbase_project_id
        self.entry = self.hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, self.__hyperbase_project_id)

    async def async_revalidate_collections(self):
        """Validate hyperbase collections.
        
        Collections are named as follows homeassistant.<base_platform>
        where platform_type is the type of the platform (e.g. sensor, switch, light).
        If the collection does not exist, it will be created.
        
        Platform types are used to determine where to store entity states.
        Example: `sensor.plug_b1_voltage`
        """
        response = None
        try:
            response = await self.hass.async_add_executor_job(self.__fetch_collections)
        except HyperbaseRESTConnectionError as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Hyperbase connection failed ({exc.status_code}): {exc}")
        
        if response is not None:
            collections_data = response.get("data", [])
            collections = []
            for collection in collections_data:
                
                # filters only homeassistant collections
                if collection["name"].startswith("homeassistant."):
                    collections.append(HyperbaseCollection(
                        id=collection["id"],
                        name=collection["name"],
                        ))

            existed_platforms = [c.name.split(".")[1] for c in collections]
            missing_collections = set(["sensor", "binary_sensor", "light"]).difference(existed_platforms)
            sensor_model = SensorModel()
            for platform in missing_collections:
                schema = sensor_model.columns
                await self.hass.async_add_executor_job(self.__create_collection, platform, schema)


    def __create_collection(self, platform, schema):
        # result = None
        headers = {
                "Authorization": f"Bearer {self.entry.data[CONF_REST_TOKEN]}",
                # "Authorization": f"Bearer",
            }
        try:
            with httpx.Client(headers=headers) as session:
                response = session.post(f"{self.entry.data[CONF_BASE_URL]}/api/rest/project/{self.__hyperbase_project_id}/collection",
                        json={
                            "name": "homeassistant." + platform,
                            "schema_fields": schema,
                            "opt_auth_column_id": False
                        }
                    )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            LOGGER.error(f"Create collection failed ({exc.response.status_code}): {exc.response.json()["error"]}")
        return


    def __fetch_collections(self):
        result = None
        try:
            with httpx.Client() as client:
                if not self.entry.data[CONF_REST_TOKEN]:
                    raise HyperbaseRESTConnectionError("Token not found", 401)
                client.headers.update({
                    "Authorization": f"Bearer {self.entry.data[CONF_REST_TOKEN]}",
                })
                client.base_url = self.entry.data[CONF_BASE_URL]
                result = client.get(f"/api/rest/project/{self.__hyperbase_project_id}/collections")
                result.raise_for_status()
        except OSError as exc:
            raise HyperbaseRESTConnectionError(str(exc), 1)
        except httpx.ConnectTimeout as exc:
            raise HyperbaseRESTConnectionError("Connection timeout", 1)
        except httpx.HTTPStatusError as exc:
            raise HyperbaseRESTConnectionError(exc.response.json()["error"]["message"], exc.response.status_code)
        
        if result is not None:
            LOGGER.info("Fetched collections from Hyperbase REST API")
            return result.json()