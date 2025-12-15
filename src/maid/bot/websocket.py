"""WebSocket client for NapCat QQ bot"""
import json
import os
import asyncio
import threading
from typing import Optional, List

from websocket import WebSocketApp

from maid.utils.logger import logger
from maid.utils.entity_cache import load_entity_cache
from maid.bot.connection import set_ws_connection

# Import all command handlers
from maid.bot.handlers.commands import (
    turn_on_handler,
    turn_off_handler,
    toggle_handler,
    climate_handler,
    script_handler,
)
from maid.bot.handlers.info import (
    info_handler,
    light_handler,
    switch_handler,
    search_handler,
)
from maid.bot.handlers.system import (
    echo_handler,
    clear_handler,
    help_handler,
    refresh_handler,
)
from maid.bot.handlers.conversation import conversation_handler


def _get_allowed_senders() -> Optional[List[str]]:
    """Get list of allowed sender QQ numbers from environment variable
    
    Returns:
        List of allowed QQ numbers, or None if all users are allowed
    """
    allowed = os.getenv("ALLOWED_SENDERS", "").strip()
    if not allowed:
        return None
    
    # Support comma or space separated QQ numbers
    qq_list = [qq.strip() for qq in allowed.replace(",", " ").split() if qq.strip()]
    return qq_list if qq_list else None


def _get_allowed_groups() -> Optional[List[str]]:
    """Get list of allowed group QQ numbers from environment variable
    
    Returns:
        List of allowed group QQ numbers, or None if all groups are allowed
    """
    allowed = os.getenv("ALLOWED_GROUPS", "").strip()
    if not allowed:
        return None
    
    # Support comma or space separated QQ numbers (same as ALLOWED_SENDERS)
    qq_list = [qq.strip() for qq in allowed.replace(",", " ").split() if qq.strip()]
    return qq_list if qq_list else None


def _is_sender_allowed(message: dict) -> bool:
    """Check if the sender is allowed to control devices
    
    Args:
        message: Message dictionary from WebSocket
    
    Returns:
        True if sender is allowed, False otherwise
    """
    allowed_senders = _get_allowed_senders()
    
    if allowed_senders is None:
        return True
    
    # Try multiple possible field names for user ID
    user_id = message.get("user_id") or message.get("sender_id")
    
    if not user_id:
        logger.warning(f"Cannot determine sender QQ number from message. Available keys: {list(message.keys())}")
        return False
    
    user_id_str = str(user_id)
    return user_id_str in allowed_senders


def _is_group_allowed(message: dict) -> bool:
    """Check if the group is allowed to receive bot responses
    
    Args:
        message: Message dictionary from WebSocket
    
    Returns:
        True if group is allowed, False otherwise
    """
    allowed_groups = _get_allowed_groups()
    
    if allowed_groups is None:
        return True
    
    # Get group ID from message
    group_id = message.get("group_id")
    
    if not group_id:
        logger.warning(f"Cannot determine group QQ number from message. Available keys: {list(message.keys())}")
        return False
    
    group_id_str = str(group_id)
    return group_id_str in allowed_groups


def on_error(ws, error):
    """WebSocket error handler"""
    logger.error(error)


def on_open(ws):
    """WebSocket connection opened"""
    set_ws_connection(ws)
    logger.info("WebSocket connection established")
    
    def load_cache():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(load_entity_cache())
        finally:
            loop.close()
    
    cache_thread = threading.Thread(target=load_cache, daemon=True)
    cache_thread.start()


def on_message(ws, message):
    """WebSocket message handler - routes commands to appropriate handlers"""
    message = json.loads(message)
    post_type = message.get("post_type", None)

    if post_type != "message" or message.get("message_type") != "group":
        return

    raw_message = message.get("raw_message", "").strip()
    if not _is_sender_allowed(message):
        return
    
    if not _is_group_allowed(message):
        return
    
    # Route commands to appropriate handlers
    if raw_message.startswith("/echo "):
        echo_handler(ws, message)
    elif raw_message == "/clear":
        clear_handler(ws, message)
    elif raw_message.startswith("/turnon "):
        turn_on_handler(ws, message)
    elif raw_message.startswith("/turnoff "):
        turn_off_handler(ws, message)
    elif raw_message.startswith("/toggle "):
        toggle_handler(ws, message)
    elif raw_message == "/info":
        info_handler(ws, message)
    elif raw_message == "/light":
        light_handler(ws, message)
    elif raw_message == "/switch":
        switch_handler(ws, message)
    elif raw_message.startswith("/script "):
        script_handler(ws, message)
    elif raw_message.startswith("/climate "):
        climate_handler(ws, message)
    elif raw_message.startswith("/search "):
        search_handler(ws, message)
    elif raw_message == "/refresh":
        refresh_handler(ws, message)
    elif raw_message == "/help":
        help_handler(ws, message)
    elif raw_message:
        # Default: treat as natural language conversation
        conversation_handler(ws, message)
