"""Command handlers for WebSocket bot"""
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
from maid.bot.handlers.conversation import (
    conversation_handler,
    clear_conversation_context,
)

__all__ = [
    # Commands
    "turn_on_handler",
    "turn_off_handler",
    "toggle_handler",
    "climate_handler",
    "script_handler",
    # Info
    "info_handler",
    "light_handler",
    "switch_handler",
    "search_handler",
    # System
    "echo_handler",
    "clear_handler",
    "help_handler",
    "refresh_handler",
    # Conversation
    "conversation_handler",
    "clear_conversation_context",
]

