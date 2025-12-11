import json
import uuid

from websocket import WebSocketApp

from meteion.utils import CommandEncoder
from meteion.utils.logger import logger
from meteion.models.message import Command, CommandType, TextMessage


def echo_handler(ws: WebSocketApp, message: dict):
    group_id = message["group_id"]
    resp = message["raw_message"][6:]

    command = Command(action=CommandType.send_group_msg,
                      params={
                          "group_id": group_id,
                          "message": TextMessage(resp)
                      })

    logger.info(f"send command: {command}")
    ws.send(json.dumps(command, cls=CommandEncoder))


def on_error(ws, error):
    logger.error(error)


def on_message(ws, message):
    logger.info(message)
    message = json.loads(message)
    post_type = message.get("post_type", None)

    if post_type != "message" or message.get("message_type") != "group":
        return

    match message["raw_message"]:   
        case "/echo ":
            echo_handler(ws, message)
        case _:
            logger.info(message)


if __name__ == "__main__":
    a = Command(action=CommandType.send_group_msg, params={
        "group_id": str(uuid.uuid4()),
        "message": TextMessage("233"),
    })
    print(json.dumps(a, cls=CommandEncoder))
