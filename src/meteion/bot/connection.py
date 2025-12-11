from websocket import WebSocketApp
from typing import Optional

_ws_connection: Optional[WebSocketApp] = None


def set_ws_connection(ws: WebSocketApp):
    """Set the WebSocket connection instance"""
    global _ws_connection
    _ws_connection = ws


def get_ws_connection() -> Optional[WebSocketApp]:
    """Get the WebSocket connection instance"""
    return _ws_connection

