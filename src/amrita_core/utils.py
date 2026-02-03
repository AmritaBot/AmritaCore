from __future__ import annotations

from datetime import datetime
from typing import Any

import pytz


def remove_think_tag(text: str) -> str:
    """Remove the first occurrence of think tag

    Args:
        text (str): Parameter to process

    Returns:
        str: Processed text
    """

    start_tag = "<think>"
    end_tag = "</think>"

    # Find the position of the first start tag
    start_idx = text.find(start_tag)
    if start_idx == -1:
        return text  # No start tag found, return original text

    # Find the position of the end tag after the start tag
    end_idx = text.find(end_tag, start_idx + len(start_tag))
    if end_idx == -1:
        return text  # No corresponding end tag found, return original text

    # Calculate the end position of the end tag
    end_of_end_tag = end_idx + len(end_tag)

    # Concatenate text after removing the tag
    text_new = text[:start_idx] + text[end_of_end_tag:]
    while text_new.startswith("\n"):
        text_new = text_new[1:]
    return text_new


def format_datetime_timestamp(time: float) -> str:
    """Format timestamp to date, weekday and time string"""
    now = datetime.fromtimestamp(time)
    formatted_date = now.strftime("%Y-%m-%d")
    formatted_weekday = now.strftime("%A")
    formatted_time = now.strftime("%I:%M:%S %p")
    return f"[{formatted_date} {formatted_weekday} {formatted_time}]"


def split_list(lst: list, threshold: int) -> list[Any]:
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
