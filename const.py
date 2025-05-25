
import logging


DOMAIN="hyperbase"
LOGGER = logging.getLogger(__package__)

CONF_MQTT_ADDRESS = "mqtt_address"
CONF_REST_ADDRESS = "rest_address"
CONF_MQTT_PORT = "mqtt_port"
CONF_REST_PORT = "rest_port"
CONF_REST_PROTOCOL = "rest_protocol"
CONF_MQTT_PROTOCOL = "mqtt_protocol"

HYPERBASE_AUTH_ENDPOINT = "/api/rest/auth/password-based"

HYPERBASE_RESPONSE_CODE = "code"
HYPERBASE_RESPONSE_SUCCESS = "success"
HYPERBASE_RESPONSE_TOKEN = "token"