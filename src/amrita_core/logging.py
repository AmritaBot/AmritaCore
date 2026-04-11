# ref: https://github.com/NoneBot/NoneBot2/blob/main/nonebot/log.py
from __future__ import annotations

import atexit
import inspect
import logging
import os
import sys
from typing import TYPE_CHECKING, Protocol

from loguru import _defaults as _lg_def
from loguru import _logger as _lg_log

from amrita_core.utils import Ref

if TYPE_CHECKING:
    from loguru import Logger, Record


logger: Logger = _lg_log.Logger(
    core=_lg_log.Core(),
    exception=None,
    depth=0,
    record=False,
    lazy=False,
    colors=False,
    raw=False,
    capture=True,
    patchers=[],
    extra={},
)  # pyright: ignore[reportAssignmentType]

debug: bool = False

if _lg_def.LOGURU_AUTOINIT and sys.stderr:
    logger.add(sys.stderr)

atexit.register(logger.remove)


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


def default_filter(record: Record):
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
logger_id: Ref[int] = Ref(
    logger.add(
        sys.stdout,
        level=0,
        diagnose=False,
        filter=default_filter,
        format=default_format,
    )
)
"""Default log handler id"""

__autodoc__ = {"logger_id": False}

__all__ = ["debug_log", "logger", "logger_id"]
