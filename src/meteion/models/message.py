import uuid

from enum import Enum


class CommandType(Enum):
    send_group_msg = "send_group_msg"


class Command(object):
    action: CommandType = None
    params: dict = None
    echo: str = None

    def __init__(self, action: CommandType, params: dict):
        self.action = action
        self.params = params
        self.echo = str(uuid.uuid4())

    def as_dict(self):
        return {"action": self.action.value, "params": self.params, "echo": self.echo}

    def __repr__(self):
        return f"Command<action={self.action.value}, params={self.params}>"


class TextMessage(object):
    data: dict | None = None

    def __init__(self, content: str):
        self.data = {
            "text": content
        }

    def as_dict(self):
        return {"type": "text", "data": self.data}


class ReplyMessage(object):
    data: dict | None = None

    def __init__(self, message_id: str):
        self.data = {
            "id": str(message_id)
        }

    def as_dict(self):
        return {"type": "reply", "data": self.data}
