import logging
import sys
import re
from config import BOT_TOKEN, TRANZUPI_API_KEY, TRANZUPI_SECRET

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that scrubs sensitive credentials like BOT_TOKEN,
    API keys, and secret keys from all log messages.
    """
    def __init__(self, name=""):
        super().__init__(name)
        self.secrets = [s for s in [BOT_TOKEN, TRANZUPI_API_KEY, TRANZUPI_SECRET] if s and len(s) > 4]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for secret in self.secrets:
                record.msg = record.msg.replace(secret, "[REDACTED]")
        if record.args:
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for secret in self.secrets:
                        arg = arg.replace(secret, "[REDACTED]")
                new_args.append(arg)
            record.args = tuple(new_args)
        return True

def setup_logger(name: str = "KiroShopBot") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveDataFilter())
        logger.addHandler(handler)

    return logger

logger = setup_logger()
