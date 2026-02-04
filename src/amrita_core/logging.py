# ref: https://github.com/NoneBot/NoneBot2/blob/main/nonebot/log.py
import inspect
import logging
import os
import sys
from typing import TYPE_CHECKING, Protocol

import loguru

if TYPE_CHECKING:
    from loguru import Logger, Record

logger: "Logger" = loguru.logger

debug: bool = False


class ToStringAble(Protocol):
    def __str__(self) -> str: ...


def debug_log(message: ToStringAble) -> None:
    global debug
    if debug:
        logger.debug(message)


class LoguruHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info, colors=True).log(
            level, record.getMessage()
        )


def default_filter(record: "Record"):
    """Default filter for logging, change level from Environment"""
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    levelno = logger.level(log_level).no if isinstance(log_level, str) else log_level
    return record["level"].no >= levelno


default_format: str = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <7}</level> | "
    "<magenta>{name}:{function}:{line}</magenta> | "
    "<level>{message}</level>"
)
"""Default log format"""

logger.remove()
logger_id = logger.add(
    sys.stdout,
    level=0,
    diagnose=False,
    filter=default_filter,
    format=default_format,
)
"""Default log handler id"""


__autodoc__ = {"logger_id": False}
