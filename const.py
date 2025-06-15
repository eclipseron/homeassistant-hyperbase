
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
CONF_AUTH_TOKEN = "auth_token"
CONF_TOKEN_ID = "token_id"
CONF_SERIAL_NUMBER = "serial_number"

HYPERBASE_RESPONSE_CODE = "code"
HYPERBASE_RESPONSE_MSG = "msg"

MQTT_CONNECTED = "hyperbase_mqtt_connected"
MQTT_DISCONNECTED = "hyperbase_mqtt_disconnected"