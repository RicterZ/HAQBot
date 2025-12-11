import os
import uuid

from enum import Enum


class CommandType(Enum):
    send_group_msg = "send_group_msg"
    send_group_forward_msg = "send_group_forward_msg"
    download_file = "download_file"


class MessageType(Enum):
    text = "text"
    markdown = "markdown"
    node = "node"


class Message(object):
    type_: MessageType = None
    data: dict

    def __init__(self, type_: MessageType, content: list):
        self.type_ = type_
        self.data = {
            "user_id": os.getenv("ACCOUNT", "2167634556"),
            "content": content
        }

    def as_dict(self):
        return {"type": self.type_.value, "data": self.data}

    def __repr__(self):
        return f"Message<type={self.type_.value}, data={self.data}>"


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


class ImageMessage(object):
    data: dict | None = None

    def __init__(self, file: str):
        self.data = {
            "file": file
        }

    def as_dict(self):
        return {"type": "image", "data": self.data}


class ReplyMessage(object):
    """Reply message segment for referencing original message"""
    data: dict | None = None

    def __init__(self, message_id: str):
        """
        Initialize reply message
        
        Args:
            message_id: ID of the message to reply to
        """
        self.data = {
            "id": str(message_id)
        }

    def as_dict(self):
        return {"type": "reply", "data": self.data}
