import websocket
import os
import rel

from meteion.message import on_message, on_error
from meteion.utils.logger import logger


def main():
    websocket.setdefaulttimeout(3)
    websocket_url = os.getenv('QQ_API', 'ws://napcat:3001')
    logger.info(f"Connecting to websocket {websocket_url}")
    ws = websocket.WebSocketApp(os.getenv('QQ_API', 'ws://napcat:3001'),
                                on_message=on_message,
                                on_error=on_error)

    ws.run_forever(dispatcher=rel, reconnect=5)
    rel.signal(2, rel.abort)
    rel.dispatch()


if __name__ == '__main__':
    main()
