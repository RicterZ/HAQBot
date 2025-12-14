import os
from typing import Dict, Any


# 翻译字典
_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "zh_CN": {
        # websocket.py
        "conversation_context_cleared": "对话上下文已清除",
        "no_conversation_context": "没有需要清除的对话上下文",
        "please_specify_entity_id": "请指定实体ID。用法: /{service_name} <实体ID> [<实体ID2> ...]",
        "turn_on": "打开",
        "turn_off": "关闭",
        "toggle": "切换",
        "action_failed": "{action}失败:\n{errors}",
        "success_action_count": "成功{action}了{count} 个实体。\n错误:\n{errors}",
        "success_action": "成功{action}: {entity_list}",
        "error_executing_action": "执行{action}时出错: {error}",
        "error_processing_command": "处理命令时出错: {error}",
        "entity_not_found": "实体未找到",
        "multiple_entities_found": "⚠️ 发现 {count} 个同名实体（别名: {alias}），将控制第一个: {first}",
        "unable_to_get_context": "无法获取环境信息",
        "error_getting_context": "获取环境信息时出错: {error}",
        "no_devices_found": "未找到 {domain} 类型的设备",
        "devices_list_header": "{domain} 设备（按区域分组）",
        "area": "区域",
        "ungrouped": "未分组",
        "state_on": "开启",
        "state_off": "关闭",
        "state_unknown": "未知",
        "context_info_header": "🏠 家居状态",
        "lights_on": "💡 开启的灯光",
        "climate_devices": "❄️ 空调设备",
        "temperature": "🌡️ 环境温度",
        "humidity": "💧 湿度",
        "air_quality": "🌬️ 空气质量",
        "energy_consumption": "⚡ 日耗电量",
        "weather": "☀️ 天气",
        "important_status": "⚠️ 重要状态",
        "current_temp": "当前",
        "target_temp": "目标",
        "mode": "模式",
        "fan": "风扇",
        "no_status_info": "暂无状态信息",
        "ungrouped_area": "未分组",
        "help_header": "{nickname} 支持的命令列表",
        "help_command_description": "显示所有支持的命令和简要描述",
        "echo_command_description": "回显输入的文本（用于测试）",
        "clear_command_description": "清除对话上下文",
        "turnon_command_description": "打开指定的设备（支持实体ID、友好名称或别名，可同时控制多个）",
        "turnoff_command_description": "关闭指定的设备（支持实体ID、友好名称或别名，可同时控制多个）",
        "toggle_command_description": "切换指定设备的状态（支持实体ID、友好名称或别名，可同时控制多个）",
        "info_command_description": "获取 Home Assistant 环境信息（实体统计）",
        "light_command_description": "列出所有灯光设备（按区域分组）",
        "switch_command_description": "列出所有开关设备（按区域分组）",
        "script_command_description": "执行 Home Assistant 脚本（支持脚本ID或实体ID）",
        "script_usage": "用法: /script <脚本ID>",
        "script_executed": "✅ 脚本执行成功: {script_id}",
        "script_execution_failed": "❌ 脚本执行失败: {script_id}\n错误: {error}",
        "climate_command_description": "控制空调设备（设置模式：制冷/制热/通风/关闭，设置温度）",
        "climate_usage": "用法: /climate <实体ID> [模式] [温度]\n示例: /climate 客厅空调 制冷 26\n      /climate 客厅空调 temp 25\n      /climate 客厅空调 关闭",
        "climate_mode_set": "✅ 模式已设置为: {mode}",
        "climate_temp_set": "✅ 温度已设置为: {temp}°C",
        "climate_no_params": "请指定模式或温度。用法: /climate <实体ID> [模式] [温度]",
        "mode_cool": "制冷",
        "mode_heat": "制热",
        "mode_fan_only": "通风",
        "mode_off": "关闭",
        "search_command_description": "模糊搜索实体（支持实体ID、友好名称或别名）",
        "search_usage": "用法: /search <查询关键词>",
        "search_results_header": "🔍 搜索结果（关键词: {query}，找到 {count} 个）:",
        "search_no_results": "未找到匹配 '{query}' 的实体",
        "search_results_truncated": "（结果已截断，仅显示前20个）",
        "permission_denied": "您没有权限执行此操作",
        
        # conversation.py
        "request_processed": "请求已处理",
        "error_processing_request": "处理请求时出错: {error}",
        
        # webhook/app.py
        "invalid_webhook_token": "无效 webhook token",
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
        "not_configured": "未配置(需要设置 HA_TOKEN)",
        "home_assistant_agent_id": "Home Assistant Agent ID",
        "qq_account": "QQ 账号",
        "webhook_server_port": "Webhook 服务器端口",
        "ha_token_not_set": "HA_TOKEN 未设置。请在 .env 文件中配置它",
        "exiting": "退出中...",
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
        "entity_not_found": "Entity not found",
        "multiple_entities_found": "⚠️ Found {count} entities with same alias ({alias}), will control the first one: {first}",
        "unable_to_get_context": "Unable to get context information",
        "error_getting_context": "Error getting context information: {error}",
        "no_devices_found": "No {domain} devices found",
        "devices_list_header": "{domain} devices (grouped by area):",
        "area": "Area",
        "ungrouped": "Ungrouped",
        "state_on": "On",
        "state_off": "Off",
        "state_unknown": "Unknown",
        "context_info_header": "🏠 Home Status",
        "lights_on": "💡 Lights On",
        "climate_devices": "❄️ Climate Control",
        "temperature": "🌡️ Ambient Temperature",
        "humidity": "💧 Humidity",
        "air_quality": "🌬️ Air Quality",
        "energy_consumption": "⚡ Daily Energy Consumption",
        "weather": "☀️ Weather",
        "important_status": "⚠️ Important Status",
        "current_temp": "Current",
        "target_temp": "Target",
        "mode": "Mode",
        "fan": "Fan",
        "no_status_info": "No status information available",
        "ungrouped_area": "Ungrouped",
        "help_header": "📋 Supported Commands:",
        "help_command_description": "Show all supported commands and brief descriptions",
        "echo_command_description": "Echo the input text (for testing)",
        "clear_command_description": "Clear conversation context",
        "turnon_command_description": "Turn on specified device(s) (supports entity_id, friendly_name, or alias, can control multiple)",
        "turnoff_command_description": "Turn off specified device(s) (supports entity_id, friendly_name, or alias, can control multiple)",
        "toggle_command_description": "Toggle specified device(s) state (supports entity_id, friendly_name, or alias, can control multiple)",
        "info_command_description": "Get Home Assistant context information (entity statistics)",
        "light_command_description": "List all light devices (grouped by area)",
        "switch_command_description": "List all switch devices (grouped by area)",
        "script_command_description": "Execute Home Assistant script (supports script ID or entity ID)",
        "script_usage": "Usage: /script <script_id>",
        "script_executed": "✅ Script executed successfully: {script_id}",
        "script_execution_failed": "❌ Script execution failed: {script_id}\nError: {error}",
        "climate_command_description": "Control climate device (set mode: cool/heat/fan_only/off, set temperature)",
        "climate_usage": "Usage: /climate <entity_id> [mode] [temperature]\nExample: /climate living_room_ac cool 26\n         /climate living_room_ac temp 25\n         /climate living_room_ac off",
        "climate_mode_set": "✅ Mode set to: {mode}",
        "climate_temp_set": "✅ Temperature set to: {temp}°C",
        "climate_no_params": "Please specify mode or temperature. Usage: /climate <entity_id> [mode] [temperature]",
        "mode_cool": "Cool",
        "mode_heat": "Heat",
        "mode_fan_only": "Fan Only",
        "mode_off": "Off",
        "search_command_description": "Fuzzy search entities (supports entity_id, friendly_name, or alias)",
        "search_usage": "Usage: /search <query>",
        "search_results_header": "🔍 Search Results (query: {query}, found {count}):",
        "search_no_results": "No entities found matching '{query}'",
        "search_results_truncated": "(Results truncated, showing first 20)",
        "permission_denied": "You do not have permission to perform this operation",
        
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
        key: 翻译键        **kwargs: 用于格式化字符串的参数        
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

