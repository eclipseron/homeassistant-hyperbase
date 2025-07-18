import asyncio
from datetime import timedelta
import datetime
import json
from typing import Any
from zoneinfo import ZoneInfo

import httpx


from .models import DomainDeviceClass, create_schema, parse_entity_data
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EVENT_HOMEASSISTANT_STOP

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from .const import (
    CONF_PROJECT_NAME,
    DOMAIN,
    CONF_BASE_URL,
    LOGGER,
)
from .exceptions import HyperbaseRESTConnectionError
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.httpx_client import get_async_client
from .registry import HyperbaseConnectorEntry, async_get_hyperbase_registry


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

class HyperbaseCoordinator:
    
    def __init__(
        self,
        hass: HomeAssistant,
        device_id: str,
        hyperbase_project_id: str,
        hyperbase_project_name: str,
        serial_number: str,
    ):
        """Initialize."""
        self.hass = hass
        self.hyperbase_device_id = device_id
        self.unloading = False
        self.__project_name = hyperbase_project_name
        
        self.__connectors: list[HyperbaseConnectorEntry] = []
        
        self.manager = HyperbaseProjectManager(
            hass,
            hyperbase_project_id,
        )
        
        self.task_manager = HyperbaseTaskManager(
            hass,
            connector_serial_number=serial_number,
            project_manager=self.manager,
        )


    async def async_startup(self):
        await self.reload_listened_devices()
        model_domains_map = await self.__async_verify_device_models()
        LOGGER.info(f"({self.__project_name}) Startup: Listened devices loaded")
        succeed = await self.manager.async_revalidate_collections(model_domains_map)
        if not succeed:
            return False
        
        LOGGER.info(f"({self.__project_name}) Startup: Hyperbase collections revalidated")
        if self.hass.is_running:
            await self.__async_startup_load_runtime_tasks()
        else:
            LOGGER.info(f"({self.__project_name}) Startup: Waiting for Home Assistant to start before loading runtime tasks")
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, self.__async_startup_load_runtime_tasks)
        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.disconnect)
        return True

    
    async def __async_startup_load_runtime_tasks(self, _=None):
        await self.task_manager.async_load_runtime_tasks(self.__connectors)
        LOGGER.info(f"({self.__project_name}) Running: Data logging is active. Please check your hyperbase instance to verify.")

    async def reload_listened_devices(self) -> list[HyperbaseConnectorEntry]:
        """Reload listened devices and return updated list of HyperbaseConnectorEntry to be used later"""
        self.__connectors = []
        
        hyp = await async_get_hyperbase_registry(self.hass)
        _conn = hyp.get_connector_entries_for_project(self.manager.project_id)
        self.__connectors = _conn.copy()

        return self.__connectors


    async def async_add_new_listened_device(self, connector: HyperbaseConnectorEntry):
        """
        Add new listened device into the runtime.
        """
        self.__connectors.append(connector)
        if connector._collection_name is None:
            raise Exception("device model identity is not exist")
        model_identity = connector._collection_name
        models = {
            model_identity: {}
        }
        er = async_get_entity_registry(self.hass)
        for entity in connector._listened_entities:
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
        
        await self.manager.async_revalidate_collections(model_domains_map, await_result=True)
        await self.task_manager.async_load_runtime_tasks([connector]) # register new device into runtime task


    async def async_update_listened_entities(self,
        connector_entity: str,
        listened_entities: list[str],
        poll_time_s: int
        ) -> HyperbaseConnectorEntry:
        
        connector = self.task_manager.get_active_connector_by_id(connector_entity)
        model_identity = connector._collection_name
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
                continue
            
            if entity_entry.translation_key is not None:
                models[model_identity][entity_entry.domain].add(entity_entry.translation_key)
        
        model_domains_map: dict[str, list[DomainDeviceClass]] = {
            model_identity: []
        }
        
        for domain in models[model_identity].keys():
            domain_class = DomainDeviceClass(
                domain,
                list(models[model_identity][domain])
            )
            model_domains_map[model_identity].append(domain_class)
        
        device_classes = model_domains_map[connector._collection_name]
        latest_schema = create_schema(device_classes)
        
        # Fetch current collections and schema
        response = await self.hass.async_add_executor_job(self.manager.fetch_collections)
        collections_data = response.get("data", [])
        
        existing_schema = None
        collection_id = None
        collection_name = None
        
        for collection in collections_data:
            # filters only homeassistant collections
            if collection["name"] == f"hass.{connector._collection_name}":
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
        connector._listened_entities = listened_entities
        connector._poll_time_s = poll_time_s
        
        # use returned device_info to cancel and reload runtime task
        # if needed.
        return connector


    async def async_reload_task(self, connector: HyperbaseConnectorEntry):
        self._cancel_runtime_task(connector._connector_entity_id)
        await asyncio.sleep(1) # wait for task cancelation
        await self.task_manager.async_load_runtime_tasks([connector])


    def _cancel_runtime_task(self, key: str):
        """Cancel task and clear info from runtime dictionary"""
        tasks = self.task_manager.runtime_tasks
        task_info = self.task_manager.runtime_task_info
        
        self.task_manager.cancel_waiting_tasks(key)
        cancel = tasks[key]
        cancel() # terminate all tasks
        if task_info.get(key) is not None:
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
        for connector in self.__connectors:
            model_identity = connector._collection_name
            
            if models.get(model_identity, None) is None:
                models[model_identity] = {}
            
            for listened_entity in connector._listened_entities:
                entity = er.async_get(listened_entity)
                if models[model_identity].get(entity.domain, None) is None:
                    models[model_identity][entity.domain] = set([])
                
                if entity.original_device_class is not None:
                    models[model_identity][entity.domain].add(entity.original_device_class)
                    continue
                
                if entity.translation_key is not None:
                    models[model_identity][entity.domain].add(entity.translation_key)
        
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


    async def disconnect(self, _=None):
        """Disonnects to MQTT Broker"""
        self.unloading = True
        tasks = self.task_manager.runtime_tasks
        for connector_id in tasks.keys():
            self._cancel_runtime_task(connector_id)
        
        # cancel retry task
        self.task_manager.cancel_retry_tasks()

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
        self.__base_url = self.entry.data.get(CONF_BASE_URL)
        self.__auth_token = self.entry.data.get("auth_token")


    async def async_revalidate_collections(self, model_mapping:dict[str, list[DomainDeviceClass]], await_result: bool = False):
        """Revalidate hyperbase collections.
        
        Collections are named as follows `hass.<manufacturer> <model identity>`
        where model identity is the type one of model name, model ID,
        device name by user, or device default name.
        If the collection does not exist, it will be created.
        
        Example: `hass.Tuya Wifi Smart Plug`
        """
        response = None
        response = await self.hass.async_add_executor_job(self.fetch_collections)
        if response is None:
            return False
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
                
                if not await_result:
                    # invoke near-parallel execution of independent tasks to create new collections
                    self.hass.async_create_task(self.__async_create_collection_task(model_name, schema_fields))
                else:
                    # this way used for updated collection while hyperbase connection is running
                    await self.__async_create_collection_task(model_name, schema_fields)
                
            for collection in collections:
                if model_mapping.get(collection.name.removeprefix("hass."), None) is None:
                    continue
                device_classes = model_mapping[collection.name.removeprefix("hass.")]
                latest_schema = create_schema(device_classes)
                existing_schema = collection.schema_fields
                missing_columns = set(latest_schema.keys()).difference(existing_schema)
                if len(missing_columns) > 0:
                    # invoke parallel execution of independent tasks to update collection schema
                    if not await_result:
                        self.hass.async_create_task(
                            self.async_update_collection_task(
                                collection.id, latest_schema, collection.name))
                    else:
                        # this way used for updated collection while hyperbase connection is running
                        await self.async_update_collection_task(
                                collection.id, latest_schema, collection.name)
            return True


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
            with httpx.Client(headers=headers, verify=False) as session:
                response = session.patch(f"{base_url}/api/rest/project/{self.__hyperbase_project_id}/collection/{collection_id}",
                        json={
                            "schema_fields": schema,
                        },
                        timeout=httpx.Timeout(10, connect=5, read=20, write=5)
                    )
                response.raise_for_status()
                LOGGER.info(f"({self.entry.data[CONF_PROJECT_NAME]}) schema updated for collection: {collection_name}")
            return response
        except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Hyperbase connection failed: {exc}")
        except httpx.HTTPStatusError as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Failed to fetch collections: {exc}")
        except json.decoder.JSONDecodeError as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Unknown response from server. JSON decode error")
        except Exception as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Unknown error on collection {collection_id}: {exc}")


    def __create_collection(self, entity_domain, schema):
        headers = {
                "Authorization": f"Bearer {self.entry.data["auth_token"]}",
            }
        response = None
        base_url = self.entry.data[CONF_BASE_URL]
        created_collection: str = ""
        try:
            with httpx.Client(headers=headers, verify=False) as session:
                response = session.post(f"{base_url}/api/rest/project/{self.__hyperbase_project_id}/collection",
                        json={
                            "name": "hass." + entity_domain,
                            "schema_fields": schema,
                            "opt_auth_column_id": False
                        },
                        timeout=httpx.Timeout(10, connect=5, read=20, write=5)
                    )
                response.raise_for_status()
                
                result = response.json()
                data = result.get("data")
                created_collection = data.get("name")
                created_collection_id = data.get("id")
                LOGGER.info(f"({self.entry.data[CONF_PROJECT_NAME]}) create new collection: hass.{entity_domain}")
                self.__collections[created_collection.removeprefix("hass.")] = created_collection_id
            
            return response
        except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Hyperbase connection failed: {exc}")
        except httpx.HTTPStatusError as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Failed to fetch collections: {exc}")
        except json.decoder.JSONDecodeError as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Unknown response from server. JSON decode error")
        except Exception as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Unknown error: {exc}")

    def fetch_collections(self):
        """
        Create a GET request to Hyperbase REST API to get list of existing collections within the project.
        This is a blocking process and must be executed by sync worker.
        """
        try:
            with httpx.Client(verify=False) as client:
                if not self.entry.data["auth_token"]:
                    raise HyperbaseRESTConnectionError("Token not found", 401)
                client.headers.update({
                    "Authorization": f"Bearer {self.entry.data["auth_token"]}",
                })
                client.base_url = self.entry.data[CONF_BASE_URL]
                result = client.get(f"/api/rest/project/{self.__hyperbase_project_id}/collections",
                    timeout=httpx.Timeout(10, connect=5, read=20, write=5))
                result.raise_for_status()
                
                return result.json()
        except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Hyperbase connection failed: {exc}")
        except httpx.HTTPStatusError as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Failed to fetch collections: {exc}")
        except json.decoder.JSONDecodeError as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Unknown response from server. JSON decode error")
        except Exception as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Unknown error: {exc}")

    @property
    def project_id(self):
        return self.__hyperbase_project_id
    
    @property
    def collections(self):
        return self.__collections
    
    @property
    def base_url(self):
        return self.__base_url
    
    @property
    def auth_token(self):
        return self.__auth_token



