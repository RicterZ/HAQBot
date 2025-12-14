"""System command handlers"""
import json
import os
import threading
from typing import Optional, List, Dict

from websocket import WebSocketApp

from maid.utils import CommandEncoder
from maid.utils.logger import logger
from maid.utils.i18n import t
from maid.utils.response import send_response, run_async_task
from maid.models.message import Command, CommandType, TextMessage
from maid.bot.handlers.conversation import clear_conversation_context
from maid.utils.entity_cache import load_entity_cache


def echo_handler(ws: WebSocketApp, message: dict):
    """Handle /echo command"""
    group_id = message["group_id"]
    resp = message["raw_message"][6:]

    command = Command(action=CommandType.send_group_msg,
                      params={
                          "group_id": group_id,
                          "message": TextMessage(resp)
                      })

    logger.info(f"send command: {command}")
    ws.send(json.dumps(command, cls=CommandEncoder))


def clear_handler(ws: WebSocketApp, message: dict):
    """Handle /clear command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    
    cleared = clear_conversation_context(group_id)
    response_text = t("conversation_context_cleared") if cleared else t("no_conversation_context")
    send_response(ws, group_id, message_id, response_text)


def _get_commands_list() -> List[Dict[str, str]]:
    """Get list of all supported commands with descriptions
    
    Returns:
        List of command dictionaries with 'command', 'description', and 'emoji' keys
    """
    return [
        {
            "command": "/help",
            "description": t("help_command_description"),
            "emoji": "📋"
        },
        {
            "command": "/info",
            "description": t("info_command_description"),
            "emoji": "🏠"
        },
        {
            "command": "/turnon <entity_id> [<entity_id2> ...]",
            "description": t("turnon_command_description"),
            "emoji": "💡"
        },
        {
            "command": "/turnoff <entity_id> [<entity_id2> ...]",
            "description": t("turnoff_command_description"),
            "emoji": "🔌"
        },
        {
            "command": "/toggle <entity_id> [<entity_id2> ...]",
            "description": t("toggle_command_description"),
            "emoji": "🔄"
        },
        {
            "command": "/light",
            "description": t("light_command_description"),
            "emoji": "💡"
        },
        {
            "command": "/switch",
            "description": t("switch_command_description"),
            "emoji": "🔌"
        },
        {
            "command": "/script <script_id>",
            "description": t("script_command_description"),
            "emoji": "📜"
        },
        {
            "command": "/climate <entity_id> [mode] [temp]",
            "description": t("climate_command_description"),
            "emoji": "❄️"
        },
        {
            "command": "/search <query>",
            "description": t("search_command_description"),
            "emoji": "🔍"
        },
        {
            "command": "/refresh",
            "description": t("refresh_command_description"),
            "emoji": "🔄"
        },
        {
            "command": "/clear",
            "description": t("clear_command_description"),
            "emoji": "🗑️"
        },
        {
            "command": "/echo <text>",
            "description": t("echo_command_description"),
            "emoji": "📢"
        },
    ]


def help_handler(ws: WebSocketApp, message: dict):
    """Handle /help command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    
    commands = _get_commands_list()
    
    lines = []
    # Get display nickname dynamically
    display_nickname = os.getenv("DISPLAY_NICKNAME", "メイド")
    lines.append(t("help_header", nickname=display_nickname))
    
    for cmd_info in commands:
        emoji = cmd_info.get("emoji", "•")
        lines.append(f"{emoji} {cmd_info['command']} - {cmd_info['description']}")
    
    response_text = "\n".join(lines)
    send_response(ws, group_id, message_id, response_text)


async def _refresh_cache_task(ws: WebSocketApp, group_id: str, message_id: Optional[str]):
    """Async task: refresh entity cache"""
    try:
        logger.info("Refreshing entity cache...")
        success = await load_entity_cache()
        
        if success:
            response_text = t("cache_refreshed")
        else:
            response_text = t("cache_refresh_failed")
        
        send_response(ws, group_id, message_id, response_text)
    except Exception as e:
        logger.error(f"Error refreshing cache: {e}", exc_info=True)
        send_response(ws, group_id, message_id, t("error_processing_command", error=str(e)))


def refresh_handler(ws: WebSocketApp, message: dict):
    """Handle /refresh command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    
    task = _refresh_cache_task(ws, group_id, message_id)
    thread = threading.Thread(target=run_async_task, args=(task,), daemon=True)
    thread.start()

