class RemoteColumns:
    def __init__(self):
        self.__columns = {
            "remote": {"kind": "string", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class RemoteEntityData:
    def __init__(self, state_value: str | None = None):
        self.__state_value = state_value
    
    @property
    def data(self):
        return {"remote": self.__state_value}