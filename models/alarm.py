from typing import Any

class AlarmColumns:
    def __init__(self):
        self.__columns = {
            "alarm": {"kind": "string", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class AlarmEntityData:
    def __init__(self, state_value: Any | None = None):
        self.__state_value = state_value
    
    @property
    def data(self):
        if self.__state_value == "unknown":
            return {"alarm": None}
        return {"alarm": self.__state_value}