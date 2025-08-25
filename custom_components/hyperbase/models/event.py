class EventColumns:
    def __init__(self):
        self.__columns = {
            "event": {"kind": "string", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class EventEntityData:
    def __init__(self, state_value: str | None = None):
        self.__state_value = state_value
    
    @property
    def data(self):
        return {"event": self.__state_value}