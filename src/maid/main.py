import websocket
import os
import rel
import threading

from maid.bot.websocket import on_message, on_error, on_open
from maid.utils.logger import logger
from maid.utils.i18n import t
from maid.webhook.app import app
import uvicorn
from dotenv import load_dotenv


def print_startup_info():
    logger.info("=" * 60)
    logger.info(t("home_assistant_qq_bot_starting"))
    logger.info("=" * 60)
    
    napcat_url = os.getenv('NAPCAT_API', 'ws://napcat:3001')
    logger.info(f"{t('napcat_websocket_url')}: {napcat_url}")
    
    ha_url = os.getenv('HA_URL', 'http://homeassistant:8123')
    ha_token = os.getenv('HA_TOKEN', '')
    ha_agent_id = os.getenv('HA_AGENT_ID', 'ollama_conversation')
    
    logger.info(f"{t('home_assistant_url')}: {ha_url}")
    if ha_token:
        token_preview = f"{ha_token[:8]}...{ha_token[-4:]}" if len(ha_token) > 12 else "***"
        logger.info(f"{t('home_assistant_token')}: {token_preview} ({t('configured')})")
    else:
        logger.warning(f"{t('home_assistant_token')}: {t('not_configured')}")
    logger.info(f"{t('home_assistant_agent_id')}: {ha_agent_id}")
    
    account = os.getenv('ACCOUNT', '')
    if account:
        logger.info(f"{t('qq_account')}: {account}")
    
    webhook_port = int(os.getenv('WEBHOOK_PORT', '8080'))
    logger.info(f"{t('webhook_server_port')}: {webhook_port}")
    
    logger.info("=" * 60)


def main():
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    
    print_startup_info()
    
    ha_token = os.getenv('HA_TOKEN', '')
    if not ha_token:
        logger.error(t("ha_token_not_set"))
        logger.error(t("exiting"))
        return
    
    webhook_port = int(os.getenv('WEBHOOK_PORT', '8080'))
    
    def run_webhook():
        uvicorn.run(app, host="0.0.0.0", port=webhook_port, log_level="info")
    
    webhook_thread = threading.Thread(target=run_webhook, daemon=True)
    webhook_thread.start()
    logger.info(t("webhook_server_started", port=webhook_port))
    
    websocket.setdefaulttimeout(3)
    websocket_url = os.getenv('NAPCAT_API', 'ws://napcat:3001')
    logger.info(f"{t('connecting_to_napcat')}: {websocket_url}")
    
    ws = websocket.WebSocketApp(websocket_url,
                                on_message=on_message,
                                on_error=on_error,
                                on_open=on_open)

    ws.run_forever(dispatcher=rel, reconnect=5)
    rel.signal(2, rel.abort)
    rel.dispatch()


if __name__ == '__main__':
    main()
