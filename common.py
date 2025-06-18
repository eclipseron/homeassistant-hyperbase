import asyncio
from datetime import timedelta
import datetime
from typing import Any

import httpx

from .util import get_model_identity

from .models import DomainDeviceClass, create_schema, parse_entity_data
from homeassistant.const import CONF_API_TOKEN
from homeassistant.helpers import json

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
from .exceptions import HyperbaseHTTPError, HyperbaseMQTTConnectionError, HyperbaseRESTConnectionError, HyperbaseRESTConnectivityError
from homeassistant.helpers.device_registry import DeviceEntry, async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import RegistryEntry, async_get as async_get_entity_registry, async_entries_for_device

class ListenedDeviceInfo:
    def __init__(
        self,
        listened_device: str,
        listened_entities: list[str],
        poll_time_s: int,
        hyperbase_entity_id: str | None = None,
        model_identity: str | None = None
    ):
        self.__listened_device = listened_device
        self.__listened_entities = listened_entities
        self.__poll_time_s = poll_time_s
        self.hyperbase_entity_id = hyperbase_entity_id
        self.__model_identity = model_identity
    
    @property
    def listened_device(self):
        return self.__listened_device
    
    @property
    def listened_entities(self):
        return self.__listened_entities
    
    @property
    def poll_time_s(self):
        return self.__poll_time_s
    
    @property
    def model_identity(self):
        return self.__model_identity


