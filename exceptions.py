from homeassistant.exceptions import HomeAssistantError

class HyperbaseMQTTConnectionError(HomeAssistantError):
    """Error to indicate a failure to connect to the Hyperbase MQTT server."""

class HyperbaseRESTConnectionError(HomeAssistantError):
    """Error to indicate a failure to connect to the Hyperbase REST server."""
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code