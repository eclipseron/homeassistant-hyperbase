import datetime
from typing import Any, Dict, Optional
import httpx
from paho.mqtt.enums import CallbackAPIVersion, MQTTProtocolVersion

from .exceptions import HyperbaseHTTPError, HyperbaseMQTTConnectionError, HyperbaseRESTConnectivityError

from .common import ListenedDeviceEntry
from homeassistant.helpers import selector
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry, async_entries_for_device
from paho.mqtt import client as mqtt

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import (
    CONF_ACTION,
    CONF_EMAIL,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TOKEN
)

from .const import (
    CONF_MQTT_TOPIC,
    LOGGER,
    DOMAIN,
    CONF_BASE_URL,
    CONF_MQTT_ADDRESS,
    CONF_MQTT_PORT,
    CONF_PROJECT_ID,
    CONF_PROJECT_NAME,
    CONF_REST_ADDRESS,
    CONF_REST_PORT,
    CONF_REST_PROTOCOL,
    HYPERBASE_RESPONSE_CODE,
    HYPERBASE_RESPONSE_MSG,
    HYPERBASE_RESPONSE_SUCCESS,
    HYPERBASE_RESPONSE_TOKEN
)

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
        raise HyperbaseHTTPError(exc.response.json()['error']['status'], status_code=exc.response.status_code)


def validate_api_token(project_id: str, token_id: str, auth_token:str, base_url: str="http://localhost:8080"):
    try:
        client = httpx.Client()
        client.headers.update({"Authorization": f"Bearer {auth_token}"})
        r = client.get(f"{base_url}/api/rest/project/{project_id}/token/{token_id}")
        r.raise_for_status()
    except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
        LOGGER.error(exc)
        raise HyperbaseRESTConnectivityError(exc.args)
    except httpx.HTTPStatusError as exc:
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
            _login_success = False
            try:
                self.__auth_token = await self.hass.async_add_executor_job(login,
                    user_input.get(CONF_EMAIL), user_input.get(CONF_PASSWORD),
                    self.__network_config.get(CONF_BASE_URL))
                _login_success = True
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
                return await self.async_step_setup_collection()
            except HyperbaseRESTConnectivityError as exc:
                errors["base"] = "network_error"
                placeholders = {
                    HYPERBASE_RESPONSE_MSG: exc.args,
                    "network_type": "REST"
                }
            except HyperbaseHTTPError as exc:
                errors["base"] = "login_error"
                placeholders = {
                    HYPERBASE_RESPONSE_CODE: exc.status_code,
                    HYPERBASE_RESPONSE_MSG: exc.args,
                }
                if _login_success:
                    errors["base"] = "project_error"
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
                }
            ),
            errors=errors,
            description_placeholders=placeholders
        )
    
    
    async def async_step_setup_collection(self, user_input: Optional[Dict[str, Any]] = None):
        """Step to config MQTT connection to Hyperbase"""
        errors = {}
        placeholders = {}
        if user_input is not None:
            try:
                await self.hass.async_add_executor_job(validate_api_token,
                    self.__project_config.get(CONF_PROJECT_ID),
                    user_input.get("token_id"),
                    self.__auth_token,
                    self.__network_config.get(CONF_BASE_URL))
                
                return self.async_create_entry(
                    title=self.__project_config.get(CONF_PROJECT_NAME),
                    data={
                        CONF_BASE_URL: self.__network_config.get(CONF_BASE_URL),
                        CONF_MQTT_ADDRESS: self.__network_config.get(CONF_MQTT_ADDRESS),
                        CONF_MQTT_PORT: self.__network_config.get(CONF_MQTT_PORT),
                        CONF_MQTT_TOPIC: self.__network_config.get(CONF_MQTT_TOPIC),
                        "auth_token": self.__auth_token,
                        CONF_PROJECT_ID: self.__project_config.get(CONF_PROJECT_ID),
                        CONF_PROJECT_NAME: self.__project_config.get(CONF_PROJECT_NAME),
                        "connection_name": user_input.get("connection_name"),
                        "api_token": user_input.get("token_id")
                        },
                )
            except HyperbaseRESTConnectivityError as exc:
                errors["base"] = "network_error"
                placeholders = {
                    HYPERBASE_RESPONSE_MSG: exc.args,
                    "network_type": "REST"
                }
            except HyperbaseHTTPError as exc:
                errors["base"] = "token_error"
                placeholders = {
                    HYPERBASE_RESPONSE_CODE: exc.status_code,
                    HYPERBASE_RESPONSE_MSG: exc.args,
                }
        else:
            user_input = {}
        
        return self.async_show_form(
            step_id="setup_collection", data_schema=vol.Schema(
            {
                vol.Required("connection_name", default=user_input.get("connection_name", "")): str,
                vol.Required("token_id", default=user_input.get("token_id", "")): str,
            }),
            errors=errors,
            description_placeholders=placeholders
        )
    
    
    async def async_step_reconfigure(self, user_input: Optional[Dict[str, Any]] = None):
        """Step to reconfigure MQTT connection to Hyperbase"""
        errors = {}
        
        # retrieve previous entry
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        new_entry = entry
        if new_entry is None:
            LOGGER.error("No previous entry found for reconfiguration")
            return self.async_abort(reason="no_previous_entry")
        
        if user_input is not None:
            
            await self.async_set_unique_id(new_entry.data[CONF_PROJECT_ID])
            self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(
                title=new_entry.data[CONF_PROJECT_NAME],
                entry=new_entry,
                data_updates={
                    CONF_MQTT_ADDRESS: user_input[CONF_MQTT_ADDRESS],
                    CONF_MQTT_PORT: user_input[CONF_MQTT_PORT],
                    CONF_MQTT_TOPIC: user_input[CONF_MQTT_TOPIC],
                    },
            )
        else:
            user_input = {}
        
        return self.async_show_form(
            step_id="reconfigure", 
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MQTT_ADDRESS, default=new_entry.data[CONF_MQTT_ADDRESS]): str,
                    vol.Required(CONF_MQTT_PORT, default=new_entry.data[CONF_MQTT_PORT]): cv.port,
                    vol.Required(CONF_MQTT_TOPIC, default=new_entry.data[CONF_MQTT_TOPIC]): str,
                }
            ),
            errors=errors
        )