class ListenedDeviceEntry:
    """Class used to setup notify entity.
    This entity represents a registered device connection to hyperbase.
    """
    def __init__(self, device: DeviceEntry, entities: list[str], poll_time_s: int):
        self.original_name = f"Hyperbase {device.name} Connector"
        model_identity = get_model_identity(device)
        self.capabilities = ListenedDeviceInfo(device.id, entities,
                                poll_time_s, model_identity=model_identity)
    
    @property
    def capabilities_dict(self):
        return {
            "listened_device": self.capabilities.listened_device,
            "listened_entities": self.capabilities.listened_entities,
            "poll_time_s": self.capabilities.poll_time_s,
            "collection_name": self.capabilities.model_identity,
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
        # server_stats: bool | None = False,
    ):
        """Initialize."""
        self.hass = hass
        # self.server_stats = server_stats
        self.hyperbase_device_id = device_id
        # self.on_tick_callbacks = []
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
    
    
    async def async_startup(self):
        er = async_get_entity_registry(self.hass)
        entity_entries = async_entries_for_device(er, self.hyperbase_device_id)
        
        for entity in entity_entries:
            listened_device = ListenedDeviceInfo(
                entity.capabilities.get("listened_device"),
                entity.capabilities.get("listened_entities"),
                entity.capabilities.get("poll_time_s"),
                entity.entity_id,
                entity.capabilities.get("collection_name"),
            )
            self.__listened_devices.append(listened_device)
        model_domains_map = await self.__async_verify_device_models()
        LOGGER.info(f"({self.__project_name}) Startup: Listened devices loaded")
        await self.manager.async_revalidate_collections(model_domains_map)
        LOGGER.info(f"({self.__project_name}) Startup: Hyperbase collections revalidated")
        await self.manager.async_get_project_collections()
        
        await self.connect()
        await self.task_manager.async_load_runtime_tasks(self.__listened_devices)
    
    
    @property
    def configured_devices(self):
        return self.__listened_devices

    async def async_add_new_listened_device(self, device: ListenedDeviceInfo):
        """
        Add new listened device into the runtime.
        """
        self.__listened_devices.append(device)
        if device.model_identity is None:
            raise Exception("device model identity is not exist")
        model_identity = device.model_identity
        models = {
            model_identity: {}
        }
        er = async_get_entity_registry(self.hass)
        for entity in device.listened_entities:
            entity_entry = er.async_get(entity)
            if models[model_identity].get(entity_entry.domain, None) is None:
                models[model_identity][entity_entry.domain] = set([])
            
            if entity_entry.original_device_class is not None:
                models[model_identity][entity_entry.domain].add(entity_entry.original_device_class)
        
        model_domains_map: dict[str, list[DomainDeviceClass]] = {
            model_identity: []
        }
        for domain in models[model_identity].keys():
            domain_class = DomainDeviceClass(
                domain,
                list(models[model_identity][domain])
            )
            model_domains_map[model_identity].append(domain_class)
        
        await self.manager.async_revalidate_collections(model_domains_map)

    
    async def __async_verify_device_models(self):
        """
        Get each device model and construct mapping for corresponding entity domains.
        
        Returns a `dict` with model identities as key and list of DomainDeviceClass.
        Model identity will be used to create new collection if needed with pattern
        `hass.<manufacturer> <model identity>`. Model identity can be one of these. Identity priority
        is aligned with the order.
        - model name
        - model id
        - device name by user
        - device default name
        """
        er = async_get_entity_registry(self.hass)
        models: dict[str, dict[str, set]] = {}
        for device in self.__listened_devices:
            model_identity = device.model_identity
            
            if models.get(model_identity, None) is None:
                models[model_identity] = {}
            
            for listened_entity in device.listened_entities:
                entity = er.async_get(listened_entity)
                if models[model_identity].get(entity.domain, None) is None:
                    models[model_identity][entity.domain] = set([])
                
                if entity.original_device_class is not None:
                    models[model_identity][entity.domain].add(entity.original_device_class)
        
        model_domains_map: dict[str, list[DomainDeviceClass]] = {}
        for model_name in models.keys():
            if model_domains_map.get(model_name, None) is None:
                model_domains_map[model_name] = []
            
            for domain in models[model_name].keys():
                domain_class = DomainDeviceClass(
                    domain,
                    list(models[model_name][domain])
                )
                model_domains_map[model_name].append(domain_class)
        
        return model_domains_map
    
    
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
        entities:list[str],
        poll_time_s:int):
        self.device_id = device_id
        self.entities = entities
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

    async def async_revalidate_collections(self, model_mapping:dict[str, list[DomainDeviceClass]]):
        """Revalidate hyperbase collections.
        
        Collections are named as follows `hass.<manufacturer> <model identity>`
        where model identity is the type one of model name, model ID,
        device name by user, or device default name.
        If the collection does not exist, it will be created.
        
        Example: `hass.Tuya Wifi Smart Plug`
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

            existing_collections = [c.name.removeprefix("hass.") for c in collections]
            
            latest_collections = model_mapping.keys()
            missing_collections = set(latest_collections).difference(existing_collections)
            
            for model_name in missing_collections:
                device_classes = model_mapping[model_name]
                schema_fields = create_schema(device_classes)
                
                # invoke parallel execution of independent tasks to create new collections
                self.hass.async_create_task(self.__async_create_collection_task(model_name, schema_fields))
            
            for collection in collections:
                if model_mapping.get(collection.name.removeprefix("hass."), None) is None:
                    continue
                device_classes = model_mapping[collection.name.removeprefix("hass.")]
                latest_schema = create_schema(device_classes)
                existing_schema = collection.schema_fields
                missing_columns = set(latest_schema.keys()).difference(existing_schema)
                if len(missing_columns) > 0:
                    
                    # update collection schema need to be sync to prevent race condition with write
                    # operation into hyperbase
                    self.hass.async_create_task(self.__async_update_collection_task(collection.id, latest_schema, collection.name))


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
                    
                    #retrieve hass.<model identity> value
                    device_model = collection_name.removeprefix("hass.")
                    self.__collections[device_model] = collection.get("id")
        LOGGER.info(f"({self.entry.data[CONF_PROJECT_NAME]}) collections reloaded")


    async def __async_create_collection_task(self, entity_domain, schema):
        await self.hass.async_add_executor_job(
            self.__create_collection, entity_domain, schema
        )
    
    async def __async_update_collection_task(self, collection_id, schema,
        collection_name: str | None = None):
        await self.hass.async_add_executor_job(
            self.__update_collection_fields, collection_id, schema, collection_name
        )

    
    def __update_collection_fields(self, collection_id, schema, collection_name):
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
                LOGGER.info(f"({self.entry.data[CONF_PROJECT_NAME]}) schema updated for collection: {collection_name}")
        
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
        """
        Create a GET request to Hyperbase REST API to get list of existing collections within the project.
        This is a blocking process and must be executed by sync worker.
        """
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
    
    async def async_publish_on_tick(self, *args):
        er = async_get_entity_registry(self.hass)
        dr = async_get_device_registry(self.hass)
        device_entry = dr.async_get(self.metadata.device_id)
        hyperbase_entry = er.async_get(self.__hyperbase_entity_id)
        hyperbase_device = dr.async_get(hyperbase_entry.device_id)
        
        sent_data = {
            "area_id": device_entry.area_id,
            "connector_entity": self.__hyperbase_entity_id,
            "connector_serial_number": hyperbase_device.serial_number,
            "name_by_user": device_entry.name_by_user,
            "name_default": device_entry.name,
            "product_id": device_entry.dict_repr["identifiers"][0][1]
        }
        
        _data_exists = False
        for entity in self.metadata.entities:
            state = self.hass.states.get(entity)

            if state is None or state == "unavailable":
                continue
            entity_entry = er.async_get(entity)
            entity_data = parse_entity_data(entity_entry, state.state)
            if entity_data is not None:
                sent_data = {**sent_data, **entity_data}
                _data_exists = True # flag used to indicate valuable data
        
        # only publish data if at least one valuable data exists
        if not _data_exists:
            return
        
        self.hass.async_create_task(self._mqttc.async_publish(
            "hyperbase-pg",
            json.json_dumps({
                "project_id": "01975477-e801-7643-98eb-f5331419a6ab",
                "collection_id": self.__project_manager.collections[hyperbase_entry.capabilities.get("collection_name")],
                "token_id": "01975485-6724-73f2-a618-713250f3872b",
                "data": sent_data,
            }),
            qos=0,
            retain=False,
            ))
        self.hass.states.async_set(
            self.__hyperbase_entity_id,
            new_state=datetime.datetime.now(),
            attributes=hyperbase_entry.capabilities,
            timestamp=datetime.datetime.now().timestamp()
        )



class HyperbaseTaskManager:
    def __init__(self, hass: HomeAssistant, mqttc: MQTT, project_manager = HyperbaseProjectManager):
        self.hass = hass
        self.__mqttc = mqttc
        # self.__dr = async_get_device_registry(self.hass)
        # self.__er = async_get_entity_registry(self.hass)
        self.__runtime_tasks = []
        self.__project_manager = project_manager


    async def async_load_runtime_tasks(self, listened_devices: list[ListenedDeviceInfo]):
        for device in listened_devices:
            task = Task(
                hass=self.hass,
                mqtt_client=self.__mqttc,
                metadata = TaskMetadata(
                    device_id=device.listened_device,
                    entities=device.listened_entities,
                    poll_time_s=device.poll_time_s,
                ),
                hyperbase_entity_id = device.hyperbase_entity_id,
                project_manager=self.__project_manager
            )
            self.__runtime_tasks.append(async_track_time_interval(self.hass,
                    task.async_publish_on_tick,
                    interval=timedelta(seconds=device.poll_time_s)
                ))

    @property
    def runtime_tasks(self):
        return self.__runtime_tasks