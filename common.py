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
        self.listened_entities = listened_entities
        self.poll_time_s = poll_time_s
        self.hyperbase_entity_id = hyperbase_entity_id
        self.__model_identity = model_identity
    
    @property
    def listened_device(self):
        return self.__listened_device
    
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
        device_id: str,
        hyperbase_mqtt_host: str,
        hyperbase_mqtt_port: int,
        hyperbase_mqtt_topic: str,
        hyperbase_project_id: str,
        hyperbase_project_name: str,
        serial_number: str,
    ):
        """Initialize."""
        self.hass = hass
        self.hyperbase_device_id = device_id
        self._disconnect_callbacks = []
        self.unloading = False
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
            connector_serial_number=serial_number,
            mqttc = self.mqtt_client,
            mqtt_topic=hyperbase_mqtt_topic,
            project_manager=self.manager,
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
        self.reload_listened_devices()
        model_domains_map = await self.__async_verify_device_models()
        LOGGER.info(f"({self.__project_name}) Startup: Listened devices loaded")
        await self.manager.async_revalidate_collections(model_domains_map)
        LOGGER.info(f"({self.__project_name}) Startup: Hyperbase collections revalidated")
        
        await self.connect()
        await self.task_manager.async_load_runtime_tasks(self.__listened_devices)
    
    
    def reload_listened_devices(self) -> list[ListenedDeviceInfo]:
        """Reload listened devices and return updated list of ListenedDeviceInfo to be used later"""
        self.__listened_devices = []
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
        return self.__listened_devices


    async def async_add_new_listened_device(self, device: ListenedDeviceInfo, entity_id: str):
        """
        Add new listened device into the runtime.
        """
        device.hyperbase_entity_id = entity_id
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
        await self.task_manager.async_load_runtime_tasks([device]) # register new device into runtime task


    async def async_update_listened_entities(self,
        connector_entity: str,
        listened_entities: list[str],
        poll_time_s: int
        ):
        
        device_info = self.task_manager.get_device_info_by_entity(connector_entity)
        model_identity = device_info.model_identity
        # construct schema for updated listened_entities.
        # It is used to check if hyperbase collection schema should update.
        models = {
            model_identity: {}
        }
        er = async_get_entity_registry(self.hass)
        for entity in listened_entities:
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
        
        device_classes = model_domains_map[device_info.model_identity]
        latest_schema = create_schema(device_classes)
        
        # Fetch current collections and schema
        response = await self.hass.async_add_executor_job(self.manager.fetch_collections)
        collections_data = response.get("data", [])
        
        existing_schema = None
        collection_id = None
        collection_name = None
        
        for collection in collections_data:
            # filters only homeassistant collections
            if collection["name"] == f"hass.{device_info.model_identity}":
                existing_schema = collection.get("schema_fields")
                collection_name = collection.get("name")
                collection_id = collection.get("id")
        
        # check for different schema.
        # call update schema API if needed
        missing_columns = set(latest_schema.keys()).difference(existing_schema.keys())
        if len(missing_columns) > 0:
            await self.manager.async_update_collection_task(
                collection_id, {**latest_schema, **existing_schema}, collection_name)
        
        # mutate Task in the runtime task info list
        # idk if it is best practice or not, duhh..
        # if it is working, I ain't touching that anymore
        device_info.listened_entities = listened_entities
        device_info.poll_time_s = poll_time_s
        
        # use returned device_info to cancel and reload runtime task
        # if needed.
        return device_info
    
    
    async def async_reload_task(self, key:str, device: ListenedDeviceInfo):
        self._cancel_runtime_task(key)
        await asyncio.sleep(1) # wait for task cancelation
        self.task_manager.async_load_runtime_tasks([device])
    
    
    def _cancel_runtime_task(self, key: str):
        """Cancel task and clear info from runtime dictionary"""
        tasks = self.task_manager.runtime_tasks
        task_info = self.task_manager.runtime_task_info
        cancel = tasks[key]
        cancel()
        del task_info[key]

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
        for connector_id in tasks.keys():
            task = tasks[connector_id] # terminate all tasks
            task()
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
        self.__updated_collections = set([])

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
            response = await self.hass.async_add_executor_job(self.fetch_collections)
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
                    collection_name = collection.get("name")
                    device_model = collection_name.removeprefix("hass.")
                    self.__collections[device_model] = collection.get("id")

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
                    self.__updated_collections.add(collection.id)
                    # invoke parallel execution of independent tasks to update collection schema
                    self.hass.async_create_task(
                        self.async_update_collection_task(
                            collection.id, latest_schema, collection.name))

    async def async_get_project_collections(self):
        response = None
        try:
            response = await self.hass.async_add_executor_job(self.fetch_collections)
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
    
    async def async_update_collection_task(self, collection_id, schema,
        collection_name: str | None = None):
        await self.hass.async_add_executor_job(
            self.__update_collection_fields, collection_id, schema, collection_name
        )

    
    def get_collection_id(self, model_identity: str):
        return self.collections.get(model_identity)
    
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
                self.__updated_collections.discard(collection_id)
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
                self.__collections[created_collection.removeprefix("hass.")] = created_collection_id
        except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
            raise HyperbaseRESTConnectivityError(exc.args)
        except httpx.HTTPStatusError as exc:
            if not is_success:
                raise HyperbaseHTTPError(exc.response.json()['error']['message'], status_code=exc.response.status_code)
            LOGGER.warning(f"({self.entry.data[CONF_PROJECT_NAME]}) Failed to create new rule for collection {created_collection}. Please add it manually in the Hyperbase.")
        return response


    def fetch_collections(self):
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
    def project_id(self):
        return self.__hyperbase_project_id
    
    @property
    def api_token_id(self):
        return self.entry.data.get(CONF_API_TOKEN)
    
    @property
    def collections(self):
        return self.__collections
    
    @property
    def updated_collections(self):
        return self.__updated_collections



