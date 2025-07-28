class LawnMowerColumns:
    def __init__(self):
        self.__columns = {
            "lawn_mower": {"kind": "string", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class LawnMowerEntityData:
    def __init__(self, state_value: str | None = None):
        self.__state_value = state_value
    
    @property
    def data(self):
        return {"lawn_mower": self.__state_value}