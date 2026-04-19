from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

import pytz

from amrita_core.types import UniResponseUsage

T = TypeVar("T")


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
    *args: UniResponseUsage[int]
    | UniResponseUsage[None]
    | UniResponseUsage[int | None],
) -> UniResponseUsage[int]:
    """Gather usages

    Returns:
        UniResponseUsage[int]: the gathered usage
    """
    u: UniResponseUsage[int] = UniResponseUsage(
        prompt_tokens=0, completion_tokens=0, total_tokens=0
    )
    for usage in args:
        u.prompt_tokens += n2zero(usage.prompt_tokens)
        u.completion_tokens += n2zero(usage.completion_tokens)
        u.total_tokens += usage.total_tokens or n2zero(usage.prompt_tokens) + n2zero(
            usage.completion_tokens
        )
    return u
