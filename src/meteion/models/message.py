import uuid

from enum import Enum


class CommandType(Enum):
    send_group_msg = "send_group_msg"
    send_group_forward_msg = "send_group_forward_msg"


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


class FileMessage(object):
    data: dict | None = None

    def __init__(self, file_path: str, name: str | None = None):
        self.data = {
            "file": file_path
        }
        if name:
            self.data["name"] = name

    def as_dict(self):
        return {"type": "file", "data": self.data}


class VideoMessage(object):
    data: dict | None = None

    def __init__(self, file_path: str):
        if not file_path.startswith(("file://", "http://", "https://")):
        if not file_path.startswith(("file://", "http://", "https://")):
            file_path = f"file://{file_path}"
        
        self.data = {
            "file": file_path
        }

    def as_dict(self):
        return {"type": "video", "data": self.data}


class ForwardNode(object):
    def __init__(self, user_id: str | int, nickname: str, content: list):
        self.data = {
            "user_id": user_id,
            "nickname": nickname,
            "content": [msg.as_dict() if hasattr(msg, 'as_dict') else msg for msg in content]
        }
    
    def as_dict(self):
        return {"type": "node", "data": self.data}
