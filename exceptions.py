from homeassistant.exceptions import HomeAssistantError

class HyperbaseMQTTConnectionError(HomeAssistantError):
    """Error to indicate a failure to connect to the Hyperbase MQTT server."""

class HyperbaseRESTConnectionError(HomeAssistantError):
    """Error to indicate a failure to connect to the Hyperbase REST server."""
    def __init__(self, *args: object, status_code: int=0):
        super().__init__(*args)
        self.status_code = status_code

class HyperbaseRESTConnectivityError(HomeAssistantError):
    """Error to indicate a failure to connect to the Hyperbase REST server."""

class HyperbaseHTTPError(HomeAssistantError):
    """Error to indicate authentication error to Hyperbase REST server"""
    def __init__(self,
        *args: object,
        status_code: int | None = None,
        translation_domain: str | None = None,
        translation_key: str | None = None,
        translation_placeholders: dict[str, str] | None = None):
        
        super().__init__(
            *args,
            translation_domain,
            translation_key,
            translation_placeholders
        )
        
        self.status_code = status_code


class InvalidConnectorEntity(Exception):
    """Error to indicate invalid hyperbase connector entity name"""

class ConnectorEntityExists(Exception):
    """Error to indicate hyperbase connector is already registered"""