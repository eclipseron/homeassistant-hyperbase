from typing import Any, Dict, Optional
import httpx

from .hyperbase_mqtt import HyperbaseMQTT
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

def login(username: str, password: str, base_url: str="http://localhost:8080"):
    try:
        client = httpx.Client()
        r = client.post(f"{base_url}/api/rest/auth/password-based",
                                json={"email": username, "password": password})
        r.raise_for_status()
        return {"success": True, "token": r.json()["data"]["token"]}
    except httpx.ConnectTimeout as exc:
        return {"success": False, "code": 0, "msg": f"Connection to host timed out"}
    except httpx.ConnectError as exc:
        return {"success": False, "code": 0, "msg": f"Failed to connect to host"}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "code": exc.response.status_code, "msg": exc.response.json()['error']['status']}


def get_hyperbase_project(project_id:str, token:str, base_url: str="http://localhost:8080"):
    try:
        client = httpx.Client()
        client.headers.update({"Authorization": f"Bearer {token}"})
        r = client.get(f"{base_url}/api/rest/project/{project_id}")
        r.raise_for_status()
        return {"success": True, "data": r.json()["data"]}
    except httpx.ConnectError as exc:
        return {"success": False, "code": 0, "msg": f"Failed to connect to host"}
    except httpx.ConnectTimeout as exc:
        return {"success": False, "code": 0, "msg": f"Connection to host timed out"}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "code": exc.response.status_code, "msg": exc.response.json()['error']['status']}



class HyperbaseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    __network_rest_address: str
    __network_base_url: str
    __auth_token: str
    __project_config: Dict[str, Any]
    
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow for this handler."""
        return HyperbaseOptionsFlowHandler()
    
    
    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Step for creating new hyperbase connection"""
        errors = {}
        placeholders = {}
        if user_input is not None:
            base_url = f"{user_input[CONF_REST_PROTOCOL]}://{user_input[CONF_REST_ADDRESS]}:{user_input[CONF_REST_PORT]}"
            success, res =  await self.__async_login(
                user_input[CONF_EMAIL],
                user_input[CONF_PASSWORD],
                base_url,
            )
            if success:
                self.__network_rest_address = user_input[CONF_REST_ADDRESS]
                self.__network_base_url = base_url
                return await self.async_step_configure_project()
            errors["base"] = "login_error"
            placeholders = {
                HYPERBASE_RESPONSE_CODE: res[HYPERBASE_RESPONSE_CODE],
                HYPERBASE_RESPONSE_MSG: res[HYPERBASE_RESPONSE_MSG],
            }
        else:
            user_input = {}
        
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(
            {
                vol.Required(CONF_REST_ADDRESS, description="Hyperbase Backend Host", default=user_input.get(CONF_REST_ADDRESS, "localhost")): str,
                vol.Required(CONF_REST_PROTOCOL, description="Hyperbase REST Protocol", default=user_input.get(CONF_REST_PROTOCOL, "http")): vol.In(cv.EXTERNAL_URL_PROTOCOL_SCHEMA_LIST),
                vol.Required(CONF_REST_PORT, description="Hyperbase Backend REST Port", default=user_input.get(CONF_REST_PORT, 8080)): cv.port,
                vol.Required(CONF_EMAIL, description="Hyperbase email", default=""): str,
                vol.Required(CONF_PASSWORD, description="Hyperbase password", default=""): str,
            }),
            errors=errors,
            description_placeholders=placeholders,
        )
    
    
    async def async_step_setup_mqtt(self, user_input: Optional[Dict[str, Any]] = None):
        """Step to config MQTT connection to Hyperbase"""
        errors = {}
        if user_input is not None:
            return self.async_create_entry(
                    title=self.__project_config[CONF_PROJECT_NAME],
                    data={
                        CONF_BASE_URL: self.__network_base_url,
                        CONF_MQTT_ADDRESS: user_input[CONF_MQTT_ADDRESS],
                        CONF_MQTT_PORT: user_input[CONF_MQTT_PORT],
                        CONF_MQTT_TOPIC: user_input[CONF_MQTT_TOPIC],
                        CONF_TOKEN: self.__auth_token,
                        CONF_PROJECT_ID: self.__project_config[CONF_PROJECT_ID],
                        CONF_PROJECT_NAME: self.__project_config[CONF_PROJECT_NAME],
                        },
                    description=f"Project ID: {self.__project_config[CONF_PROJECT_NAME]}",
                )
        else:
            user_input = {}
        
        return self.async_show_form(
            step_id="setup_mqtt", data_schema=vol.Schema(
            {
                vol.Required(CONF_MQTT_ADDRESS, description="Hyperbase Backend Host", default=user_input.get(CONF_MQTT_ADDRESS, self.__network_rest_address)): str,
                vol.Required(CONF_MQTT_PORT, description="Hyperbase MQTT Port", default=user_input.get(CONF_MQTT_PORT, 1883)): cv.port,
                vol.Required(CONF_MQTT_TOPIC, description="Hyperbase MQTT Topic", default=user_input.get(CONF_MQTT_TOPIC, "hyperbase")): str,
            }),
            errors=errors
        )
    
    
    async def async_step_configure_project(self, user_input: Optional[Dict[str, Any]] = None):
        """Step to specify target project ID to collect data into Hyperbase"""
        errors = {}
        if user_input is not None:
            success, res = await self.__async_get_project(
                user_input.get(CONF_PROJECT_ID),
                self.__auth_token,
                self.__network_base_url,
            )
            if success:
                await self.async_set_unique_id(user_input.get(CONF_PROJECT_ID))
                self._abort_if_unique_id_configured()
                return await self.async_step_setup_mqtt()
            
            if res.get(HYPERBASE_RESPONSE_CODE, 0) == 0:
                errors["base"] = res.get(HYPERBASE_RESPONSE_MSG, "Unknown error")
            else:
                errors["base"] = f"Failed to configure project ({res.get(HYPERBASE_RESPONSE_CODE)}): {res.get(HYPERBASE_RESPONSE_MSG)}"
        else:
            user_input = {}
        
        return self.async_show_form(
            step_id="configure_project", 
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROJECT_ID, description="Hyperbase Project ID", default=user_input.get(CONF_PROJECT_ID, "")): str,
                }
            ),
            errors=errors
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
    
    
    async def __async_get_project(self, project_id, token: str, base_url: str):
        res = await self.hass.async_add_executor_job(
            get_hyperbase_project,
            project_id,
            token,
            base_url,
        )
        success: bool = res.get(HYPERBASE_RESPONSE_SUCCESS)
        if success:
            self.__project_config = {
                CONF_PROJECT_ID: project_id,
                CONF_PROJECT_NAME: res["data"][CONF_NAME],
            }
            LOGGER.info("Project configured successfully")
        return success, res
    
    
    async def __async_login(self, user_email, user_password, base_url):
        res = await self.hass.async_add_executor_job(
            login,
            user_email,
            user_password,
            base_url,
        )
        success: bool = res.get(HYPERBASE_RESPONSE_SUCCESS)
        if success:
            self.__auth_token = res.get(HYPERBASE_RESPONSE_TOKEN)
            LOGGER.info("Hyperbase login successful")
        return success, res


