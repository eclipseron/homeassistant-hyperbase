class SirenColumns:
    def __init__(self):
        self.__columns = {
            "siren_is_on": {"kind": "boolean", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class SirenEntityData:
    def __init__(self, state_value: bool | None = None):
        self.__state_value = state_value
    
    @property
    def data(self):
        return {"siren_is_on": self.__state_value}