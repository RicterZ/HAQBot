"""
国际化支持模块
支持中文（默认）和英文
"""
import os
from typing import Dict, Any


# 翻译字典
_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "zh_CN": {
        # websocket.py
        "conversation_context_cleared": "对话上下文已清除。",
        "no_conversation_context": "没有需要清除的对话上下文。",
        "please_specify_entity_id": "请指定实体ID。用法: /{service_name} <实体ID> [<实体ID2> ...]",
        "turn_on": "打开",
        "turn_off": "关闭",
        "toggle": "切换",
        "action_failed": "{action}失败:\n{errors}",
        "success_action_count": "成功{action}了 {count} 个实体。\n错误:\n{errors}",
        "success_action": "成功{action}: {entity_list}",
        "error_executing_action": "执行{action}时出错: {error}",
        "error_processing_command": "处理命令时出错: {error}",
        "unable_to_get_context": "无法获取环境信息",
        "error_getting_context": "获取环境信息时出错: {error}",
        
        # conversation.py
        "request_processed": "请求已处理",
        "error_processing_request": "处理请求时出错: {error}",
        
        # webhook/app.py
        "invalid_webhook_token": "无效的 webhook token",
        "group_id_and_message_required": "group_id 和 message 是必需的",
        "notification_sent": "通知已发送",
        "failed_to_send_notification": "发送通知失败",
        "group_id_required": "group_id 是必需的",
        "message_or_url_required": "至少需要提供 message 或 url 之一",
        "failed_to_download_video_stream": "下载视频流失败",
        "failed_to_process_video_stream": "处理视频流失败: {error}",
        "multimodal_notification_sent": "多模态通知已发送",
        "failed_to_send_multimodal_notification": "发送多模态通知失败",
        
        # sender.py
        "websocket_not_available": "WebSocket 连接不可用",
        "message_or_file_required": "至少需要提供 message 或 file_path 之一",
        
        # main.py
        "home_assistant_qq_bot_starting": "Home Assistant QQ Bot - 启动中...",
        "napcat_websocket_url": "NapCat WebSocket URL",
        "home_assistant_url": "Home Assistant URL",
        "home_assistant_token": "Home Assistant Token",
        "configured": "已配置",
        "not_configured": "未配置 (需要设置 HA_TOKEN)",
        "home_assistant_agent_id": "Home Assistant Agent ID",
        "qq_account": "QQ 账号",
        "webhook_server_port": "Webhook 服务器端口",
        "ha_token_not_set": "HA_TOKEN 未设置。请在 .env 文件中配置它。",
        "exiting": "退出...",
        "webhook_server_started": "Webhook 服务器已启动，端口: {port}",
        "connecting_to_napcat": "正在连接到 NapCat WebSocket",
    },
    "en_US": {
        # websocket.py
        "conversation_context_cleared": "Conversation context cleared.",
        "no_conversation_context": "No conversation context to clear.",
        "please_specify_entity_id": "Please specify entity ID. Usage: /{service_name} <entity_id> [<entity_id2> ...]",
        "turn_on": "Turn on",
        "turn_off": "Turn off",
        "toggle": "Toggle",
        "action_failed": "{action} failed:\n{errors}",
        "success_action_count": "Successfully {action} {count} entity/entities.\nErrors:\n{errors}",
        "success_action": "Successfully {action}: {entity_list}",
        "error_executing_action": "Error executing {action}: {error}",
        "error_processing_command": "Error processing command: {error}",
        "unable_to_get_context": "Unable to get context information",
        "error_getting_context": "Error getting context information: {error}",
        
        # conversation.py
        "request_processed": "Request processed",
        "error_processing_request": "Error processing request: {error}",
        
        # webhook/app.py
        "invalid_webhook_token": "Invalid webhook token",
        "group_id_and_message_required": "group_id and message are required",
        "notification_sent": "Notification sent",
        "failed_to_send_notification": "Failed to send notification",
        "group_id_required": "group_id is required",
        "message_or_url_required": "At least one of message or url is required",
        "failed_to_download_video_stream": "Failed to download video stream",
        "failed_to_process_video_stream": "Failed to process video stream: {error}",
        "multimodal_notification_sent": "Multimodal notification sent",
        "failed_to_send_multimodal_notification": "Failed to send multimodal notification",
        
        # sender.py
        "websocket_not_available": "WebSocket connection not available",
        "message_or_file_required": "At least one of message or file_path must be provided",
        
        # main.py
        "home_assistant_qq_bot_starting": "Home Assistant QQ Bot - Starting...",
        "napcat_websocket_url": "NapCat WebSocket URL",
        "home_assistant_url": "Home Assistant URL",
        "home_assistant_token": "Home Assistant Token",
        "configured": "configured",
        "not_configured": "NOT CONFIGURED (HA_TOKEN is required)",
        "home_assistant_agent_id": "Home Assistant Agent ID",
        "qq_account": "QQ Account",
        "webhook_server_port": "Webhook server port",
        "ha_token_not_set": "HA_TOKEN is not set. Please configure it in .env file.",
        "exiting": "Exiting...",
        "webhook_server_started": "Webhook server started on port {port}",
        "connecting_to_napcat": "Connecting to NapCat WebSocket",
    }
}


def get_language() -> str:
    """获取当前语言设置，默认为中文"""
    lang = os.getenv("LANGUAGE", "zh_CN").strip()
    if lang not in _TRANSLATIONS:
        return "zh_CN"
    return lang


def t(key: str, **kwargs) -> str:
    """
    获取翻译文本
    
    Args:
        key: 翻译键
        **kwargs: 用于格式化字符串的参数
        
    Returns:
        翻译后的文本
    """
    lang = get_language()
    translation = _TRANSLATIONS.get(lang, _TRANSLATIONS["zh_CN"]).get(key, key)
    
    if kwargs:
        try:
            return translation.format(**kwargs)
        except KeyError:
            # 如果格式化失败，返回原始翻译
            return translation
    
    return translation


__all__ = ('t', 'get_language')

