from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo
import httpx
from paho.mqtt.enums import CallbackAPIVersion, MQTTProtocolVersion

from .util import get_model_identity, is_valid_connector_entity, format_device_name

from .exceptions import ConnectorEntityExists, HyperbaseHTTPError, HyperbaseMQTTConnectionError, HyperbaseRESTConnectivityError, InvalidConnectorEntity, FailedConnector

from .common import HyperbaseConnectorEntry, async_get_hyperbase_registry
from homeassistant.helpers import selector
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry, async_entries_for_device
from homeassistant.helpers.httpx_client import get_async_client
from paho.mqtt import client as mqtt

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import (
    CONF_ACTION,
    CONF_EMAIL,
    CONF_ENTITY_ID,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_API_TOKEN,
)

from .const import (
    CONF_AUTH_TOKEN,
    CONF_BUCKET_ID,
    CONF_MQTT_TOPIC,
    CONF_USER_COLLECTION_ID,
    CONF_USER_ID,
    LOGGER,
    DOMAIN,
    CONF_BASE_URL,
    CONF_MQTT_ADDRESS,
    CONF_MQTT_PORT,
    CONF_PROJECT_ID,
    CONF_PROJECT_NAME,
    CONF_REST_ADDRESS,
    HYPERBASE_RESPONSE_CODE,
    HYPERBASE_RESPONSE_MSG,
)

@dataclass
class HyperbaseCollection:
    id: str
    name: str

def login(email: str, password: str, base_url: str="http://localhost:8080"):
    try:
        client = httpx.Client()
        r = client.post(f"{base_url}/api/rest/auth/password-based",
                                json={"email": email, "password": password})
        r.raise_for_status()
        return r.json()["data"]["token"]
    except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
        LOGGER.error(exc)
        raise HyperbaseRESTConnectivityError(exc.args)
    except httpx.HTTPStatusError as exc:
        LOGGER.error(exc.response.json()['error']['message'])
        raise HyperbaseHTTPError(exc.response.json()['error']['status'], status_code=exc.response.status_code)


async def async_get_hyperbase_collections(hass: HomeAssistant, project_id:str, auth_token:str, base_url: str):
    try:
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        client = get_async_client(hass, verify_ssl=False)
        res = await client.get(
            f"{base_url}/api/rest/project/{project_id}/collections",
            headers=headers,
        )
        res.raise_for_status()
        
        collections = {}
        data = res.json().get("data", [])
        for collection in data:
            if collection.get("name", "").startswith("hass."):
                collection_name = collection.get("name")
                collections[collection_name] = collection.get("id")
        
        return collections
    except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
        LOGGER.error(exc)
        raise HyperbaseRESTConnectivityError(exc.args)
    except httpx.HTTPStatusError as exc:
        LOGGER.error(exc.response.json()['error']['message'])
        raise HyperbaseHTTPError(exc.response.json()['error']['status'], status_code=exc.response.status_code)

def get_hyperbase_project(project_id:str, auth_token:str, base_url: str="http://localhost:8080"):
    try:
        client = httpx.Client()
        client.headers.update({"Authorization": f"Bearer {auth_token}"})
        r = client.get(f"{base_url}/api/rest/project/{project_id}")
        r.raise_for_status()
        return r.json()["data"]
    except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
        LOGGER.error(exc)
        raise HyperbaseRESTConnectivityError(exc.args)
    except httpx.HTTPStatusError as exc:
        LOGGER.error(exc.response.json()['error']['message'])
        raise HyperbaseHTTPError(exc.response.json()['error']['status'], status_code=exc.response.status_code)


def validate_user_account(project_id: str, user_id: str, auth_token:str, base_url: str="http://localhost:8080"):
    try:
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        with httpx.Client(verify=False, headers=headers) as client:
            r = client.get(f"{base_url}/api/rest/project/{project_id}/collections")
            r.raise_for_status()
            collections: list[dict] = r.json().get("data", [{}])
            
            collection_id = ""
            for collection in collections:
                if collection.get("name") == "Users":
                    collection_id = collection.get("id")

            r = client.get(f"{base_url}/api/rest/project/{project_id}/collection/{collection_id}/record/{user_id}")
            r.raise_for_status()
            return {"collection_id": collection_id, "user_id": user_id}
    except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
        LOGGER.error(exc)
        raise HyperbaseRESTConnectivityError(exc.args)
    except httpx.HTTPStatusError as exc:
        LOGGER.error(exc.response.json()['error']['message'])
        raise HyperbaseHTTPError(exc.response.json()['error']['status'], status_code=exc.response.status_code)


