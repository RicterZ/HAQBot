"""Shared utilities for sending responses and running async tasks"""
import json
import asyncio
from typing import Optional
from websocket import WebSocketApp

from maid.models.message import Command, CommandType, TextMessage, ReplyMessage
from maid.utils import CommandEncoder


def send_response(ws: WebSocketApp, group_id: str, message_id: Optional[str], response_text: str):
    """Helper function to send response message"""
    message_segments = []
    if message_id:
        message_segments.append(ReplyMessage(message_id))
    message_segments.append(TextMessage(response_text))
    
    command = Command(
        action=CommandType.send_group_msg,
        params={
            "group_id": group_id,
            "message": [msg.as_dict() for msg in message_segments]
        }
    )
    ws.send(json.dumps(command, cls=CommandEncoder))


def run_async_task(coro):
    """Helper function to run async task in separate thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()