class Task:
    def __init__(
        self,
        hass: HomeAssistant,
        auth_token: str,
        base_url: str,
        collection_id: str,
        collection_name: str,
        connector: HyperbaseConnectorEntry,
        connector_serial_number: str,
        project_id: str,
        project_name: str,
        cancel_callback,
        retry_callback,
    ):
        self.hass = hass
        self.connector = connector
        self.__connector_serial_number = connector_serial_number
        self.__prev_data = None
        self.__prev_fields = set([])
        self.__project_id = project_id
        self.__auth_token = auth_token
        self.__base_url = base_url
        self.__project_name = project_name
        self.__collection_name = collection_name
        self.__collection_id = collection_id
        self.cancel_callback = cancel_callback
        self.retry_callback =retry_callback


    async def async_publish_on_tick(self, *args):
        er = async_get_entity_registry(self.hass)
        dr = async_get_device_registry(self.hass)
        device_entry = dr.async_get(self.connector._listened_device.id)
        if device_entry is None:
            return
        
        sent_data = {
            "area_id": device_entry.area_id,
            "connector_entity": self.connector._connector_entity_id,
            "connector_serial_number": self.__connector_serial_number,
            "name_by_user": device_entry.name_by_user,
            "name_default": device_entry.name,
            "product_id": device_entry.dict_repr["identifiers"][0][1],
        }
        
        _data_exist = False
        
        if self.__prev_data is None:
            self.__prev_data = sent_data
        
        _field_with_data = set([])
        for entity in self.connector._listened_entities:
            state = self.hass.states.get(entity)
            if state is None or state.state == "unavailable":
                continue
            entity_entry = er.async_get(entity)
            entity_data = parse_entity_data(entity_entry, state)
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
                del self.__prev_data[changed_field]
        
        self.__prev_fields = _field_with_data.copy()
        
        self.__prev_data["record_date"] = datetime.datetime.now(tz=ZoneInfo("UTC")).isoformat()
        task = self.hass.async_create_task(self.async_post_data(
            self.__prev_data,
        ))
        
        # append post task to callback. invoked when shutting down if post task still running
        self.cancel_callback(self.connector._connector_entity_id, task)


    async def async_publish_reload_status(self):
        """
        Publish reload status to Hyperbase collection as first sent data.
        This is used to notify that the device is reloaded and ready to collect data.
        """
        er = async_get_entity_registry(self.hass)
        dr = async_get_device_registry(self.hass)
        device_entry = dr.async_get(self.connector._listened_device.id)
        if device_entry is None:
            return
        
        sent_data = {
            "area_id": device_entry.area_id,
            "connector_entity": self.connector._connector_entity_id,
            "connector_serial_number": self.__connector_serial_number,
            "name_by_user": device_entry.name_by_user,
            "name_default": device_entry.name,
            "product_id": device_entry.dict_repr["identifiers"][0][1],
            "status": "reloaded",
            "record_date": datetime.datetime.now(tz=ZoneInfo("UTC")).isoformat()
        }
        
        for entity in self.connector._listened_entities:
            state = self.hass.states.get(entity)
            if state is None or state.state == "unavailable":
                continue
            entity_entry = er.async_get(entity)
            entity_data = parse_entity_data(entity_entry, state)
            if entity_data is not None:
                sent_data = {**sent_data, **entity_data}
        
        task = self.hass.async_create_task(self.async_post_data(
            sent_data,
        ))
        
        # append post task to callback. invoked when shutting down if post task still running
        self.cancel_callback(self.connector._connector_entity_id, task)


    async def async_post_data(self, payload: dict):
        """Post data to Hyperbase collection."""
        headers = {
            "Authorization": f"Bearer {self.__auth_token}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "Connection": "close",
        }
        
        backup = {
            "collection_id": self.__collection_id,
            "collection_name": self.__collection_name,
            "payload": payload.copy()
        }
        
        try:
            session = get_async_client(self.hass, verify_ssl=False)
            response = await session.post(
                f"{self.__base_url}/api/rest/project/{self.__project_id}/collection/{self.__collection_id}/record",
                json=payload,
                headers=headers,
                timeout=httpx.Timeout(10, connect=5, read=20, write=5)
            )
            response.raise_for_status()
            self.hass.states.async_set(
                self.connector._connector_entity_id,
                new_state=datetime.datetime.now(),
                attributes={
                    "listened_device": self.connector._listened_device.id,
                    "listened_entities": self.connector._listened_entities,
                    "poll_time_s": self.connector._poll_time_s,
                    "model_identity": self.__collection_name,
                    },
                timestamp=datetime.datetime.now().timestamp()
            )
        except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
            LOGGER.error(f"({self.__project_name}) Hyperbase connection failed on collection {self.__collection_name}: {exc}")
            self.retry_callback(backup)
        
        except httpx.HTTPStatusError as exc:
            LOGGER.error(f"({self.__project_name}) Failed to store data into collection {self.__collection_name}: {exc}")
            LOGGER.info(exc.response.json())
            self.retry_callback(backup)
        
        except httpx.RemoteProtocolError as exc:
            LOGGER.warning(f"({self.__project_name}) Response malformed on hyperbase. Please check your data in collection {self.__collection_name}: {exc}")



