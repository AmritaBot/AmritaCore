from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Generator, Iterable, Sequence
from datetime import datetime
from types import ModuleType
from typing import Any, Generic, Literal, TypeVar, overload

import pytz
from amrita_sense.logging import logger
from pydantic import BaseModel

from amrita_core.types import UniResponseUsage

T = TypeVar("T")


def model_dump(obj: Iterable[BaseModel | dict]) -> Sequence[Any]:
    return [obj.model_dump() if isinstance(obj, BaseModel) else obj for obj in obj]


def remove_think_tag(text: str) -> str:
    """Remove the first occurrence of think tag

    Args:
        text (str): Parameter to process

    Returns:
        str: Processed text
    """

    start_tag = "<think>"
    end_tag = "</think>"
    start_idx = text.find(start_tag)
    if start_idx == -1:
        return text
    end_idx = text.find(end_tag, start_idx + len(start_tag))
    if end_idx == -1:
        return text

    end_of_end_tag = end_idx + len(end_tag)

    text_new = text[:start_idx] + text[end_of_end_tag:]
    while text_new.startswith("\n"):
        text_new = text_new[1:]
    return text_new


def split_list(lst: list[T], threshold: int) -> list[list[T]]:
    """Split list into multiple sublists, each sublist length does not exceed threshold"""
    if len(lst) <= threshold:
        return [lst]
    return [lst[i : i + threshold] for i in range(0, len(lst), threshold)]


def get_current_datetime_timestamp(utc_time: None | datetime = None):
    """Get current time and format as date, weekday and time string"""
    utc_time = utc_time or datetime.now(pytz.utc)
    asia_shanghai = pytz.timezone("Asia/Shanghai")
    now = utc_time.astimezone(asia_shanghai)
    formatted_date = now.strftime("%Y-%m-%d")
    formatted_weekday = now.strftime("%A")
    formatted_time = now.strftime("%H:%M:%S")
    return f"[{formatted_date} {formatted_weekday} {formatted_time}]"


def kw2dict(**kwargs: Any) -> dict[str, Any]:
    """Return the keyword arguments as a dictionary."""
    return kwargs


def n2zero(n: int | None) -> int:
    return n or 0


class Ref(Generic[T]):
    value: T

    def __init__(self, value: T) -> None:
        self.value = value


def gather_usage(
    base: UniResponseUsage[int],
    *args: UniResponseUsage[int]
    | UniResponseUsage[None]
    | UniResponseUsage[int | None]
    | None,
) -> UniResponseUsage[int]:
    """Gather usages

    Args:
        base(UniResponseUsage[int]): Base object of usage.
        *args: Usages to gather.

    Returns:
        UniResponseUsage[int]: the gathered usage (base)
    """
    u = base
    for usage in args:
        if usage is None:
            continue
        u.prompt_tokens += n2zero(usage.prompt_tokens)
        u.completion_tokens += n2zero(usage.completion_tokens)
        if usage.total_tokens is not None:
            u.total_tokens += usage.total_tokens
        else:
            u.total_tokens += n2zero(usage.prompt_tokens) + n2zero(
                usage.completion_tokens
            )
    return u


def on_none(value: Any | None) -> bool:
    """Used for Pydantic's exclude_if

    Args:
        value (Any | None): Value to check

    Returns:
        bool: Returns True when Value is None
    """
    return value is None


@overload
def side_effect_import(
    module: ModuleType, r_raise: Literal[False] = False
) -> Generator[ModuleType | BaseException]: ...


@overload
def side_effect_import(
    module: ModuleType, r_raise: Literal[True]
) -> Generator[ModuleType]: ...


def side_effect_import(
    module: ModuleType, r_raise: bool = False
) -> Generator[ModuleType | BaseException]:
    """Import module and side effect import all submodules"""
    from . import _env

    name_base = module.__package__

    if name_base is None:
        raise TypeError("Side effect import only works for package")

    if (
        _env.TEST_MODE.value and name_base not in _env._MODULE_LOADED
    ) or not _env.TEST_MODE.value:
        _env._MODULE_LOADED[name_base] = True

        for loader, module_name, is_pkg in pkgutil.iter_modules(module.__path__):
            if not r_raise:
                try:
                    yield importlib.import_module(f"{name_base}.{module_name}")
                except BaseException as e:
                    yield e
            else:
                yield importlib.import_module(f"{name_base}.{module_name}")
    else:
        return


def load_and_notice(module: ModuleType, name: str):
    logger.info(f"Loading {name}......")
    for item in side_effect_import(module, False):
        if isinstance(item, BaseException):
            logger.opt(exception=item, colors=True).warning(
                f"[{name}] Failed to import because {item}"
            )
        else:
            logger.debug(f"[{name}] Imported {item.__name__}")