class TaskMetadata:
    def __init__(
        self,
        project_id: str,
        api_token_id: str):
        self.__project_id = project_id
        self.__api_token_id = api_token_id
    
    
    @property
    def project_id(self):
        return self.__project_id
    
    @property
    def api_token_id(self):
        return self.__api_token_id



class Task:
    def __init__(
        self,
        hass: HomeAssistant,
        connector_serial_number: str,
        device_info: ListenedDeviceInfo,
        mqtt_client: MQTT,
        mqtt_topic: str,
        project_manager: HyperbaseProjectManager,
    ):
        self.hass = hass
        self.device_info = device_info
        self._mqttc = mqtt_client
        self.__project_manager = project_manager
        self.__mqtt_topic = mqtt_topic
        self.__connector_serial_number = connector_serial_number
        self.__prev_data = None
        self.__prev_fields = set([])
    
    async def async_publish_on_tick(self, *args):
        if self._mqttc is None:
            return
        er = async_get_entity_registry(self.hass)
        dr = async_get_device_registry(self.hass)
        device_entry = dr.async_get(self.device_info.listened_device)
        
        sent_data = {
            "area_id": device_entry.area_id,
            "connector_entity": self.device_info.hyperbase_entity_id,
            "connector_serial_number": self.__connector_serial_number,
            "name_by_user": device_entry.name_by_user,
            "name_default": device_entry.name,
            "product_id": device_entry.dict_repr["identifiers"][0][1]
        }
        
        _data_exist = False
        
        if self.__prev_data is None:
            self.__prev_data = sent_data
        
        _field_with_data = set([])
        for entity in self.device_info.listened_entities:
            state = self.hass.states.get(entity)
            if state is None or state.state == "unavailable":
                continue
            entity_entry = er.async_get(entity)
            entity_data = parse_entity_data(entity_entry, state.state)
            if entity_data is not None:
                _field_with_data.add(list(entity_data.keys())[0])
                self.__prev_data = {**self.__prev_data, **entity_data}
                _data_exist = True
        
        
        if not _data_exist:
            if self.__prev_data is None:
                return
            else:
                self.__prev_data["status"] = "device unavailable"
        else:
            self.__prev_data["status"] = None
        
        changed_fields = self.__prev_fields.difference(_field_with_data)
        if len(changed_fields) > 0:
            for changed_field in changed_fields:
                self.__prev_data[changed_field] = None # reset value of changed field.
        
        self.__prev_fields = _field_with_data.copy()
        
        
        self.hass.async_create_task(self._mqttc.async_publish(
            self.__mqtt_topic,
            json.json_dumps({
                "project_id": self.__project_manager.project_id,
                "collection_id": self.__project_manager.get_collection_id(self.device_info.model_identity),
                "token_id": self.__project_manager.api_token_id,
                "data": self.__prev_data,
            }),
            qos=0,
            retain=False,
            ))
        
        self.hass.states.async_set(
            self.device_info.hyperbase_entity_id,
            new_state=datetime.datetime.now(),
            attributes={
                "listened_device": self.device_info.listened_device,
                "listened_entities": self.device_info.listened_entities,
                "poll_time_s": self.device_info.poll_time_s,
                "model_identity": self.device_info.model_identity,
                },
            timestamp=datetime.datetime.now().timestamp()
        )
    
    
    async def async_publish_reload_status(self):
        if self._mqttc is None:
            return
        er = async_get_entity_registry(self.hass)
        dr = async_get_device_registry(self.hass)
        device_entry = dr.async_get(self.device_info.listened_device)
        
        sent_data = {
            "area_id": device_entry.area_id,
            "connector_entity": self.device_info.hyperbase_entity_id,
            "connector_serial_number": self.__connector_serial_number,
            "name_by_user": device_entry.name_by_user,
            "name_default": device_entry.name,
            "product_id": device_entry.dict_repr["identifiers"][0][1],
            "status": "reloaded"
        }
        
        for entity in self.device_info.listened_entities:
            state = self.hass.states.get(entity)
            if state is None or state.state == "unavailable":
                continue
            entity_entry = er.async_get(entity)
            entity_data = parse_entity_data(entity_entry, state.state)
            if entity_data is not None:
                sent_data = {**sent_data, **entity_data}
        
        self.hass.async_create_task(self._mqttc.async_publish(
            self.__mqtt_topic,
            json.json_dumps({
                "project_id": self.__project_manager.project_id,
                "collection_id": self.__project_manager.get_collection_id(self.device_info.model_identity),
                "token_id": self.__project_manager.api_token_id,
                "data": sent_data,
            }),
            qos=0,
            retain=False,
            ))
        
        self.hass.states.async_set(
            self.device_info.hyperbase_entity_id,
            new_state=datetime.datetime.now(),
            attributes={
                "listened_device": self.device_info.listened_device,
                "listened_entities": self.device_info.listened_entities,
                "poll_time_s": self.device_info.poll_time_s,
                "model_identity": self.device_info.model_identity,
                },
            timestamp=datetime.datetime.now().timestamp()
        )



