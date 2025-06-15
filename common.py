import asyncio
from datetime import timedelta
import datetime
from typing import Any

import httpx

from .models import COLUMNS_MODELS, EntityDomainClasses, create_schema, parse_data
from homeassistant.const import CONF_API_TOKEN, Platform
from homeassistant.helpers import json
from homeassistant.helpers.entity_platform import EntityRegistry

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval
from .mqtt import MQTT
from .const import (
    CONF_PROJECT_NAME,
    DOMAIN,
    CONF_BASE_URL,
    LOGGER,
    MQTT_CONNECTED,
    MQTT_DISCONNECTED,
)
from .models.sensor import SensorModel
from .exceptions import HyperbaseHTTPError, HyperbaseMQTTConnectionError, HyperbaseRESTConnectionError, HyperbaseRESTConnectivityError
from homeassistant.helpers.device_registry import DeviceEntry, async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry, async_entries_for_device

class ListenedDeviceInfo:
    def __init__(
        self,
        listened_device: str,
        listened_entities: list[str],
        poll_time_s: int,
        hyperbase_entity_id: str | None = None,
    ):
        self.__listened_device = listened_device
        self.__listened_entities = listened_entities
        self.__poll_time_s = poll_time_s
        self.hyperbase_entity_id = hyperbase_entity_id
    
    @property
    def listened_device(self):
        return self.__listened_device
    
    @property
    def listened_entities(self):
        return self.__listened_entities
    
    @property
    def poll_time_s(self):
        return self.__poll_time_s


