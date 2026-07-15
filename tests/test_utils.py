import re
from datetime import datetime

import pytz

from amrita_core.types import UniResponseUsage
from amrita_core.utils import (
    gather_usage,
    get_current_datetime_timestamp,
    n2zero,
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


# n2zero


class TestN2zero:
    def test_with_positive_int(self):
        assert n2zero(42) == 42

    def test_with_zero(self):
        assert n2zero(0) == 0

    def test_with_none(self):
        assert n2zero(None) == 0


# gather_usage


class TestGatherUsage:
    """Unit tests for the gather_usage utility — the core token-accumulation
    function used by MemoryLimiter, agent strategies, and workflow nodes."""

    @staticmethod
    def _make_usage(
        prompt: int = 0, completion: int = 0, total: int | None = None
    ) -> UniResponseUsage[int]:
        return UniResponseUsage(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total if total is not None else prompt + completion,
        )

    def test_basic_accumulation(self):
        base = self._make_usage(10, 5, 15)
        extra = self._make_usage(20, 10, 30)
        result = gather_usage(base, extra)
        assert result is base
        assert base.prompt_tokens == 30
        assert base.completion_tokens == 15
        assert base.total_tokens == 45

    def test_none_usage_is_skipped(self):
        base = self._make_usage(10, 5, 15)
        result = gather_usage(base, None)
        assert result is base
        assert base.prompt_tokens == 10
        assert base.completion_tokens == 5
        assert base.total_tokens == 15

    def test_usage_with_none_prompt(self):
        base = self._make_usage(10, 5, 15)
        extra: UniResponseUsage[int | None] = UniResponseUsage(
            prompt_tokens=None,
            completion_tokens=3,
            total_tokens=3,  # type: ignore[arg-type]
        )
        gather_usage(base, extra)
        assert base.prompt_tokens == 10  # n2zero(None) == 0
        assert base.completion_tokens == 8
        assert base.total_tokens == 18

    def test_total_tokens_none_falls_back_to_sum(self):
        base = self._make_usage(0, 0, 0)
        extra: UniResponseUsage[int | None] = UniResponseUsage(
            prompt_tokens=7,
            completion_tokens=3,
            total_tokens=None,  # type: ignore[arg-type]
        )
        gather_usage(base, extra)
        assert base.total_tokens == 10  # 7 + 3

    def test_multiple_args(self):
        base = self._make_usage(0, 0, 0)
        u1 = self._make_usage(1, 2, 3)
        u2 = self._make_usage(4, 5, 9)
        u3 = self._make_usage(10, 20, 30)
        gather_usage(base, u1, u2, u3)
        assert base.prompt_tokens == 15
        assert base.completion_tokens == 27
        assert base.total_tokens == 42

    def test_all_none_args(self):
        base = self._make_usage(5, 5, 10)
        result = gather_usage(base, None, None, None)
        assert result is base
        assert base.prompt_tokens == 5
        assert base.completion_tokens == 5
        assert base.total_tokens == 10

    def test_returns_same_object(self):
        base = self._make_usage(1, 1, 2)
        extra = self._make_usage(3, 4, 7)
        result = gather_usage(base, extra)
        assert result is base
