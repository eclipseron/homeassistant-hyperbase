class SelectColumns:
    def __init__(self):
        self.__columns = {
            "selected_option": {"kind": "string", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class SelectEntityData:
    def __init__(self, state_value: str | None = None):
        self.__state_value = state_value
    
    @property
    def data(self):
        return {"selected_option": self.__state_value}