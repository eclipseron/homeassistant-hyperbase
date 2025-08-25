class ConversationColumns:
    def __init__(self):
        self.__columns = {
            "conversation": {"kind": "string", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class ConversationEntityData:
    def __init__(self, state_value: str | None = None):
        self.__state_value = state_value
    
    @property
    def data(self):
        return {"conversation": self.__state_value}