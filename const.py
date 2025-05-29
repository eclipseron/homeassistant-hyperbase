
import logging

from homeassistant.loader import MQTT
from homeassistant.util.hass_dict import HassKey


class HyperbaseConfig:
    config: dict[str, str] = {}

DOMAIN="hyperbase"
LOGGER = logging.getLogger(__package__)

HYPERBASE_CONFIG: HassKey[HyperbaseConfig] = HassKey(DOMAIN)

CONF_BASE_URL = "base_url"
CONF_MQTT_ADDRESS = "mqtt_address"
CONF_MQTT_PORT = "mqtt_port"
CONF_MQTT_PROTOCOL = "mqtt_protocol"
CONF_MQTT_TOPIC = "mqtt_topic"
CONF_PROJECT_ID = "project_id"
CONF_PROJECT_NAME = "project_name"
CONF_REST_ADDRESS = "rest_address"
CONF_REST_PORT = "rest_port"
CONF_REST_PROTOCOL = "rest_protocol"
CONF_REST_TOKEN = "token"

HYPERBASE_AUTH_ENDPOINT = "/api/rest/auth/password-based"

HYPERBASE_RESPONSE_CODE = "code"
HYPERBASE_RESPONSE_MSG = "msg"
HYPERBASE_RESPONSE_SUCCESS = "success"
HYPERBASE_RESPONSE_TOKEN = "token"

MQTT_CONNECTED = "hyperbase_mqtt_connected"
MQTT_DISCONNECTED = "hyperbase_mqtt_disconnected"