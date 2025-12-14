import logging
import os


def get_log_level():
    """Get log level from environment variable"""
    debug = os.getenv("DEBUG", "").lower() in ("1", "true", "yes", "on")
    return logging.DEBUG if debug else logging.INFO


logging.basicConfig(format='%(created)f [%(levelname)s] %(funcName)s: %(message)s', level=get_log_level())
logger = logging.getLogger(__name__)


__all__ = ('logger', )
