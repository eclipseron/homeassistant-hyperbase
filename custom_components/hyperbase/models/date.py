class DateColumns:
    def __init__(self):
        self.__columns = {
            "date": {"kind": "string", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class DateEntityData:
    def __init__(self, date_iso: str | None = None):
        self.__state_value = date_iso
    
    @property
    def data(self):
        return {"date": self.__state_value}