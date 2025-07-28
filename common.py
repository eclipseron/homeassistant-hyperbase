import asyncio
from datetime import timedelta, datetime
from io import BytesIO
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from config.custom_components.hyperbase.recorder import SnapshotRecorder


from .models import DomainDeviceClass, create_schema, parse_entity_data
from homeassistant.const import CONF_API_TOKEN, EVENT_HOMEASSISTANT_STARTED, EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers import json
from homeassistant.util.json import json_loads

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from .mqtt import MQTT
from .const import (
    CONF_PROJECT_NAME,
    DOMAIN,
    CONF_BASE_URL,
    LOGGER,
)
from .exceptions import HyperbaseMQTTConnectionError, HyperbaseRESTConnectionError
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from .registry import HyperbaseConnectorEntry, async_get_hyperbase_registry
from homeassistant.helpers.httpx_client import get_async_client



class HyperbaseCoordinator:
    def __init__(
        self,
        hass: HomeAssistant,
        bucket_id: str,
        device_id: str,
        hyperbase_mqtt_host: str,
        hyperbase_mqtt_port: int,
        hyperbase_mqtt_topic: str,
        hyperbase_project_id: str,
        hyperbase_project_name: str,
        user_id: str,
        user_collection_id: str,
    ):
        """Initialize."""
        self.hass = hass
        self.hyperbase_device_id = device_id
        self.unloading = False
        self._project_name = hyperbase_project_name
        
        self._connectors: list[HyperbaseConnectorEntry] = []
        
        self.manager = HyperbaseProjectManager(
            hass,
            hyperbase_project_id,
            bucket_id,
        )
        
        self.mqtt_client = MQTT(
            hass,
            hyperbase_mqtt_host,
            hyperbase_mqtt_port,
        )
        
        self.task_manager = HyperbaseTaskManager(
            hass,
            mqttc = self.mqtt_client,
            mqtt_topic=hyperbase_mqtt_topic,
            project_manager=self.manager,
            user_id=user_id,
            user_collection_id=user_collection_id
        )


    async def async_startup(self):
        await self.reload_listened_devices()
        model_domains_map = await self.__async_verify_device_models()
        LOGGER.info(f"({self._project_name}) Startup: Listened devices loaded")
        succeed = await self.manager.async_revalidate_collections(model_domains_map)
        if not succeed:
            return False
        
        LOGGER.info(f"({self._project_name}) Startup: Hyperbase collections revalidated")
        await self.connect()
        if self.hass.is_running:
            await self.__async_startup_load_runtime_tasks()
        else:
            LOGGER.info(f"({self._project_name}) Startup: Waiting for Home Assistant to start before loading runtime tasks")
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, self.__async_startup_load_runtime_tasks)
        
        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.disconnect)
        return True
    
    
    async def __async_startup_load_runtime_tasks(self, _=None):
        await self.task_manager.async_load_runtime_tasks(self._connectors)
        LOGGER.info(f"({self._project_name}) Running: Data logging is active. Please check your hyperbase instance to verify.")
    
    
    async def reload_listened_devices(self) -> list[HyperbaseConnectorEntry]:
        """Reload listened devices and return updated list of HyperbaseConnectorEntry to be used later"""
        self._connectors = []
        
        hyp = await async_get_hyperbase_registry(self.hass)
        _conn = hyp.get_connector_entries_for_project(self.manager.project_id)
        self._connectors = _conn.copy()

        return self._connectors


    async def async_add_new_listened_device(self, connector: HyperbaseConnectorEntry):
        """
        Add new listened device into the runtime.
        """
        self._connectors.append(connector)
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
                continue
            
            if entity_entry.translation_key is not None:
                models[model_identity][entity_entry.domain].add(entity_entry.translation_key)
                continue
            
            else:
                models[model_identity][entity_entry.domain].add("unknown")
        
        
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
        ):
        
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
                continue
            
            else:
                models[model_identity][entity_entry.domain].add("unknown")
        
        model_domains_map: dict[str, list[DomainDeviceClass]] = {
            model_identity: []
        }
        
        for domain in models[model_identity].keys():
            domain_class = DomainDeviceClass(
                domain,
                list(models[model_identity][domain])
            )
            model_domains_map[model_identity].append(domain_class)
        
        device_classes = model_domains_map.get(model_identity)
        latest_schema = create_schema(device_classes)
        
        # Fetch current collections and schema
        response = await self.hass.async_add_executor_job(self.manager.fetch_collections)
        collections_data = response.get("data", [])
        
        existing_schema = None
        collection_id = None
        collection_name = None
        
        for collection in collections_data:
            # filters only homeassistant collections
            if collection["name"] == f"hass.{model_identity}":
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
        
        # use returned conenector to cancel and reload runtime task
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
        
        # self.task_manager.cancel_waiting_tasks(key)
        cancel = tasks.get(key)
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
        for connector in self._connectors:
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
                    continue
                
                else:
                    models[model_identity][entity.domain].add("unknown")
        
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


    async def connect(self):
        """Connects to MQTT Broker"""
        try:
            _ = await self.mqtt_client.async_connect()
            LOGGER.info(f"({self._project_name}) MQTT connection established")
        except HyperbaseMQTTConnectionError as exc:
            LOGGER.error(f"({self._project_name}) MQTT connection failed: {exc}")


    async def disconnect(self, _=None):
        """Disonnects to MQTT Broker"""
        self.unloading = True
        await self.mqtt_client.async_disconnect()
        tasks = self.task_manager.runtime_tasks
        for connector_id in tasks.keys():
            task = tasks[connector_id] # terminate all tasks
            task()


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
        bucket_id: str
    ):
        """Initialize Hyperbase project manager."""
        self.hass = hass
        self.__hyperbase_project_id = hyperbase_project_id
        self._hyperbase_bucket_id = bucket_id
        self.entry = self.hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, self.__hyperbase_project_id)
        self.__collections = {}
        self.__updated_collections = set([])

    async def async_revalidate_collections(self, model_mapping:dict[str, list[DomainDeviceClass]], await_result: bool = False):
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
    
    
    def get_collection_ids(self):
        collections_ids = [self.collections.get(collection_name) for collection_name in self.collections.keys()]
        return collections_ids
    
    
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
                self.__updated_collections.discard(collection_id)
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
        api_token_id = self.entry.data.get(CONF_API_TOKEN)
        
        is_success = False
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
                        },
                        timeout=httpx.Timeout(10, connect=5, read=20, write=5),
                    )
                response.raise_for_status()
                self.__collections[created_collection.removeprefix("hass.")] = created_collection_id
        except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Hyperbase connection failed: {exc}")
        except httpx.HTTPStatusError as exc:
            if not is_success:
                LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Failed to create collection: {exc}")
                return
            LOGGER.warning(f"({self.entry.data[CONF_PROJECT_NAME]}) Failed to create new rule for collection {created_collection}. Please add it manually in the Hyperbase.")
        except Exception as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Unknown error: {exc}")
    
    
    async def async_create_bucket_object(self, payload: dict):
        headers = {
                "Authorization": f"Bearer {self.entry.data["auth_token"]}",
            }
        json_string = json.json_dumps(payload)
        json_bytes = json_string.encode("utf-8")
        
        file = BytesIO(json_bytes)
        file_name = f"HA{datetime.now().strftime("%Y%M%d_%H%m%s")}.json"
        files = {"file": (file_name, file, "application/json")}
        base_url = self.entry.data[CONF_BASE_URL]
        try:
            session = get_async_client(self.hass)
            response = await session.post(f"{base_url}/api/rest/project/{self.__hyperbase_project_id}/bucket/{self._hyperbase_bucket_id}/file",
                    files=files,
                    data = {"file_name": file_name},
                    timeout=httpx.Timeout(10, connect=5, read=20, write=5),
                    headers=headers
                )
            response.raise_for_status()
            LOGGER.info(f"({self.entry.data[CONF_PROJECT_NAME]}) Inconsistent data stored.")
        except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Hyperbase connection failed: {exc}")
        except httpx.HTTPStatusError as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Failed to store retry log.")
        except Exception as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Unknown error: {exc}")
    
    
    async def async_fetch_csv_data(self, collection_id, start_time, end_time):
        try:
            client = get_async_client(self.hass, verify_ssl=False)
            
            headers = {
                "Authorization": f"Bearer {self.entry.data["auth_token"]}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            
            query = {
                "orders": [
                    {"field": "connector_entity", "kind": "asc"},
                    {"field": "record_date", "kind": "asc"},
                ],
                "filters": [{
                    "op": "AND",
                    "children": [
                        {"field": "record_date", "op": ">=", "value": start_time},
                        {"field": "record_date", "op": "<=", "value": end_time},
                    ]
                }]
            }
            if not self.entry.data["auth_token"]:
                raise HyperbaseRESTConnectionError("Token not found", 401)
            
            client.base_url = self.entry.data[CONF_BASE_URL]
            LOGGER.info(query)
            result = await client.post(f"/api/rest/project/{self.__hyperbase_project_id}/collection/{collection_id}/records",
                headers=headers,
                timeout=httpx.Timeout(10, connect=5, read=20, write=5),
                json=query)
            result.raise_for_status()
            return {
                "success": True,
                "data": result.json().get("data"),
                "count": result.json().get("pagination").get("total")
            }
        except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Hyperbase connection failed: {exc}")
            return {"success": False}
        except httpx.HTTPStatusError as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Failed to fetch collections: {exc}")
            return {"success": False}
        except Exception as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Unknown error: {exc}")
            return {"success": False}
    
    
    async def async_fetch_records_consistency(self, collection_id, start_time, end_time):
        try:
            client = get_async_client(self.hass, verify_ssl=False)
            
            headers = {
                "Authorization": f"Bearer {self.entry.data["auth_token"]}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            
            query = {
                "fields": ["record_date", "connector_entity"],
                "orders": [
                    {"field": "connector_entity", "kind": "asc"},
                    {"field": "record_date", "kind": "asc"},
                ],
                "filters": [{
                    "op": "AND",
                    "children": [
                        {"field": "record_date", "op": ">=", "value": start_time},
                        {"field": "record_date", "op": "<", "value": end_time},
                    ]
                }]
            }
            if not self.entry.data["auth_token"]:
                raise HyperbaseRESTConnectionError("Token not found", 401)
            
            client.base_url = self.entry.data[CONF_BASE_URL]
            result = await client.post(f"/api/rest/project/{self.__hyperbase_project_id}/collection/{collection_id}/records",
                headers=headers,
                timeout=httpx.Timeout(10, connect=5, read=20, write=5),
                json=query)
            result.raise_for_status()
            
            return {
                "success": True,
                "data": result.json().get("data"),
                "count": result.json().get("pagination").get("total")
            }
        except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Hyperbase connection failed: {exc}")
            return {"success": False}
        except httpx.HTTPStatusError as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Failed to fetch collections: {exc}")
            return {"success": False}
        except Exception as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Unknown error: {exc}")
            return {"success": False}


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
        except Exception as exc:
            LOGGER.error(f"({self.entry.data[CONF_PROJECT_NAME]}) Unknown error: {exc}")

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
        api_token_id: str,
        collection_id: str,
        collection_name: str,
        connector: HyperbaseConnectorEntry,
        mqtt_client: MQTT,
        mqtt_topic: str,
        project_id: str,
        project_name: str,
        user_id: str,
        user_collection_id: str,
        callbacks: dict[str, Any] = None,
    ):
        self.hass = hass
        self.connector = connector
        self._mqttc = mqtt_client
        self._mqtt_topic = mqtt_topic
        self.__prev_data = None
        self.__prev_fields = set([])
        self.__project_id = project_id
        self.__project_name = project_name
        self.__collection_name = collection_name
        self.__collection_id = collection_id
        self.__api_token_id = api_token_id
        self._user_id = user_id
        self._user_collection_id = user_collection_id
        
        self.snapshot_buffer = callbacks.get("snapshot_buffer")
    
    
    async def async_publish_on_tick(self, current_time: datetime):
        er = async_get_entity_registry(self.hass)
        dr = async_get_device_registry(self.hass)
        device_entry = dr.async_get(self.connector._listened_device.id)
        if device_entry is None:
            return
        
        _data_exist = False
        
        if self.__prev_data is None:
            self.__prev_data = {}
        
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
                self.__prev_data[changed_field] = None # reset value of changed field.
        
        product_id = device_entry.id
        if len(device_entry.dict_repr.get("identifiers")) > 0:
            product_id = device_entry.dict_repr["identifiers"][0][1]
        
        self.__prev_fields = _field_with_data.copy()
        self.__prev_data["record_date"] = current_time.isoformat()
        self.__prev_data["area_id"] = device_entry.area_id
        self.__prev_data["connector_entity"] = self.connector._connector_entity_id
        self.__prev_data["name_by_user"] = device_entry.name_by_user
        self.__prev_data["name_default"] = device_entry.name
        self.__prev_data["product_id"] = product_id
        
        self.hass.async_create_task(self.async_post_data(
            self.__prev_data,
        ))
    
    
    async def async_publish_reload_status(self):
        er = async_get_entity_registry(self.hass)
        dr = async_get_device_registry(self.hass)
        device_entry = dr.async_get(self.connector._listened_device.id)
        
        product_id = device_entry.id
        if len(device_entry.dict_repr.get("identifiers")) > 0:
            product_id = device_entry.dict_repr["identifiers"][0][1]
        
        sent_data = {
            "area_id": device_entry.area_id,
            "connector_entity": self.connector._connector_entity_id,
            "name_by_user": device_entry.name_by_user,
            "name_default": device_entry.name,
            "product_id": product_id,
            "status": "reloaded",
            "record_date": datetime.now(tz=ZoneInfo("UTC")).isoformat()
        }
        
        for entity in self.connector._listened_entities:
            state = self.hass.states.get(entity)
            if state is None or state.state == "unavailable":
                continue
            entity_entry = er.async_get(entity)
            entity_data = parse_entity_data(entity_entry, state)
            if entity_data is not None:
                sent_data = {**sent_data, **entity_data}
        
        self.hass.async_create_task(self.async_post_data(
            sent_data,
        ))
    
    
    async def async_post_data(self, payload: dict):
        json_data = json.json_dumps({
                "project_id": self.__project_id,
                "collection_id": self.__collection_id,
                "token_id": self.__api_token_id,
                "user": {
                    "collection_id": self._user_collection_id,
                    "id": self._user_id,
                },
                "data": payload,
            })
        
        timestamp = datetime.fromisoformat(payload.get("record_date"))
        _timestamp = timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        self.snapshot_buffer({
            "timestamp": _timestamp,
            "connector_entity_id": self.connector._connector_entity_id,
            "collection_id": self.__collection_id,
            "payload": json_data,
        })
        
        """Publish data to Hyperbase collection."""
        await self._mqttc.async_publish(
            self._mqtt_topic,
            json_data,
            qos=1,
            retain=False,
        )
        
        self.hass.states.async_set(
            self.connector._connector_entity_id,
            new_state=datetime.now(),
            attributes={
                "listened_device": self.connector._listened_device.id,
                "listened_entities": self.connector._listened_entities,
                "poll_time_s": self.connector._poll_time_s,
                "model_identity": self.__collection_name,
                },
            timestamp=datetime.now().timestamp()
        )


class HyperbaseTaskManager:
    def __init__(self,
        hass: HomeAssistant,
        mqttc: MQTT,
        mqtt_topic: str,
        project_manager: HyperbaseProjectManager,
        user_id: str,
        user_collection_id: str,
        ):
        
        self.hass = hass
        self.mqttc = mqttc
        self._data_collecting_tasks: dict[str, Any] = {}
        self._data_collecting_task_info: dict[str, Task] = {}
        self.project_manager = project_manager
        self._mqtt_topic = mqtt_topic
        
        self._user_id = user_id
        self._user_collection_id = user_collection_id
        
        self.recorder = SnapshotRecorder(self.hass)
        
        self._snapshot_buffer: list[dict] = []
        self._shutdown_callback = []
    
    
    async def async_load_runtime_tasks(self, connectors: list[HyperbaseConnectorEntry]):
        await self._async_check_failed()
        
        self._shutdown_callback.append(
            async_track_time_interval(self.hass,
                self._async_write_snapshot, interval=timedelta(seconds=15))
        )
        self._shutdown_callback.append(
            async_track_time_interval(self.hass,
                self._async_consistency_check, interval=timedelta(minutes=3))
        )
        self._shutdown_callback.append(
            async_track_time_interval(self.hass,
                self._async_check_failed, interval=timedelta(minutes=3))
        )
        
        for connector in connectors:
            self.hass.async_create_task(self.__start_logging(connector))


    async def __start_logging(self, connector: HyperbaseConnectorEntry):
        task = Task(
                hass=self.hass,
                api_token_id=self.project_manager.api_token_id,
                collection_id=self.project_manager.get_collection_id(connector._collection_name),
                collection_name=connector._collection_name,
                connector=connector,
                mqtt_client=self.mqttc,
                mqtt_topic=self._mqtt_topic,
                project_id=self.project_manager.project_id,
                project_name=self.project_manager.entry.data[CONF_PROJECT_NAME],
                user_id = self._user_id,
                user_collection_id = self._user_collection_id,
                callbacks={
                    "snapshot_buffer": self.append_snapshot_buffer,
                }
            )
        
        self._data_collecting_task_info[connector._connector_entity_id] = task
        
        await task.async_publish_reload_status()
        
        self._data_collecting_tasks[connector._connector_entity_id] = async_track_time_interval(self.hass,
                task.async_publish_on_tick,
                interval=timedelta(seconds=connector._poll_time_s),
                cancel_on_shutdown=True,
            )


    async def _async_write_snapshot(self, _=None):
        if len(self._snapshot_buffer) < 1:
            return
        snapshot_entries = self._snapshot_buffer.copy()
        self._snapshot_buffer.clear()
        await self.hass.async_add_executor_job(self.recorder.write_recorder, snapshot_entries, self.project_manager.project_id)


    async def _async_consistency_check(self, _last_entry_record_time: datetime):
        hyp = await async_get_hyperbase_registry(self.hass)
        connectors = hyp.get_connector_entries()
        start_time = _last_entry_record_time - timedelta(minutes=4)
        end_time = _last_entry_record_time - timedelta(minutes=1)
        
        _set, _mapping = await self.hass.async_add_executor_job(
            self.recorder.query_snapshots,
            start_time.isoformat(),
            end_time.isoformat())
        
        # prevent calling API if there is no collected data within given time range
        if len(_set) < 0:
            return
        
        collection_ids = []
        for connector in connectors:
            collection_id = self.project_manager.get_collection_id(connector._collection_name)
            collection_ids.append(collection_id)
        
        hyperbase_data_set = set([])
        is_success = False
        for collection_id in collection_ids:
            res = await self.project_manager.async_fetch_records_consistency(
                collection_id,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
            )
            if not res.get("success"):
                is_success = False
                break
            
            is_success = True
            if res.get("count") < 1:
                continue
            for entry in res.get("data"):
                hyperbase_data_set.add((entry.get("connector_entity"), entry.get("record_date")))
        
        if not is_success:
            await self.hass.async_add_executor_job(
                self.recorder.write_fail_snapshot,
                start_time.isoformat(),
                end_time.isoformat())
            return is_success
        
        
        _set = set(_set)
        _set.difference_update(hyperbase_data_set)
        if len(_set) > 0:
            snapshot_ids = []
            for item in _set:
                snapshot_id = _mapping.get(f"{item[0]}{item[1]}")
                id_query = f"id={snapshot_id}"
                snapshot_ids.append(id_query)
            payloads = await self.hass.async_add_executor_job(
                self.recorder.query_snapshots_by_ids, snapshot_ids)
            
            # payload is a tuple: (data, )
            payloads_json = [json_loads(payload[0]) for payload in payloads]
            
            for payload in payloads:
                await self._async_retry_failed(payload[0])
            
            retry_data = {
                "timestamp": _last_entry_record_time.isoformat(),
                "length": len(payloads_json),
                "data": payloads_json,
            }
            
            await self.project_manager.async_create_bucket_object(retry_data)
        
        return is_success


    async def _async_check_failed(self, _=None):
        failed_snapshots = await self.hass.async_add_executor_job(
            self.recorder.query_failed_snapshots
        )
        if len(failed_snapshots) < 1:
            return
        
        for failed_snapshot in failed_snapshots:
            is_success = await self._async_consistency_check(datetime.fromisoformat(failed_snapshot.end_time))
            if not is_success:
                await self.hass.async_add_executor_job(
                    self.recorder.delete_failed_snapshot_by_id,
                    failed_snapshot.failed_id
                )
                return
        
        first_entry_start_time = failed_snapshots[0].start_time
        last_entry_start_time = failed_snapshots[-1].start_time
        
        await self.hass.async_add_executor_job(
            self.recorder.flush_failed_snapshots,
            first_entry_start_time,
            last_entry_start_time
        )


    async def _async_retry_failed(self, payload):
        self.hass.async_create_task(self.mqttc.async_publish(
            self._mqtt_topic,
            payload,
            qos=1,
            retain=False,
        ))


    def append_snapshot_buffer(self, snapshot_entry: dict):
        self._snapshot_buffer.append(snapshot_entry)


    def get_active_connector_by_id(self, connector_entity: str) -> HyperbaseConnectorEntry | None:
        if self._data_collecting_task_info.get(connector_entity) is None:
            return None
        return self._data_collecting_task_info.get(connector_entity).connector


    def _shutdown_cancel(self):
        for task in self._shutdown_callback:
            task()


    @property
    def runtime_tasks(self):
        return self._data_collecting_tasks
    
    @property
    def runtime_task_info(self):
        return self._data_collecting_task_info