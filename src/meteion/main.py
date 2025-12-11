import websocket
import os
import rel

from meteion.bot.websocket import on_message, on_error
from meteion.utils.logger import logger
from dotenv import load_dotenv


def print_startup_info():
    logger.info("=" * 60)
    logger.info("Home Assistant QQ Bot - Starting...")
    logger.info("=" * 60)
    
    napcat_url = os.getenv('NAPCAT_API', 'ws://napcat:3001')
    logger.info(f"NapCat WebSocket URL: {napcat_url}")
    
    ha_url = os.getenv('HA_URL', 'http://homeassistant:8123')
    ha_token = os.getenv('HA_TOKEN', '')
    ha_agent_id = os.getenv('HA_AGENT_ID', 'ollama_conversation')
    
    logger.info(f"Home Assistant URL: {ha_url}")
    if ha_token:
        token_preview = f"{ha_token[:8]}...{ha_token[-4:]}" if len(ha_token) > 12 else "***"
        logger.info(f"Home Assistant Token: {token_preview} (configured)")
    else:
        logger.warning("Home Assistant Token: NOT CONFIGURED (HA_TOKEN is required)")
    logger.info(f"Home Assistant Agent ID: {ha_agent_id}")
    
    account = os.getenv('ACCOUNT', '')
    if account:
        logger.info(f"QQ Account: {account}")
    
    logger.info("=" * 60)


def main():
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    
    print_startup_info()
    
    ha_token = os.getenv('HA_TOKEN', '')
    if not ha_token:
        logger.error("HA_TOKEN is not set. Please configure it in .env file.")
        logger.error("Exiting...")
        return
    
    websocket.setdefaulttimeout(3)
    websocket_url = os.getenv('NAPCAT_API', 'ws://napcat:3001')
    logger.info(f"Connecting to NapCat WebSocket: {websocket_url}")
    
    ws = websocket.WebSocketApp(websocket_url,
                                on_message=on_message,
                                on_error=on_error)

    ws.run_forever(dispatcher=rel, reconnect=5)
    rel.signal(2, rel.abort)
    rel.dispatch()


if __name__ == '__main__':
    main()
