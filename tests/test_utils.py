import re
from datetime import datetime

import pytz

from amrita_core.utils import (
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
    match = re.search(
        r"\[(\d{4})-(\d{2})-(\d{2})\s+\S+\s+(\d{2}):(\d{2}):(\d{2})\]", result
    )
    assert match is not None, f"Unexpected timestamp format: {result}"
    year, month, day, hour, minute, second = map(int, match.groups())
    assert 1970 <= year <= 2100
    assert 1 <= month <= 12
    assert 1 <= day <= 31
    assert 0 <= hour <= 23
    assert 0 <= minute <= 59
    assert 0 <= second <= 59
    utc_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
    result_with_utc = get_current_datetime_timestamp(utc_time)
    match_utc = re.search(
        r"\[(\d{4})-(\d{2})-(\d{2})\s+\S+\s+(\d{2}):(\d{2}):(\d{2})\]", result_with_utc
    )
    assert match_utc is not None, (
        f"Unexpected timestamp format for UTC input: {result_with_utc}"
    )

    year_utc, month_utc, day_utc, hour_utc, minute_utc, second_utc = map(
        int, match_utc.groups()
    )
    assert (year_utc, month_utc, day_utc) == (2023, 1, 1)
    assert (hour_utc, minute_utc, second_utc) == (20, 0, 0)