class HyperbaseTaskManager:
    def __init__(self,
        hass: HomeAssistant,
        connector_serial_number: str,
        mqttc: MQTT,
        mqtt_topic: str,
        project_manager: HyperbaseProjectManager,
        ):
        
        self.hass = hass
        self.__mqttc = mqttc
        self.__runtime_tasks: dict[str, Any] = {}
        self.__runtime_task_info: dict[str, Task] = {}
        self.__project_manager = project_manager
        self.__mqtt_topic = mqtt_topic
        self.__connector_serial_number = connector_serial_number

    async def async_load_runtime_tasks(self, listened_devices: list[ListenedDeviceInfo]):
        for device in listened_devices:
            self.hass.async_create_task(self.__poll_entity_state(device))


    async def __poll_entity_state(self, device: ListenedDeviceInfo):
        # at least one valueable is available to create new task
        _flag = False
        
        while True:
            
            # cancel work if integration is unloaded
            if self.__mqttc is None:
                return
            
            collection_id = self.__project_manager.get_collection_id(device.model_identity)

            # wait until corresponding collection ID registered into runtime first
            if collection_id is None:
                continue
            
            # wait until corresponding collection ID schema updated
            if self.__project_manager.updated_collections.issuperset([collection_id]):
                continue
            
            # ensure at least one entity is ready to be collected
            for entity in device.listened_entities:
                state = self.hass.states.get(entity)
                if state is None or state.state == "unavailable":
                    await asyncio.sleep(5) # sleep to spare time for states loading
                    continue
                _flag = True
            
            if _flag:
                break
        
        task = Task(
                hass=self.hass,
                connector_serial_number=self.__connector_serial_number,
                device_info=device,
                mqtt_client=self.__mqttc,
                mqtt_topic=self.__mqtt_topic,
                project_manager=self.__project_manager,
            )
        self.__runtime_task_info[device.hyperbase_entity_id] = task
        
        await task.async_publish_reload_status()
        
        self.__runtime_tasks[device.hyperbase_entity_id] = async_track_time_interval(self.hass,
                task.async_publish_on_tick,
                interval=timedelta(seconds=device.poll_time_s)
            )
    
    def get_device_info_by_entity(self, connector_entity: str) -> ListenedDeviceInfo | None:
        if self.__runtime_task_info.get(connector_entity) is None:
            return None
        return self.__runtime_task_info.get(connector_entity).device_info


    @property
    def runtime_tasks(self):
        return self.__runtime_tasks
    
    @property
    def runtime_task_info(self):
        return self.__runtime_task_info