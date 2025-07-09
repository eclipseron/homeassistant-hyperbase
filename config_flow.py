import datetime
from typing import Any, Dict, Optional
from uuid import uuid4
import httpx

from .registry import HyperbaseConnectorEntry, async_get_hyperbase_registry

from .util import get_model_identity, is_valid_connector_entity, format_device_name

from .exceptions import ConnectorEntityExists, HyperbaseHTTPError, HyperbaseRESTConnectivityError, InvalidConnectorEntity

from homeassistant.helpers import selector
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry, async_entries_for_device


from homeassistant import config_entries
from homeassistant.core import State, callback
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
    CONF_SERIAL_NUMBER,
    CONF_TOKEN_ID,
    LOGGER,
    DOMAIN,
    CONF_BASE_URL,
    CONF_PROJECT_ID,
    CONF_PROJECT_NAME,
    CONF_REST_ADDRESS,
    HYPERBASE_RESPONSE_CODE,
    HYPERBASE_RESPONSE_MSG,
)

def login(email: str, password: str, base_url: str="http://localhost:8080"):
    try:
        client = httpx.Client(verify=False)
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


def get_hyperbase_project(project_id:str, auth_token:str, base_url: str="http://localhost:8080"):
    try:
        client = httpx.Client(verify=False)
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


