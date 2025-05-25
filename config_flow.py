from typing import Any, Dict, Optional
import httpx

from .hyperbase_mqtt import HyperbaseMQTT
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import CONF_EMAIL, CONF_ID, CONF_NAME, CONF_PASSWORD, CONF_TOKEN
from .const import CONF_BASE_URL, CONF_MQTT_ADDRESS, CONF_MQTT_PORT, CONF_PROJECT_ID, CONF_PROJECT_NAME, CONF_REST_ADDRESS, CONF_REST_PORT, CONF_REST_PROTOCOL, DOMAIN, HYPERBASE_RESPONSE_CODE, HYPERBASE_RESPONSE_MSG, HYPERBASE_RESPONSE_SUCCESS, HYPERBASE_RESPONSE_TOKEN
from .const import LOGGER

def login(username: str, password: str, base_url: str="http://localhost:8080"):
    try:
        client = httpx.Client()
        r = client.post(f"{base_url}/api/rest/auth/password-based",
                                json={"email": username, "password": password})
        r.raise_for_status()
        return {"success": True, "token": r.json()["data"]["token"]}
    except httpx.ConnectError as exc:
        return {"success": False, "code": 0, "msg": f"Failed to connect to host"}
    except httpx.ConnectTimeout as exc:
        return {"success": False, "code": 0, "msg": f"Connection to host timed out"}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "code": exc.response.status_code, "msg": exc.response.json()['error']['status']}


def get_hyperbase_project(project_id:str, token:str, base_url: str="http://localhost:8080"):
    try:
        LOGGER.info(f"{project_id} | {token}")
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
    __network_config: Dict[str, Any]
    __project_config: Dict[str, Any]
    
    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Step for creating new hyperbase connection"""
        errors = {}
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
                return await self.async_step_setup_mqtt()

            if res.get(HYPERBASE_RESPONSE_CODE, 0) == 0:
                errors["base"] = res.get(HYPERBASE_RESPONSE_MSG, "Unknown error")
            else:
                errors["base"] = f"Login failed: {res.get(HYPERBASE_RESPONSE_MSG)}"
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
        )
    
    
    async def async_step_setup_mqtt(self, user_input: Optional[Dict[str, Any]] = None):
        errors = {}
        if user_input is not None:
            mq = HyperbaseMQTT(user_input[CONF_MQTT_ADDRESS], user_input[CONF_MQTT_PORT])
            response = mq.pingTCP()
            success = response.get(HYPERBASE_RESPONSE_SUCCESS, False)
            if success:
                self.__network_config = {
                    CONF_MQTT_ADDRESS: user_input[CONF_MQTT_ADDRESS],
                    CONF_MQTT_PORT: user_input[CONF_MQTT_PORT],
                    CONF_BASE_URL: self.__network_base_url,
                }
                return await self.async_step_configure_project()
            
            if response.get(HYPERBASE_RESPONSE_CODE) == 136:
                errors["base"] = response.get(HYPERBASE_RESPONSE_MSG, "Unknown error")
        else:
            user_input = {}
        
        return self.async_show_form(
            step_id="setup_mqtt", data_schema=vol.Schema(
            {
                vol.Required(CONF_MQTT_ADDRESS, description="Hyperbase Backend Host", default=user_input.get(CONF_MQTT_ADDRESS, self.__network_rest_address)): str,
                vol.Required(CONF_MQTT_PORT, description="Hyperbase MQTT port", default=user_input.get(CONF_MQTT_PORT, 1883)): cv.port,
            }),
            errors=errors
        )
    
    
    async def async_step_configure_project(self, user_input: Optional[Dict[str, Any]] = None):
        errors = {}
        LOGGER.info(self.__network_config)
        if user_input is not None:
            success, res = await self.__async_get_project(
                user_input.get(CONF_PROJECT_ID),
                self.__auth_token,
                self.__network_config[CONF_BASE_URL],
            )
            if success:
                return self.async_create_entry(
                    title=self.__project_config[CONF_PROJECT_NAME],
                    data={
                        CONF_BASE_URL: self.__network_config[CONF_BASE_URL],
                        CONF_MQTT_ADDRESS: self.__network_config[CONF_MQTT_ADDRESS],
                        CONF_MQTT_PORT: self.__network_config[CONF_MQTT_PORT],
                        CONF_TOKEN: self.__auth_token,
                        CONF_PROJECT_ID: self.__project_config[CONF_PROJECT_ID],
                        CONF_PROJECT_NAME: self.__project_config[CONF_PROJECT_NAME],
                        },
                    description=f"Project ID: {self.__project_config[CONF_PROJECT_NAME]}",
                )
            
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