CONF_SETUP_MQTT = "setup_mqtt"
CONF_ADD_DEVICE = "add_device"
CONF_REMOVE_DEVICE = "remove_device"


CONF_ACTIONS = {
    CONF_SETUP_MQTT: "Configure MQTT Address, Port, and topic to Hyperbase",
    CONF_ADD_DEVICE: "Add Device Integration",
    CONF_REMOVE_DEVICE: "Remove Device Integration",
}


class HyperbaseOptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input):
        if user_input is not None:
            if user_input[CONF_ACTION] == CONF_SETUP_MQTT:
                return await self.async_step_setup_mqtt()
    
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACTION, default=CONF_ADD_DEVICE): vol.In(CONF_ACTIONS),
                }
            )
        )
    
    
    async def async_step_setup_mqtt(self, user_input: Optional[dict[str, Any]] = None):
        if user_input is not None:
            new_entry = self.config_entry.data.copy()
            new_entry.update(user_input)
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=new_entry
            )
            return self.async_create_entry(
                title=new_entry[CONF_PROJECT_NAME],
                data={},
            )
        else:
            user_input = {}
        
        return self.async_show_form(
            step_id="setup_mqtt",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MQTT_ADDRESS, default=self.config_entry.data.get(CONF_MQTT_ADDRESS, "localhost")): str,
                    vol.Required(CONF_MQTT_PORT, default=self.config_entry.data.get(CONF_MQTT_PORT, 1883)): cv.port,
                    vol.Required(CONF_MQTT_TOPIC, default=self.config_entry.data.get(CONF_MQTT_TOPIC, "hyperbase")): str,
                }
            )
        )