def ping_rest_server(base_url: str):
    try:
        client = httpx.Client(verify=False)
        _ = client.get(base_url)
        return {"success": True}
    except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
        LOGGER.error(exc)
        raise HyperbaseRESTConnectivityError(exc.args)


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
                self.__network_config = {
                    CONF_BASE_URL: base_url,
                }
                return await self.async_step_login()
            except HyperbaseRESTConnectivityError as exc:
                placeholders = {
                    HYPERBASE_RESPONSE_MSG: exc.args,
                    "network_type": "REST"
                }
            errors["base"] = "network_error"
            
        else:
            user_input = {}
        
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(
            {
                vol.Required(CONF_REST_ADDRESS, description="Hyperbase Backend Host", default=user_input.get(CONF_REST_ADDRESS, "http://localhost:8080")): str,
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
                
                serial_number = user_input.get(CONF_SERIAL_NUMBER, "")
                if serial_number == "":
                    serial_number = str(uuid4())
                
                return self.async_create_entry(
                    title=self.__project_config.get(CONF_PROJECT_NAME),
                    data={
                        CONF_BASE_URL: self.__network_config.get(CONF_BASE_URL),
                        CONF_AUTH_TOKEN: self.__auth_token,
                        CONF_PROJECT_ID: self.__project_config.get(CONF_PROJECT_ID),
                        CONF_PROJECT_NAME: self.__project_config.get(CONF_PROJECT_NAME),
                        CONF_API_TOKEN: user_input.get(CONF_TOKEN_ID),
                        CONF_SERIAL_NUMBER: serial_number,
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
            user_input = {}
        
        return self.async_show_form(
            step_id="login", 
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, description="Hyperbase Account Email", default=user_input.get(CONF_EMAIL, "")): str,
                    vol.Required(CONF_PASSWORD, description="Hyperbase Account Password", default=user_input.get(CONF_PASSWORD, "")): str,
                    vol.Required(CONF_PROJECT_ID, description="Hyperbase Project ID", default=user_input.get(CONF_PROJECT_ID, "")): str,
                    vol.Optional(CONF_SERIAL_NUMBER, default=user_input.get(CONF_SERIAL_NUMBER, "")): str,
                }
            ),
            errors=errors,
            description_placeholders=placeholders
        )
    
    # async def async_step_reconfigure(self, user_input: Optional[Dict[str, Any]] = None):
    #     """Step to reconfigure MQTT connection to Hyperbase"""
    #     errors = {}
        
    #     # retrieve previous entry
    #     entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
    #     new_entry = entry
    #     if new_entry is None:
    #         LOGGER.error("No previous entry found for reconfiguration")
    #         return self.async_abort(reason="no_previous_entry")
        
    #     if user_input is not None:
            
    #         await self.async_set_unique_id(new_entry.data[CONF_PROJECT_ID])
    #         self._abort_if_unique_id_mismatch()
    #         return self.async_update_reload_and_abort(
    #             title=new_entry.data[CONF_PROJECT_NAME],
    #             entry=new_entry,
    #             data_updates={},
    #         )
    #     else:
    #         user_input = {}
        
    #     return self.async_show_form(
    #         step_id="reconfigure", 
    #         data_schema=vol.Schema(
    #             {
    #                 vol.Required(CONF_MQTT_ADDRESS, default=new_entry.data[CONF_MQTT_ADDRESS]): str,
    #                 vol.Required(CONF_MQTT_PORT, default=new_entry.data[CONF_MQTT_PORT]): cv.port,
    #                 vol.Required(CONF_MQTT_TOPIC, default=new_entry.data[CONF_MQTT_TOPIC]): str,
    #             }
    #         ),
    #         errors=errors
    #     )


CONF_ADD_DEVICE = "add_device"
CONF_MANAGE_DEVICE = "manage_device"
CONF_REMOVE_DEVICE = "delete_device"

CONF_ACTIONS = {
    CONF_ADD_DEVICE: "Register New Device",
    CONF_MANAGE_DEVICE: "Manage Registered Devices",
    CONF_REMOVE_DEVICE: "Remove Registered Device",
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
                vol.Required(CONF_ENTITY_ID, default=user_input.get(CONF_ENTITY_ID, entities[0])): selector.EntitySelector(
                    config=selector.EntitySelectorConfig(
                        include_entities=entities
                        )),
            }),
        )
    
    
    async def __update_entity_capabilities(self, entity_id: str, capabilities: dict[str, Any], prev_state: State):
        er = async_get_entity_registry(self.hass)
        entity = er.async_update_entity(
            entity_id=entity_id,
            capabilities=capabilities,
            # config_entry_id=self.config_entry.entry_id,
            # device_id=self.config_entry.runtime_data.hyperbase_device_id,
            # has_entity_name=True,
            # original_name=entry.original_name,
        )
        
        # set updated configuration into corresponding entity attributes.
        # awaits the execution to make sure the attributes is updated before
        # continue the operation.
        await self.hass.async_add_executor_job(self.hass.states.set,
            entity.entity_id, prev_state.state, entity.capabilities, True)
    
    async def async_step_manage_connector(self, user_input: Optional[Dict[str, Any]]=None):
        er = async_get_entity_registry(self.hass)
        
        hyp = await async_get_hyperbase_registry(self.hass)
        connector = hyp.get_connector_entry(self.__current_connector_entity)
        
        
        listened_entity_domains: dict[str, list[str]] = {}
        listened_entities: list = connector._listened_entities
        prev_poll_time_s: int = connector._poll_time_s
        
        entity_entries = async_entries_for_device(er, connector._listened_device)
        for default_entity in entity_entries:
            if default_entity.original_device_class is None:
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
        connector_entity = f"{format_device_name(registering_device.name)}_{int(datetime.datetime.now().timestamp()*1000)}"
        
        schema = vol.Schema({
            vol.Required("connector_entity", default=connector_entity): str,
        })
        
        listened_entity_domains: dict[str, list[str]] = {}
        entity_entries = async_entries_for_device(er, self.__current_device)
        for entry in entity_entries:
            if entry.original_device_class is None:
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
                
                _entity = er.async_get_entity_id("notify", "hyperbase", f"{user_input.get("connector_entity")}_last_sent")
                if _entity is not None:
                    raise ConnectorEntityExists
                
                entry = er.async_get_or_create(
                        device_id=self.config_entry.runtime_data.hyperbase_device_id,
                        domain="notify",
                        platform="hyperbase",
                        unique_id=f"{user_input.get("connector_entity")}_last_sent",
                        has_entity_name=True,
                        config_entry=self.config_entry,
                        original_name=get_model_identity(registering_device),
                    )
                
                connector = HyperbaseConnectorEntry(
                    hass = self.hass,
                    connector_entity_id=entry.entity_id,
                    project_id=self.config_entry.data.get(CONF_PROJECT_ID),
                    listened_device=self.__current_device,
                    listened_entities=listened_entities,
                    poll_time_s=user_input.get("poll_time_s"),
                )
                
                await self.config_entry.runtime_data.async_add_new_listened_device(connector, entry.entity_id)
                
                hyperbase = await async_get_hyperbase_registry(self.hass)
                await hyperbase.async_store_connector_entry(connector)
                
                if user_input["add_next"]:
                    return await self.async_step_select_device()
                
                return self.async_create_entry(
                    title="new_device_config",
                    data={}
                )
            except InvalidConnectorEntity:
                errors["base"] = "invalid_entity"
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
            errors=errors
        )