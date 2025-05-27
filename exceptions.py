from homeassistant.exceptions import HomeAssistantError

class HyperbaseMQTTConnectionError(HomeAssistantError):
    """Error to indicate a failure to connect to the Hyperbase MQTT server."""