from datetime import datetime

import pytz

from amrita_core.utils import (
    format_datetime_timestamp,
    get_current_datetime_timestamp,
    remove_think_tag,
    split_list,
)


def test_remove_think_tag():
    text_with_tags = "Hello <think>thinking</think> world"
    expected = "Hello  world"
    assert remove_think_tag(text_with_tags) == expected

    text_without_tags = "Hello world"
    assert remove_think_tag(text_without_tags) == text_without_tags


def test_format_datetime_timestamp():
    timestamp = 1672531200.0  # 2023-01-01 00:00:00 UTC
    result = format_datetime_timestamp(timestamp)
    assert "[2023-01-01" in result
    assert "Sunday" in result
    assert "00:00:00" in result or "AM" in result


def test_split_list():
    lst = [1, 2, 3, 4, 5, 6]
    assert split_list(lst, 2) == [[1, 2], [3, 4], [5, 6]]
    assert split_list(lst, 3) == [[1, 2, 3], [4, 5, 6]]
    assert split_list(lst, 4) == [[1, 2, 3, 4], [5, 6]]
    assert split_list([1, 2], 5) == [[1, 2]]
    assert split_list([], 3) == [[]]
    assert split_list([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]
    assert split_list([1], 1) == [[1]]
    assert split_list([1, 2, 3], 1) == [[1], [2], [3]]


def test_get_current_datetime_timestamp():
    result = get_current_datetime_timestamp()
    assert "[" in result  # 应该包含年份
    assert "00:00:00" not in result
    utc_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
    result_with_utc = get_current_datetime_timestamp(utc_time)
    assert "[2023-01-01 Sunday 20:00:00]" in result_with_utc