class HyperbaseTaskManager:
    def __init__(self,
        hass: HomeAssistant,
        connector_serial_number: str,
        project_manager: HyperbaseProjectManager,
        ):
        
        self.hass = hass
        self.__runtime_tasks: dict[str, Any] = {}
        self.__runtime_task_info: dict[str, Task] = {}
        self.__project_manager = project_manager
        self.__connector_serial_number = connector_serial_number
        self.__waiting_tasks: dict[str, list[Any]] = {}
        self.__failed_tasks: list[dict[str, Any]] = []
        self.__retry_tasks = []
        self.__retry_tracker = None


    async def async_load_runtime_tasks(self, connectors: list[HyperbaseConnectorEntry]):
        for connector in connectors:
            self.hass.async_create_task(self.__poll_entity_state(connector))


    async def __poll_entity_state(self, connector: HyperbaseConnectorEntry):
        task = Task(
                hass=self.hass,
                auth_token=self.__project_manager.auth_token,
                base_url=self.__project_manager.base_url,
                collection_id=self.__project_manager.get_collection_id(connector._collection_name),
                collection_name=connector._collection_name,
                connector=connector,
                connector_serial_number=self.__connector_serial_number,
                project_id=self.__project_manager.project_id,
                project_name=self.__project_manager.entry.data[CONF_PROJECT_NAME],
                cancel_callback=self._append_waiting_tasks_callback,
                retry_callback=self._append_retry_tasks_callback
            )
        self.__runtime_task_info[connector._connector_entity_id] = task
        
        await task.async_publish_reload_status()
        
        self.__runtime_tasks[connector._connector_entity_id] = async_track_time_interval(self.hass,
                task.async_publish_on_tick,
                interval=timedelta(seconds=connector._poll_time_s),
                cancel_on_shutdown=True,
            )
        
        self.__retry_tracker = async_track_time_interval(self.hass,
                self.async_create_retry_task,
                interval=timedelta(seconds=20),
                cancel_on_shutdown=True
            )


    def get_active_connector_by_id(self, connector_entity: str) -> HyperbaseConnectorEntry | None:
        if self.__runtime_task_info.get(connector_entity) is None:
            return None
        return self.__runtime_task_info.get(connector_entity).connector


    def _append_waiting_tasks_callback(self, connector_id: str, task):
        if self.__waiting_tasks.get(connector_id) is None:
            self.__waiting_tasks[connector_id] = []
        self.__waiting_tasks[connector_id].append(task)


    def _append_retry_tasks_callback(self, failed_data: dict):
        self.__failed_tasks.append(failed_data)


    def cancel_waiting_tasks(self, connector_id):
        for task in self.__waiting_tasks.get(connector_id):
            task.cancel()

    
    def cancel_retry_tasks(self):
        for task in self.__retry_tasks:
            task.cancel()
        if self.__retry_tracker is not None:
            self.__retry_tracker()

    async def async_create_retry_task(self, _=None):
        if len(self.__failed_tasks) < 1:
            return
        LOGGER.warning(f"({self.__project_manager.entry.data[CONF_PROJECT_NAME]}) Found {len(self.__failed_tasks)} failed data loggings. Scheduling for retry.")
        for failed in self.__failed_tasks:
            task = self.hass.async_create_task(self.async_retry_post_data(failed))
            self.__retry_tasks.append(task)
        
        self.__failed_tasks.clear()
    
    
    async def async_retry_post_data(self, failed_data):
        """Post data to Hyperbase collection."""
        collection_id = failed_data.get("collection_id")
        collection_name = failed_data.get("collection_name")
        project_name = self.__project_manager.entry.data[CONF_PROJECT_NAME]
        data = failed_data.get("payload")
        
        headers = {
            "Authorization": f"Bearer {self.__project_manager.auth_token}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "Connection": "close",
        }
        
        try:
            session = get_async_client(self.hass, verify_ssl=False)
            response = await session.post(
                f"{self.__base_url}/api/rest/project/{self.__project_manager.project_id}/collection/{collection_id}/record",
                json=data,
                headers=headers,
                timeout=httpx.Timeout(10, connect=5, read=20, write=5)
            )
            response.raise_for_status()
        except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
            LOGGER.error(f"({project_name}) Hyperbase connection failed on collection {collection_name}: {exc}")
            self.__failed_tasks.append(failed_data)
        
        except httpx.HTTPStatusError as exc:
            LOGGER.error(f"({project_name}) Failed to store data into collection {collection_name}: {exc}")
            self.__failed_tasks.append(failed_data)
        
        except httpx.RemoteProtocolError as exc:
            LOGGER.warning(f"({project_name}) Response malformed on hyperbase. Please check your data in collection {collection_name}: {exc}")
    
    
    @property
    def runtime_tasks(self):
        return self.__runtime_tasks

    @property
    def runtime_task_info(self):
        return self.__runtime_task_info