class ListenedDeviceEntry:
    """Class used to setup notify entity.
    This entity represents a registered device connection to hyperbase.
    """
    def __init__(self, device: DeviceEntry, entities: list[str], poll_time_s: int):
        self.original_name = f"Hyperbase {device.name} Connector"
        self.capabilities = ListenedDeviceInfo(device.id, entities, poll_time_s)
    
    @property
    def capabilities_dict(self):
        return {
            "listened_device": self.capabilities.listened_device,
            "listened_entities": self.capabilities.listened_entities,
            "poll_time_s": self.capabilities.poll_time_s
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
        device_id: str,
        server_stats: bool | None = False,
    ):
        """Initialize."""
        self.hass = hass
        self.server_stats = server_stats
        self.hyperbase_device_id = device_id
        self.on_tick_callbacks = []
        self._disconnect_callbacks = []
        self.unloading = False
        self.__mqtt_topic = hyperbase_mqtt_topic
        self.__project_name = hyperbase_project_name
        
        self.__listened_devices: list[ListenedDeviceInfo] = []
        
        self.manager = HyperbaseProjectManager(
            hass,
            hyperbase_project_id,
        )
        
        self.mqtt_client = MQTT(
            hass,
            hyperbase_mqtt_host,
            hyperbase_mqtt_port,
        )
        
        self.task_manager = HyperbaseTaskManager(
            hass,
            self.mqtt_client,
            self.manager
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
    
    
    async def async_get_listened_devices(self, registry: EntityRegistry, device_id: str):
        """
        Get list of listened devices based on hyperbase entity
        
        - `registry` is the entity registry object
        - `device_id` is id of Hyperbase connector device id
        """
        entity_entries = async_entries_for_device(registry, device_id)
        for entity in entity_entries:
            listened_device = ListenedDeviceInfo(
                entity.capabilities.get("listened_device"),
                entity.capabilities.get("listened_entities"),
                entity.capabilities.get("poll_time_s"),
                entity.entity_id,
            )
            self.__listened_devices.append(listened_device)
    
    @property
    def configured_devices(self):
        return self.__listened_devices

    async def async_add_configured_device(self, listened_device: str, listened_entities: list[str],
                                        poll_time_s: int, hyperbase_entity_id: str):
        """
        Add new listened device into the runtime.
        """
        device = ListenedDeviceInfo(listened_device, listened_entities, poll_time_s, hyperbase_entity_id)
        self.__listened_devices.append(device)
        er = async_get_entity_registry(self.hass)
        configured_domains = []
        for entity_id in listened_entities:
            entity_entry = er.async_get(entity_id)
            try:
                configured_domains.index(entity_entry.domain)
            except ValueError:
                configured_domains.append(entity_entry.domain)
        return configured_domains
    
    
    async def async_verify_device_models(self):
        dr = async_get_device_registry(self.hass)
        er = async_get_entity_registry(self.hass)
        models: dict[str, dict[str, set]] = {}
        for device in self.__listened_devices:
            device_entry = dr.async_get(device.listened_device)
            model_identity = ""
            
            if device_entry.model is not None:
                model_identity = device_entry.model
            elif device_entry.model_id is not None:
                model_identity = device_entry.model_id
            elif device_entry.name_by_user is not None:
                model_identity = device_entry.name_by_user
            else:
                model_identity = device_entry.name
            
            if models.get(model_identity, None) is None:
                if device_entry.manufacturer is not None:
                    model_identity = f"{device_entry.manufacturer} {model_identity}"
                models[model_identity] = {}
            
            for listened_entity in device.listened_entities:
                entity = er.async_get(listened_entity)
                if models[model_identity].get(entity.domain, None) is None:
                    models[model_identity][entity.domain] = set([])
                
                if entity.original_device_class is not None:
                    models[model_identity][entity.domain].add(entity.original_device_class)
        
        class_model: dict[str, list[EntityDomainClasses]] = {}
        for model_name in models.keys():
            if class_model.get(model_name, None) is None:
                class_model[model_name] = []
            
            for domain in models[model_name].keys():
                domain_class = EntityDomainClasses(
                    domain,
                    list(models[model_name][domain])
                )
                class_model[model_name].append(domain_class)
        
        await self.manager.async_revalidate_collections(class_model)
    
    
    async def async_verify_domains(self):
        er = async_get_entity_registry(self.hass)
        configured_domains = []
        for device in self.__listened_devices:
            for listened_entity in device.listened_entities:
                entity = er.async_get(listened_entity)
                try:
                    configured_domains.index(entity.domain)
                except ValueError:
                    configured_domains.append(entity.domain)
        # await self.manager.async_revalidate_collections(configured_domains)
    
    
    @callback
    def _on_connection_change(self, *args, **kwargs):
        pass


    async def connect(self):
        """Connects to MQTT Broker"""
        try:
            _ = await self.mqtt_client.async_connect()
            LOGGER.info(f"({self.__project_name}) MQTT connection established")
        except HyperbaseMQTTConnectionError as exc:
            LOGGER.error(f"({self.__project_name}) MQTT connection failed: {exc}")


    async def disconnect(self):
        """Disonnects to MQTT Broker"""
        self.unloading = True
        await self.mqtt_client.async_disconnect()
        tasks = self.task_manager.runtime_tasks
        for task in tasks:
            task() # terminate all tasks
        for cb in self._disconnect_callbacks:
            cb() # terminate event dispatcher callbacks

    @property
    def is_connected(self):
        return self.mqtt_client.connected


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
                    
                    
                    await self.mqtt_client.async_publish(
                        self.__mqtt_topic,
                        json.json_dumps({
                            "project_id": "0196a9e5-b702-7e20-b9ef-c6fa4bbce49a",
                            "collection_id": "019717a8-e86e-75e3-903b-464fb141bbdd",
                            "token_id": "0196a9e5-bc75-7902-b44d-a64cbdd53074",
                            "data": json_data
                        }),
                        qos=0,
                        retain=False,
                    )



class HyperbaseCollection:
    def __init__(
        self,
        id: str,
        name: str,
        schema_fields: list[str],
    ):
        """Initialize Hyperbase collection."""
        self.id = id
        self.name = name
        self.schema_fields = set(schema_fields)


class TaskMetadata:
    def __init__(
        self,
        device_id: str,
        entity_id:str,
        domain:str,
        poll_time_s:int):
        self.device_id = device_id
        self.entity_id = entity_id
        self.domain = domain
        self.poll_time_s = poll_time_s



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
        self.__collections = {}

    async def async_revalidate_collections(self, model_mapping:dict[str, list[EntityDomainClasses]]):
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
            collections: list[HyperbaseCollection] = []
            for collection in collections_data:
                
                # filters only homeassistant collections
                if collection["name"].startswith("hass."):
                    collections.append(HyperbaseCollection(
                        id=collection["id"],
                        name=collection["name"],
                        schema_fields=collection["schema_fields"].keys()
                        ))

            existed_models = [c.name.removeprefix("hass.") for c in collections]
            missing_collections = set(model_mapping.keys()).difference(existed_models)
            
            for model in missing_collections:
                domain_classes = model_mapping[model]
                schema = create_schema(domain_classes)
                self.hass.async_create_task(self.__async_create_collection_task(model, schema))
            
            for c in collections:
                domain_classes = model_mapping[c.name.removeprefix("hass.")]
                schema = create_schema(domain_classes)
                diff_columns = set(schema.keys()).difference(c.schema_fields)
                if len(diff_columns) > 0:
                    await self.hass.async_add_executor_job(self.__update_collection_fields,
                        c.id, schema)


    async def async_get_project_collections(self):
        response = None
        try:
            response = await self.hass.async_add_executor_job(self.__fetch_collections)
        except Exception as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Hyperbase connection failed {exc}")
        
        if response is not None:
            collections_data = response.get("data", [])
            for collection in collections_data:
                # filters only homeassistant collections
                if collection["name"].startswith("hass."):
                    collection_name = collection.get("name")
                    
                    #retrieve homeassistant.<model> value
                    entity_domain = collection_name.split(".")[1] 
                    self.__collections[entity_domain] = collection.get("id")
        LOGGER.info(f"({self.entry.data[CONF_PROJECT_NAME]}) collections reloaded")


    async def __async_create_collection_task(self, entity_domain, schema):
        await self.hass.async_add_executor_job(
            self.__create_collection, entity_domain, schema
        )

    
    def __update_collection_fields(self, collection_id, schema):
        headers = {
                "Authorization": f"Bearer {self.entry.data["auth_token"]}",
            }
        response = None
        base_url = self.entry.data[CONF_BASE_URL]
        try:
            with httpx.Client(headers=headers) as session:
                response = session.patch(f"{base_url}/api/rest/project/{self.__hyperbase_project_id}/collection/{collection_id}",
                        json={
                            "schema_fields": schema,
                        }
                    )
                response.raise_for_status()
                LOGGER.info(f"({self.entry.data[CONF_PROJECT_NAME]}) schema updated for collection: {collection_id}")
        
        except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
            raise HyperbaseRESTConnectivityError(exc.args)
        except httpx.HTTPStatusError as exc:
            raise HyperbaseHTTPError(exc.response.json()['error']['message'], status_code=exc.response.status_code)
        return response

    def __create_collection(self, entity_domain, schema):
        headers = {
                "Authorization": f"Bearer {self.entry.data["auth_token"]}",
            }
        response = None
        base_url = self.entry.data[CONF_BASE_URL]
        api_token_id = self.entry.data.get(CONF_API_TOKEN)
        
        is_success = False
        created_collection: str = ""
        try:
            with httpx.Client(headers=headers) as session:
                response = session.post(f"{base_url}/api/rest/project/{self.__hyperbase_project_id}/collection",
                        json={
                            "name": "hass." + entity_domain,
                            "schema_fields": schema,
                            "opt_auth_column_id": False
                        }
                    )
                response.raise_for_status()
                is_success = True
                LOGGER.info(f"({self.entry.data[CONF_PROJECT_NAME]}) create new collection: hass.{entity_domain}")
                
                # insert new rule for api token to insert into created collection
                result = response.json()
                data = result.get("data")
                created_collection = data.get("name")
                created_collection_id = data.get("id")
                response = session.post(f"{base_url}/api/rest/project/{self.__hyperbase_project_id}/token/{api_token_id}/collection_rule",
                        json={
                            "collection_id": created_collection_id,
                            "find_one": "none",
                            "find_many": "none",
                            "insert_one": True,
                            "update_one": "none",
                            "delete_one": "none"
                        }
                    )
                response.raise_for_status()
        except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
            raise HyperbaseRESTConnectivityError(exc.args)
        except httpx.HTTPStatusError as exc:
            if not is_success:
                raise HyperbaseHTTPError(exc.response.json()['error']['message'], status_code=exc.response.status_code)
            LOGGER.warning(f"({self.entry.data[CONF_PROJECT_NAME]}) Failed to create new rule for collection {created_collection}. Please add it manually in the Hyperbase.")
        return response


    def __fetch_collections(self):
        result = None
        try:
            with httpx.Client() as client:
                if not self.entry.data["auth_token"]:
                    raise HyperbaseRESTConnectionError("Token not found", 401)
                client.headers.update({
                    "Authorization": f"Bearer {self.entry.data["auth_token"]}",
                })
                client.base_url = self.entry.data[CONF_BASE_URL]
                result = client.get(f"/api/rest/project/{self.__hyperbase_project_id}/collections")
                result.raise_for_status()
        except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
            raise HyperbaseRESTConnectivityError(exc.args)
        except httpx.HTTPStatusError as exc:
            raise HyperbaseHTTPError(exc.response.json()['error']['status'], status_code=exc.response.status_code)
        
        if result is not None:
            return result.json()

    @property
    def collections(self):
        return self.__collections



class Task:
    def __init__(
        self,
        hass: HomeAssistant,
        mqtt_client: MQTT,
        metadata: TaskMetadata,
        hyperbase_entity_id: str,
        project_manager: HyperbaseProjectManager
    ):
        self.hass = hass
        self.metadata = metadata
        self._mqttc = mqtt_client
        self.__hyperbase_entity_id = hyperbase_entity_id
        self.__project_manager = project_manager
        
        er = async_get_entity_registry(self.hass)
        dr = async_get_device_registry(self.hass)
        self.entity_entry = er.async_get(self.metadata.entity_id)
        self.device_entry = dr.async_get(self.metadata.device_id)
        
        self.hyperbase_entry = er.async_get(self.__hyperbase_entity_id)
        self.hyperbase_device = dr.async_get(self.hyperbase_entry.device_id)
    
    async def async_publish_on_tick(self, *args):
        state = self.hass.states.get(self.metadata.entity_id)
        if state is None:
            LOGGER.warning(f"State for entity: {self.metadata.entity_id} is None")
            return
        
        json_data = parse_data(
            self.hyperbase_device.serial_number,
            self.__hyperbase_entity_id,
            self.device_entry,
            self.entity_entry,
            state,
            last_reported=state.last_reported
            )
        if json_data is None:
            LOGGER.warning(f"Unsupported entity domain: {self.entity_entry.domain}")
            return
        
        self.hass.async_create_task(self._mqttc.async_publish(
            "hyperbase-pg",
            json.json_dumps({
                "project_id": "0196a9e5-b702-7e20-b9ef-c6fa4bbce49a",
                "collection_id": self.__project_manager.collections[self.entity_entry.domain],
                "token_id": "01975ee2-9d14-74e2-8d4d-de0d29634044",
                "data": json_data,
            }),
            qos=0,
            retain=False,
            ))
        self.hass.states.async_set(
            self.__hyperbase_entity_id,
            new_state=datetime.datetime.now(),
            attributes=self.hyperbase_entry.capabilities,
            timestamp=datetime.datetime.now().toordinal()
        )



class HyperbaseTaskManager:
    def __init__(self, hass: HomeAssistant, mqttc: MQTT, project_manager = HyperbaseProjectManager):
        self.hass = hass
        self.__mqttc = mqttc
        self.__dr = async_get_device_registry(self.hass)
        self.__er = async_get_entity_registry(self.hass)
        self.__runtime_tasks = []
        self.__project_manager = project_manager


    async def async_load_runtime_tasks(self, configured_devices: list[ListenedDeviceInfo]):
        for device in configured_devices:
            for entity_id in device.listened_entities:
                self.hass.async_create_task(
                    self.__async_get_entity_state(
                        device.listened_device,
                        entity_id,
                        device.poll_time_s,
                        device.hyperbase_entity_id,
                        self._on_state_loaded
                    ))


    async def __async_get_entity_state(self, device_id, entity_id, poll_time_s, hyperbase_entity_id, loader_callback):
        """
        Try to poll entity state each 5 seconds.
        Loop exited if state registered.
        
        Calls `loader_callback` when exit.
        """
        domain = None
        while True:
            state = self.hass.states.get(entity_id)
            if state is not None:
                domain = state.domain
                break
            await asyncio.sleep(5) # wait for 5 seconds before refetch state
        LOGGER.info(f"state for {state.entity_id} verified")
        if state is not None:
            loader_callback(device_id, entity_id, domain, poll_time_s, hyperbase_entity_id)


    @property
    def runtime_tasks(self):
        return self.__runtime_tasks
    
    @callback
    def _on_state_loaded(self, device_id, entity_id, domain, poll_time_s, hyperbase_entity_id):
        task = Task(
            hass=self.hass,
            mqtt_client=self.__mqttc,
            metadata = TaskMetadata(
                device_id,
                entity_id,
                domain,
                poll_time_s,
            ),
            hyperbase_entity_id = hyperbase_entity_id,
            project_manager=self.__project_manager
        )
        self.__runtime_tasks.append(
            async_track_time_interval(
                    self.hass,
                    task.async_publish_on_tick,
                    interval=timedelta(seconds=task.metadata.poll_time_s),
                ),
            )