from typing import Any, Dict, Optional
import httpx

from .hyperbase_mqtt import HyperbaseMQTT
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from .const import CONF_MQTT_ADDRESS, CONF_MQTT_PORT, CONF_REST_ADDRESS, CONF_REST_PORT, CONF_REST_PROTOCOL, DOMAIN, HYPERBASE_RESPONSE_SUCCESS, HYPERBASE_RESPONSE_TOKEN
from .const import LOGGER

def login(username: str, password: str, base_url: str="http://localhost:8080"):
    try:
        client = httpx.Client()
        r = client.post(f"{base_url}/api/rest/auth/password-based",
                                json={"email": username, "password": password})
        r.raise_for_status()
        return {"success": True, "token": r.json()["data"]["token"]}
    except httpx.ConnectError as exc:
        return {"success": False, "code": 0, "msg": "Failed to connect to host"}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "code": exc.response.status_code, "msg": exc.response.json()['error']['status']}


class HyperbaseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    
    data: Optional[Dict[str, Any]]
    
    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Step for creating new hyperbase connection"""
        errors: Dict[str, str] = {}
        if user_input is not None:
            self.data = user_input
            success, res =  await self.__async_login()
            if success:
                return await self.async_step_setup_mqtt()
        
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(
            {
                vol.Required(CONF_REST_ADDRESS, description="Hyperbase Backend Host", default="localhost"): str,
                vol.Required(CONF_REST_PROTOCOL, description="Hyperbase REST Protocol", default="http"): vol.In(cv.EXTERNAL_URL_PROTOCOL_SCHEMA_LIST),
                vol.Required(CONF_REST_PORT, description="Hyperbase Backend REST Port", default=8080): cv.port,
                vol.Required(CONF_EMAIL, description="Hyperbase email", default=""): str,
                vol.Required(CONF_PASSWORD, description="Hyperbase password", default=""): str,
            }),
            errors=errors,
        )
    
    
    async def async_step_setup_mqtt(self, user_input: Optional[Dict[str, Any]] = None):
        errors: Dict[str, str] = {}
        if user_input is not None:
            mq = HyperbaseMQTT(user_input[CONF_MQTT_ADDRESS], user_input[CONF_MQTT_PORT])
            mq.connectTCP()
            return self.async_create_entry(title="Hyperbase connection", data=self.data)
        
        return self.async_show_form(
            step_id="setup_mqtt", data_schema=vol.Schema(
            {
                vol.Required(CONF_MQTT_ADDRESS, description="Hyperbase Backend Host", default=self.data[CONF_REST_ADDRESS]): str,
                vol.Required(CONF_MQTT_PORT, description="Hyperbase MQTT port", default=8183): cv.port,
            }),
            errors=errors
        )
    
    
    async def __async_login(self):
        res = await self.hass.async_add_executor_job(
            login,
            self.data[CONF_EMAIL],
            self.data[CONF_PASSWORD],
            f"{self.data[CONF_REST_PROTOCOL]}://{self.data[CONF_REST_ADDRESS]}:{self.data[CONF_REST_PORT]}"
        )
        success: bool = res.get(HYPERBASE_RESPONSE_SUCCESS, False)
        if success:
            self.data[HYPERBASE_RESPONSE_TOKEN] = res.get(HYPERBASE_RESPONSE_TOKEN)
            LOGGER.info("Hyperbase login successful")
        return success, res