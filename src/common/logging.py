from __future__ import annotations

import logging
import logging.config
import time

from .config import load_config

LOG_FORMAT = "%(asctime)sZ %(levelname)s %(name)s %(message)s"
LOG_DATEFMT = "%Y-%m-%dT%H:%M:%S"


def _utc_formatter() -> logging.Formatter:
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATEFMT)
    formatter.converter = time.gmtime
    return formatter


def configure_logging() -> None:
    config = load_config()
    level_name = config.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(_utc_formatter())

    logging.basicConfig(level=level, handlers=[handler])


__all__ = ["configure_logging", "LOG_FORMAT", "LOG_DATEFMT"]