CONF_ADD_DEVICE = "add_device"
CONF_MANAGE_DEVICE = "manage_device"
CONF_REMOVE_DEVICE = "config_device"

CONF_ACTIONS = {
    CONF_ADD_DEVICE: "Register New Device",
    CONF_MANAGE_DEVICE: "Manage Registered Devices",
    CONF_REMOVE_DEVICE: "Remove Registered Device",
}

CONF_REMOVE_DEVICE_CONFIRM = "remove_device_confirm"


class HyperbaseOptionsFlowHandler(config_entries.OptionsFlow):
    __new_registering_device: list[ListenedDeviceEntry] = []
    __current_device = ""
    __config_actions = ""
    
    async def async_step_init(self, user_input: Optional[Dict[str, str]]=None):
        if user_input is not None:
            self.__config_actions = user_input.get(CONF_ACTION)
            return await self.async_step_select_device()
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACTION, default=CONF_MANAGE_DEVICE): vol.In(CONF_ACTIONS)
                }
            )
        )
    
    async def async_step_select_device(self, user_input: Optional[Dict[str, Any]]=None):
        er = async_get_entity_registry(self.hass)
        entries = er.entities.get_entries_for_config_entry_id(self.config_entry.entry_id)
        configured_devices = []
        for e in entries:
            configured_devices.append(e.capabilities.get("listened_device"))
        
        errors = {}
        
        if user_input is not None:
            self.__current_device = user_input.get("device")
            if self.__config_actions == CONF_ADD_DEVICE:
                try:
                    _ = configured_devices.index(self.__current_device)
                    errors["base"] = "device_exists"
                except ValueError:
                    return await self.async_step_select_entities()
            if self.__config_actions == CONF_MANAGE_DEVICE:
                try:
                    _ = configured_devices.index(self.__current_device)
                    pass
                except ValueError:
                    errors["base"]="device_not_exists"
            if self.__config_actions == CONF_REMOVE_DEVICE:
                try:
                    _ = configured_devices.index(self.__current_device)
                    return await self.async_step_remove_device()
                except ValueError:
                    errors["base"]="device_not_exists"
        else:
            user_input={}
        
        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({
                vol.Required("device", default=user_input.get("device")): selector.DeviceSelector(),
            }),
            errors=errors,
        )
    
    
    async def async_step_select_entities(self, user_input: Optional[Dict[str, Any]]=None):
        dr = async_get_device_registry(self.hass)
        er = async_get_entity_registry(self.hass)
        
        entries = async_entries_for_device(er, self.__current_device)
        entities = [e.entity_id for e in entries]
        
        if user_input is not None:
            registering_device = dr.async_get(self.__current_device)
            new_device = ListenedDeviceEntry(
                registering_device,
                user_input.get("listened_entities"),
                user_input.get("poll_time_s")
            )
            self.__new_registering_device.append(new_device)
            if user_input["add_next"]:
                return await self.async_step_select_device()
            
            for device in self.__new_registering_device:
                entry = er.async_get_or_create(
                    device_id=self.config_entry.runtime_data.hyperbase_device_id,
                    domain="notify",
                    platform="hyperbase",
                    unique_id=device.unique_id,
                    has_entity_name=True,
                    config_entry=self.config_entry,
                    original_name=device.original_name,
                    capabilities=device.capabilities
                )
                domains = await self.config_entry.runtime_data.async_add_configured_device(
                        device.capabilities.get("listened_device"),
                        device.capabilities.get("listened_entities"),
                        device.capabilities.get("poll_time_s"),
                    )
                self.config_entry.async_create_task(
                    self.hass,
                    self.config_entry.runtime_data.manager.async_revalidate_collections(domains))
                self.hass.states.async_set(entry.entity_id,
                                        datetime.datetime.now(), device.capabilities)
            
            # empty list of new added devices
            self.__new_registering_device.clear()
            return self.async_create_entry(
                title="new_device_config",
                data={}
            )
        
        return self.async_show_form(
            step_id="select_entities",
            data_schema=vol.Schema({
                vol.Required("listened_entities", default=entities): selector.EntitySelector(
                    config=selector.EntitySelectorConfig(
                        include_entities=entities,
                        multiple=True
                    )
                ),
                vol.Required("poll_time_s", default=5): int,
                vol.Required("add_next", default=False): selector.BooleanSelector()
            })
        )
    
    
    async def async_step_remove_device(self, user_input: Optional[Dict[str, Any]]=None):
        er = async_get_entity_registry(self.hass)
        entries = er.entities.get_entries_for_config_entry_id(self.config_entry.entry_id)
        entity_id = ""
        
        errors = {}
        
        for e in entries:
            if e.capabilities["listened_device"] == self.__current_device:
                entity_id = e.entity_id
                break
        
        if user_input is not None:
            if user_input[CONF_REMOVE_DEVICE_CONFIRM] != entity_id:
                errors["base"] = "invalid_id"
            else:
                er.async_remove(entity_id)
                
                return self.async_create_entry(
                    title="remove_device_config",
                    data={}
                )
        else:
            user_input = {}
        
        return self.async_show_form(
            step_id="remove_device",
            data_schema=vol.Schema({
                vol.Required(CONF_REMOVE_DEVICE_CONFIRM, default=user_input.get(CONF_REMOVE_DEVICE_CONFIRM, entity_id)): str
            }),
            errors=errors
        )