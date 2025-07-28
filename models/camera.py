from typing import Any

class CameraColumns:
    def __init__(self):
        self.__columns = {
            "camera": {"kind": "string", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class CameraEntityData:
    def __init__(self, state_value: Any | None = None):
        self.__state_value = state_value
    
    @property
    def data(self):
        if self.__state_value == "unknown":
            return {"camera": None}
        return {"camera": self.__state_value}