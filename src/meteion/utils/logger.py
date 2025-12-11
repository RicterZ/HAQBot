import logging


logging.basicConfig(format='%(created)f [%(levelname)s] %(funcName)s: %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


__all__ = ('logger', )