async def async_create_bucket(hass: HomeAssistant, project_id: str, auth_token: str, base_url):
    try:
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        req = {
            "name": "HA Retries",
        }
        
        client = get_async_client(hass, verify_ssl=False)
        
        buckets_res = await client.get(
                f"{base_url}/api/rest/project/{project_id}/buckets",
                headers=headers,
            )
        buckets_res.raise_for_status()
        buckets_data = buckets_res.json().get("data", [])
        
        for _bucket in buckets_data:
            token_name = _bucket.get("name", "")
            if token_name == "HA Retries":
                return _bucket.get("id")
        
        
        res = await client.post(
            f"{base_url}/api/rest/project/{project_id}/bucket",
            json=req,
            headers=headers,
        )
        res.raise_for_status()
        bucket: dict = res.json().get("data", {})
        bucket_id = bucket.get("id")
        
        return bucket_id
    except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
        LOGGER.error(exc)
        raise HyperbaseRESTConnectivityError(exc.args)
    except httpx.HTTPStatusError as exc:
        LOGGER.error(exc.response.json()['error']['message'])
        raise HyperbaseHTTPError(exc.response.json()['error']['status'], status_code=exc.response.status_code)


def create_api_token(project_id: str, auth_token: str, bucket_id: str,base_url):
    try:
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        
        with httpx.Client(verify=False, headers=headers) as client:
            
            tokens_res = client.get(
                f"{base_url}/api/rest/project/{project_id}/tokens",
            )
            tokens_res.raise_for_status()
            tokens_data = tokens_res.json().get("data", [])
            
            for _token in tokens_data:
                token_name = _token.get("name", "")
                if token_name == "HA Access Token":
                    return _token.get("id")
            
            
            res = client.post(
                f"{base_url}/api/rest/project/{project_id}/token",
                json={
                    "name": "HA Access Token",
                    "allow_anonymous": False,
                }
            )
            res.raise_for_status()
            token: dict = res.json().get("data", {})
            token_id = token.get("id")
            
            # add bucket rule to allow create new file into the bucket
            res = client.post(
                f"{base_url}/api/rest/project/{project_id}/token/{token_id}/bucket_rule",
                json={
                    "bucket_id": bucket_id,
                    "find_one": "none",
                    "find_many": "none",
                    "insert_one": True,
                    "update_one": "none",
                    "delete_one": "none",
                }
            )
            res.raise_for_status()
            return token_id
    except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
        LOGGER.error(exc)
        raise HyperbaseRESTConnectivityError(exc.args)
    except httpx.HTTPStatusError as exc:
        LOGGER.error(exc.response.json()['error']['message'])
        raise HyperbaseHTTPError(exc.response.json()['error']['status'], status_code=exc.response.status_code)

def ping_rest_server(base_url: str):
    try:
        client = httpx.Client()
        _ = client.get(base_url)
        return {"success": True}
    except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
        LOGGER.error(exc)
        raise HyperbaseRESTConnectivityError(exc.args)


def ping_mqtt_server(host:str, port:int, topic: str):
    
    def _on_connect_callback(_mqttc: mqtt.Client, _userdata, _flags, result_code: int, properties):
        if result_code != mqtt.CONNACK_ACCEPTED:
            return result_code
        _mqttc.publish(topic, payload="ping")
    
    def _on_publish_callback(_mqttc: mqtt.Client, userdata, mid, reason_code, properties):
        LOGGER.info("ping sent")
        _mqttc.disconnect()
        _mqttc.loop_stop()
    
    def _on_disconnect_callback(client, userdata, disconnect_flags, reason_code, properties):
        LOGGER.info(f"MQTT client disconnected ({reason_code})")
    
    mqttc = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id="hass",
            protocol=MQTTProtocolVersion.MQTTv5
        )
    mqttc.on_connect = _on_connect_callback
    mqttc.on_publish = _on_publish_callback
    mqttc.on_disconnect = _on_disconnect_callback
    
    connect_result = None
    try:
        connect_result = mqttc.connect(host, port)
    except OSError as exc:
        LOGGER.error(exc)
        raise HyperbaseMQTTConnectionError(exc.args)
    
    if connect_result is not None and connect_result != 0:
        raise HyperbaseMQTTConnectionError(mqtt.error_string(connect_result))
    
    mqttc.loop_start()

class HyperbaseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    __auth_token: str = ""
    __project_config: dict[str, Any] = {}
    __network_config: dict[str, Any] = {}
    
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow for this handler."""
        return HyperbaseOptionsFlowHandler()
    
    
    async def async_step_user(self, user_input: Optional[dict[str, Any]] = None):
        """Step for creating new hyperbase connection"""
        errors = {}
        placeholders = {}
        if user_input is not None:
            base_url = user_input.get(CONF_REST_ADDRESS)
            try: 
                await self.hass.async_add_executor_job(ping_rest_server, base_url)
                await self.hass.async_add_executor_job(ping_mqtt_server,
                    user_input.get(CONF_MQTT_ADDRESS),
                    user_input.get(CONF_MQTT_PORT),
                    user_input.get(CONF_MQTT_TOPIC)
                )
                self.__network_config = {
                    CONF_BASE_URL: base_url,
                    CONF_MQTT_ADDRESS: user_input.get(CONF_MQTT_ADDRESS),
                    CONF_MQTT_PORT: user_input.get(CONF_MQTT_PORT),
                    CONF_MQTT_TOPIC: user_input.get(CONF_MQTT_TOPIC)
                }
                return await self.async_step_login()
            except HyperbaseRESTConnectivityError as exc:
                placeholders = {
                    HYPERBASE_RESPONSE_MSG: exc.args,
                    "network_type": "REST"
                }
            except HyperbaseMQTTConnectionError as exc:
                placeholders = {
                    HYPERBASE_RESPONSE_MSG: exc.args,
                    "network_type": "MQTT"
                }
            errors["base"] = "network_error"
            
        else:
            user_input = {}
        
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(
            {
                vol.Required(CONF_REST_ADDRESS, description="Hyperbase Backend Host", default=user_input.get(CONF_REST_ADDRESS, "http://localhost:8080")): str,
                vol.Required(CONF_MQTT_ADDRESS, description="MQTT Broker Address", default=user_input.get(CONF_MQTT_ADDRESS, "localhost")): str,
                vol.Required(CONF_MQTT_PORT, description="MQTT Broker Port", default=user_input.get(CONF_MQTT_PORT, 1883)): cv.port,
                vol.Required(CONF_MQTT_TOPIC, description="MQTT Topic to publish", default=user_input.get(CONF_MQTT_TOPIC, "hyperbase")): str
            }),
            errors=errors,
            description_placeholders=placeholders,
        )
    
    
    async def async_step_login(self, user_input: Optional[Dict[str, Any]] = None):
        """Step to specify target project ID to collect data into Hyperbase"""
        errors = {}
        placeholders = {}
        if user_input is not None:
            is_login_success = False
            is_project_exists = False
            try:
                self.__auth_token = await self.hass.async_add_executor_job(login,
                    user_input.get(CONF_EMAIL), user_input.get(CONF_PASSWORD),
                    self.__network_config.get(CONF_BASE_URL))
                is_login_success = True
                project = await self.hass.async_add_executor_job(get_hyperbase_project,
                    user_input.get(CONF_PROJECT_ID),
                    self.__auth_token,
                    self.__network_config.get(CONF_BASE_URL)
                )
                self.__project_config = {
                    CONF_PROJECT_ID: user_input.get(CONF_PROJECT_ID),
                    CONF_PROJECT_NAME: project.get(CONF_NAME)
                }
                await self.async_set_unique_id(user_input.get(CONF_PROJECT_ID))
                self._abort_if_unique_id_configured()
                
                is_project_exists = True
                
                user_collection = await self.hass.async_add_executor_job(validate_user_account,
                    self.__project_config.get(CONF_PROJECT_ID),
                    user_input.get(CONF_USER_ID),
                    self.__auth_token,
                    self.__network_config.get(CONF_BASE_URL))
                
                bucket_id = await async_create_bucket(
                    self.hass, self.__project_config.get(CONF_PROJECT_ID),
                    self.__auth_token, self.__network_config.get(CONF_BASE_URL))
                
                token_id = await self.hass.async_add_executor_job(create_api_token,
                    self.__project_config.get(CONF_PROJECT_ID),
                    self.__auth_token,
                    bucket_id,
                    self.__network_config.get(CONF_BASE_URL))
                
                return self.async_create_entry(
                    title=self.__project_config.get(CONF_PROJECT_NAME),
                    data={
                        CONF_BASE_URL: self.__network_config.get(CONF_BASE_URL),
                        CONF_MQTT_ADDRESS: self.__network_config.get(CONF_MQTT_ADDRESS),
                        CONF_MQTT_PORT: self.__network_config.get(CONF_MQTT_PORT),
                        CONF_MQTT_TOPIC: self.__network_config.get(CONF_MQTT_TOPIC),
                        CONF_AUTH_TOKEN: self.__auth_token,
                        CONF_PROJECT_ID: self.__project_config.get(CONF_PROJECT_ID),
                        CONF_PROJECT_NAME: self.__project_config.get(CONF_PROJECT_NAME),
                        CONF_API_TOKEN: token_id,
                        CONF_USER_ID: user_collection.get("user_id"),
                        CONF_USER_COLLECTION_ID: user_collection.get("collection_id"),
                        CONF_BUCKET_ID: bucket_id,
                    },
                )
            except HyperbaseRESTConnectivityError as exc:
                errors["base"] = "network_error"
                placeholders = {
                    HYPERBASE_RESPONSE_MSG: exc.args,
                    "network_type": "REST"
                }
            except HyperbaseHTTPError as exc:
                if not is_login_success:
                    errors["base"] = "login_error"
                    placeholders = {
                        HYPERBASE_RESPONSE_CODE: exc.status_code,
                        HYPERBASE_RESPONSE_MSG: exc.args,
                    }
                elif not is_project_exists:
                    errors["base"] = "project_error"
                    placeholders = {
                        HYPERBASE_RESPONSE_CODE: exc.status_code,
                        HYPERBASE_RESPONSE_MSG: exc.args,
                    }
                else:
                    errors["base"] = "token_error"
                    placeholders = {
                        HYPERBASE_RESPONSE_CODE: exc.status_code,
                        HYPERBASE_RESPONSE_MSG: exc.args,
                    }
        else:
            user_input = {}
        
        return self.async_show_form(
            step_id="login", 
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, description="Hyperbase Account Email", default=user_input.get(CONF_EMAIL, "")): str,
                    vol.Required(CONF_PASSWORD, description="Hyperbase Account Password", default=user_input.get(CONF_PASSWORD, "")): str,
                    vol.Required(CONF_PROJECT_ID, description="Hyperbase Project ID", default=user_input.get(CONF_PROJECT_ID, "")): str,
                    vol.Required(CONF_USER_ID, default=user_input.get(CONF_USER_ID, "")): str,
                }
            ),
            errors=errors,
            description_placeholders=placeholders
        )


CONF_ADD_DEVICE = "add_device"
CONF_MANAGE_DEVICE = "manage_device"
CONF_REMOVE_DEVICE = "delete_device"
CONF_DOWNLOAD_DATA = "download_data"

CONF_ACTIONS = {
    CONF_ADD_DEVICE: "Register New Device",
    CONF_MANAGE_DEVICE: "Manage Registered Devices",
    CONF_REMOVE_DEVICE: "Remove Registered Device",
    CONF_DOWNLOAD_DATA: "Download CSV Data",
}

CONF_REMOVE_DEVICE_CONFIRM = "remove_device_confirm"


class ListenedEntityDomain:
    def __init__(self, domain, entity_id):
        self.domain = domain
        self.entity = entity_id

class HyperbaseOptionsFlowHandler(config_entries.OptionsFlow):
    __current_device = ""
    __current_connector_entity = ""
    __action = ""
    
    async def async_step_init(self, user_input: Optional[Dict[str, str]]=None):
        if user_input is not None:
            self.__action = user_input.get(CONF_ACTION)
            if self.__action == CONF_MANAGE_DEVICE or self.__action == CONF_REMOVE_DEVICE:
                return await self.async_step_select_connector()
            elif self.__action == CONF_DOWNLOAD_DATA:
                return await self.async_step_download_csv()
            
            return await self.async_step_select_device()
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACTION, default=CONF_MANAGE_DEVICE): vol.In(CONF_ACTIONS)
                }
            )
        )
    
    
    async def async_step_download_csv(self, user_input: dict | Any = None):
        collections = await async_get_hyperbase_collections(
            self.hass, self.config_entry.data.get(CONF_PROJECT_ID),
            self.config_entry.data.get(CONF_AUTH_TOKEN), self.config_entry.data.get(CONF_BASE_URL))
        
        collection_options = [collection_name for collection_name in collections.keys()]
        
        if user_input is not None:
            
            _oldest_dt = datetime.strptime(user_input.get("Oldest Data"), "%Y-%m-%d %H:%M:%S")
            _latest_dt = datetime.strptime(user_input.get("Latest Data"), "%Y-%m-%d %H:%M:%S")
            
            oldest_dt = _oldest_dt.astimezone(tz=ZoneInfo("UTC")).isoformat()
            latest_dt = _latest_dt.astimezone(tz=ZoneInfo("UTC")).isoformat()
            _collection_name = user_input.get("Collection Name")
            collection_id = collections.get(_collection_name)
            url = f"/api/hyperbase/download_csv?start_time={oldest_dt}&end_time={latest_dt}&collection_id={collection_id}"
            encoded_url = quote(url, safe="/?&=")
            
            HA_url = user_input.get("Home Assistant Base URL")
            self.base_url = f"{HA_url}{encoded_url}"
            return await self.async_step_confirm_url()
            
        return  self.async_show_form(
            step_id="download_csv",
            data_schema=vol.Schema(
                {
                    vol.Required("Oldest Data", default=datetime.now().strftime("%Y-%m-%d %H:%M:%S")): selector.DateTimeSelector(),
                    vol.Required("Latest Data", default=datetime.now().strftime("%Y-%m-%d %H:%M:%S")): selector.DateTimeSelector(),
                    vol.Required("Collection Name"): selector.SelectSelector(
                        config=selector.SelectSelectorConfig(
                            mode="dropdown",
                            options=collection_options
                        )
                    ),
                    vol.Required("Home Assistant Base URL", default="http://localhost:8123"): str,
                }
            )
        )
    
    
    async def async_step_confirm_url(self, user_input: Any = None):
        placeholders = {"csv_download_url": self.base_url}
        if user_input is not None:
            return self.async_create_entry(
                data={}
            )
        else:
            user_input = {}
        
        return self.async_show_form(
            step_id="confirm_url",
            data_schema=vol.Schema({}),
            description_placeholders=placeholders
        )
    async def async_step_select_device(self, user_input: Optional[Dict[str, Any]]=None):
        errors = {}
        
        if user_input is not None:
            self.__current_device = user_input.get("device")
            return await self.async_step_select_entities()
        else:
            user_input={}
        
        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({
                vol.Required("device", default=user_input.get("device")): selector.DeviceSelector(),
            }),
            errors=errors,
        )
    
    
    async def async_step_select_connector(self, user_input: Optional[Dict[str, Any]]=None) -> config_entries.ConfigFlowResult:
        er = async_get_entity_registry(self.hass)
        entries = er.entities.get_entries_for_config_entry_id(self.config_entry.entry_id)
        entities = [entry.entity_id for entry in entries]
        default = None
        if len(entities) > 0:
            default = entities[0]
        
        if user_input is not None:
            self.__current_connector_entity = user_input.get(CONF_ENTITY_ID)
            if self.__action == CONF_REMOVE_DEVICE:
                return await self.async_step_remove_device()
            return await self.async_step_manage_connector()
        else:
            user_input = {}
        
        return self.async_show_form(
            step_id="select_connector",
            data_schema=vol.Schema({
                vol.Required(CONF_ENTITY_ID, default=user_input.get(CONF_ENTITY_ID, default)): selector.EntitySelector(
                    config=selector.EntitySelectorConfig(
                        include_entities=entities
                        )),
            }),
        )
    
    
    async def async_step_manage_connector(self, user_input: Optional[Dict[str, Any]]=None):
        er = async_get_entity_registry(self.hass)
        
        hyp = await async_get_hyperbase_registry(self.hass)
        connector = hyp.get_connector_entry(self.__current_connector_entity)
        
        
        listened_entity_domains: dict[str, list[str]] = {}
        listened_entities: list = connector._listened_entities
        prev_poll_time_s: int = connector._poll_time_s
        
        entity_entries = async_entries_for_device(er, connector._listened_device.id)
        
        for default_entity in entity_entries:
            if default_entity.original_device_class is None:
                if default_entity.translation_key is not None:
                    _available_entities = listened_entity_domains.get(f"{default_entity.domain}.{default_entity.translation_key}", [])
                    _available_entities.append(default_entity.entity_id)
                    listened_entity_domains[f"{default_entity.domain}.{default_entity.translation_key}"] = _available_entities
                    continue
                _available_entities = listened_entity_domains.get(default_entity.domain, [])
                _available_entities.append(default_entity.entity_id)
                listened_entity_domains[default_entity.domain] = _available_entities
                continue
            _available_entities = listened_entity_domains.get(f"{default_entity.domain}.{default_entity.original_device_class}", [])
            _available_entities.append(default_entity.entity_id)
            listened_entity_domains[f"{default_entity.domain}.{default_entity.original_device_class}"] = _available_entities
        
        
        schema = vol.Schema({})
        
        
        for entity_domain_mapping in listened_entity_domains.keys():
            default_select = set(listened_entity_domains.get(entity_domain_mapping)).intersection(listened_entities)
            _selected = None
            if len(default_select) > 0:
                _selected = list(default_select)[0]
            
            schema = schema.extend({
                vol.Optional(entity_domain_mapping,
                        description={
                            "suggested_value": _selected
                        }): selector.EntitySelector(
                        config=selector.EntitySelectorConfig(
                            include_entities=listened_entity_domains.get(entity_domain_mapping)
                        )
                    )
            })
        
        schema = schema.extend({
            vol.Required("poll_time_s", default=connector._poll_time_s): int,
        })
        
        errors={}
        placeholders={}
        
        if user_input is not None:
            listened_entities = []
            for input_key in user_input.keys():
                if input_key == "poll_time_s":
                    continue
                listened_entities.append(user_input.get(input_key))
            prev_state = self.hass.states.get(self.__current_connector_entity)
            _updated = {
                "listened_entities": listened_entities,
                "poll_time_s": user_input["poll_time_s"]
            }
            
            new_state_attr = {**prev_state.attributes, **_updated}

            
            
            # set updated configuration into corresponding entity attributes.
            # awaits the execution to make sure the attributes is updated before
            # continue the operation.
            await self.hass.async_add_executor_job(self.hass.states.set,
                connector._connector_entity_id, prev_state.state, new_state_attr, True)
            
            
            # update runtime information for new entities configuration without
            # the need to revalidate or re-read from file
            device_info = await self.config_entry.runtime_data.async_update_listened_entities(
                self.__current_connector_entity,
                listened_entities,
                user_input.get("poll_time_s")
            )
            
            if prev_poll_time_s != user_input.get("poll_time_s"):
                # if poll time is changed, we need to reload the runtime task
                await self.config_entry.runtime_data.async_reload_task(device_info)
            
            await hyp.async_update_connector_entries(
                connector._connector_entity_id, listened_entities, user_input.get("poll_time_s")
            )
            
            self.__current_connector_entity = ""
            return self.async_create_entry(
                title="new_device_config",
                data={}
            )
        
        return self.async_show_form(
            step_id="manage_connector",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders
        )
    
    
    async def async_step_select_entities(self, user_input: Optional[Dict[str, Any]]=None):
        dr = async_get_device_registry(self.hass)
        er = async_get_entity_registry(self.hass)
        
        registering_device = dr.async_get(self.__current_device)
        connector_entity = f"{format_device_name(registering_device.name)}_last_sent"
        
        schema = vol.Schema({
            vol.Required("connector_entity", default=connector_entity): str,
        })
        
        listened_entity_domains: dict[str, list[str]] = {}
        entity_entries = async_entries_for_device(er, self.__current_device)
        for entry in entity_entries:
            if entry.original_device_class is None:
                if entry.translation_key is not None:
                    _available_entities = listened_entity_domains.get(f"{entry.domain}.{entry.translation_key}", [])
                    _available_entities.append(entry.entity_id)
                    listened_entity_domains[f"{entry.domain}.{entry.translation_key}"] = _available_entities
                    continue
                _available_entities = listened_entity_domains.get(entry.domain, [])
                _available_entities.append(entry.entity_id)
                listened_entity_domains[entry.domain] = _available_entities
                continue
            _available_entities = listened_entity_domains.get(f"{entry.domain}.{entry.original_device_class}", [])
            _available_entities.append(entry.entity_id)
            listened_entity_domains[f"{entry.domain}.{entry.original_device_class}"] = _available_entities
        
        for entity_domain_mapping in listened_entity_domains.keys():
            schema = schema.extend({
                vol.Optional(entity_domain_mapping,
                        description={
                            "suggested_value": listened_entity_domains.get(entity_domain_mapping)[0]
                        }): selector.EntitySelector(
                        config=selector.EntitySelectorConfig(
                            include_entities=listened_entity_domains.get(entity_domain_mapping)
                        )
                    )
            })
        
        schema = schema.extend({
            vol.Required("poll_time_s", default=5): int,
            vol.Required("add_next", default=False): selector.BooleanSelector()
        })
        
        errors={}
        placeholders={}
        
        if user_input is not None:
            try:
                _ = is_valid_connector_entity(user_input.get("connector_entity"))
                listened_entities = []
                for input_key in user_input.keys():
                    if input_key == "poll_time_s" or input_key == "add_next" or input_key == "connector_entity":
                        continue
                    listened_entities.append(user_input.get(input_key))
                _entity = er.async_get_entity_id("event", "hyperbase", user_input.get("connector_entity"))
                if _entity is not None:
                    raise ConnectorEntityExists
                
                entry = er.async_get_or_create(
                        device_id=self.config_entry.runtime_data.hyperbase_device_id,
                        domain="event",
                        platform="hyperbase",
                        unique_id=user_input.get("connector_entity"),
                        has_entity_name=True,
                        config_entry=self.config_entry,
                        original_name=get_model_identity(registering_device),
                    )
                
                
                connector = HyperbaseConnectorEntry(
                    connector_entity_id=entry.entity_id,
                    project_id=self.config_entry.data.get(CONF_PROJECT_ID),
                    listened_device=registering_device,
                    listened_entities=listened_entities,
                    poll_time_s=user_input.get("poll_time_s"),
                )
                
                hyperbase = await async_get_hyperbase_registry(self.hass)
                await hyperbase.async_store_connector_entry(connector)
                
                await self.config_entry.runtime_data.async_add_new_listened_device(connector)
                collection_id = self.config_entry.runtime_data.manager.get_collection_id(connector._collection_name)
                if collection_id is None:
                    er.async_remove(entry.entity_id)
                    await hyperbase.async_delete_connector_entry(connector._connector_entity_id)
                    self.config_entry.runtime_data._cancel_runtime_task(connector._connector_entity_id)
                    raise FailedConnector
                
                if user_input["add_next"]:
                    return await self.async_step_select_device()
                
                return self.async_create_entry(
                    title="new_device_config",
                    data={}
                )
            except InvalidConnectorEntity:
                errors["base"] = "invalid_entity"
            except FailedConnector:
                errors["base"] = "failed_connector"
            except ConnectorEntityExists:
                errors["base"] = "entity_exists"
        
        return self.async_show_form(
            step_id="select_entities",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders
        )
    
    
    async def async_step_remove_device(self, user_input: Optional[Dict[str, Any]]=None):
        er = async_get_entity_registry(self.hass)
        
        hyp = await async_get_hyperbase_registry(self.hass)
        
        errors = {}
        placeholders = {}
        placeholders["connector_entity_id"] = self.__current_connector_entity
        
        if user_input is not None:
            if user_input.get(CONF_REMOVE_DEVICE_CONFIRM) != self.__current_connector_entity:
                errors["base"] = "invalid_id"
            else:
                er.async_remove(self.__current_connector_entity)
                await hyp.async_delete_connector_entry(self.__current_connector_entity)
                self.config_entry.runtime_data._cancel_runtime_task(self.__current_connector_entity)
                return self.async_create_entry(
                    title="remove_device_config",
                    data={}
                )
        else:
            user_input = {}
        
        return self.async_show_form(
            step_id="remove_device",
            data_schema=vol.Schema({
                vol.Required(CONF_REMOVE_DEVICE_CONFIRM): str
            }),
            description_placeholders=placeholders,
            errors=errors
        )