class ButtonColumns:
    def __init__(self):
        self.__columns = {
            "button": {"kind": "string", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class ButtonEntityData:
    def __init__(self, state_value: str | None = None):
        self.__state_value = state_value
    
    @property
    def data(self):
        return {"button": self.__state_value}