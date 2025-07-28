from typing import Any

class SatelliteColumns:
    def __init__(self):
        self.__columns = {
            "satellite": {"kind": "string", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class SatelliteEntityData:
    def __init__(self, state_value: Any | None = None):
        self.__state_value = state_value
    
    @property
    def data(self):
        if self.__state_value == "unknown":
            return {"satellite": None}
        return {"satellite": self.__state_value}