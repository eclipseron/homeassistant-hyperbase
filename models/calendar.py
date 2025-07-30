class CalendarColumns:
    def __init__(self):
        self.__columns = {
            "calendar": {"kind": "string", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class CalendarEntityData:
    def __init__(self, state_value: str | None = None):
        self.__state_value = state_value
    
    @property
    def data(self):
        return {"calendar": self.__state_value}