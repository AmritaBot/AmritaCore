# pyright: reportAttributeAccessIssue=false, reportOptionalMemberAccess=false
"""Adapter-layer error normalization and the tool-result capability guard."""

from __future__ import annotations

import pytest

from amrita_core.exceptions import (
    AdapterAuthError,
    AdapterError,
    AdapterRateLimitError,
    AdapterTimeoutError,
    UnsupportedContentError,
    is_context_overflow_error,
    normalize_adapter_error,
    normalize_adapter_errors,
)
from amrita_core.types import Message, TextContent, ToolResult


class RateLimitError(Exception):
    """Stand-in for the SDK exception of the same name."""

    status_code = 429


class APITimeoutError(Exception):
    status_code = None


class _BareError(Exception):
    pass


class TestNormalizeAdapterError:
    def test_keeps_the_original_exception(self):
        original = RateLimitError("slow down")
        normalized = normalize_adapter_error(original, adapter="openai")
        assert isinstance(normalized, AdapterRateLimitError)
        assert normalized.original is original
        assert normalized.status_code == 429
        assert normalized.adapter == "openai"
        # Keep the original wording: logs and overflow detection rely on it.
        assert "slow down" in str(normalized)

    def test_maps_by_class_name_without_importing_the_sdk(self):
        assert isinstance(
            normalize_adapter_error(APITimeoutError("timeout")), AdapterTimeoutError
        )

    def test_maps_by_status_when_the_name_is_unknown(self):
        class Weird(Exception):
            status_code = 401

        assert isinstance(normalize_adapter_error(Weird("nope")), AdapterAuthError)

    def test_unknown_error_stays_generic(self):
        normalized = normalize_adapter_error(_BareError("???"))
        assert type(normalized) is AdapterError
        assert normalized.original.__class__ is _BareError

    def test_already_normalized_passes_through(self):
        first = normalize_adapter_error(_BareError("x"))
        assert normalize_adapter_error(first) is first

    def test_context_overflow_matches_through_the_wrapper(self):
        original = _BareError("This model's maximum context length is 8192 tokens")
        assert is_context_overflow_error(normalize_adapter_error(original))


class TestNormalizeDecorator:
    @pytest.mark.asyncio
    async def test_wraps_coroutines(self):
        @normalize_adapter_errors("test")
        async def boom():
            raise _BareError("down")

        with pytest.raises(AdapterError) as excinfo:
            await boom()
        assert isinstance(excinfo.value.original, _BareError)
        assert excinfo.value.adapter == "test"

    @pytest.mark.asyncio
    async def test_wraps_async_generators(self):
        @normalize_adapter_errors("test")
        async def stream():
            yield "a"
            raise _BareError("mid-stream")

        async def collect():
            return [chunk async for chunk in stream()]

        with pytest.raises(AdapterError):
            await collect()

    @pytest.mark.asyncio
    async def test_adapter_errors_are_not_rewrapped(self):
        marker = UnsupportedContentError(
            protocol="p", scope="tool_result", tool_call_ids=("1",)
        )

        @normalize_adapter_errors("test")
        async def boom():
            raise marker

        with pytest.raises(UnsupportedContentError) as excinfo:
            await boom()
        assert excinfo.value is marker


class TestUnsupportedContentError:
    def test_notice_names_the_kind_and_the_adapter(self):
        exc = UnsupportedContentError(
            protocol="openai", scope="tool_result", kinds=("image",)
        )
        assert "image" in exc.notice
        assert "openai" in exc.notice
        assert exc.notice.startswith("ERR:")


class TestAgentLoopRepair:
    """The agent loop folds untransportable blocks into a text note and lets the model decide."""

    def _messages(self) -> list:
        return [
            Message(role="user", content="hi"),
            ToolResult(
                role="tool",
                name="shot",
                tool_call_id="call_1",
                content=[TextContent(text="see"), TextContent(text="x")],
            ),
            ToolResult(
                role="tool",
                name="shot",
                tool_call_id="call_2",
                content="plain",
            ),
        ]

    def test_repairs_only_the_flagged_results(self):
        from amrita_core.builtins.agent.react_base import (
            _relax_unsupported_tool_results,
        )

        messages = self._messages()
        exc = UnsupportedContentError(
            protocol="openai",
            scope="tool_result",
            kinds=("image",),
            tool_call_ids=("call_1",),
        )
        repaired = _relax_unsupported_tool_results(messages, exc)
        assert repaired is not None
        assert repaired[1] is not messages[1]
        assert repaired[2] is messages[2]
        blocks = repaired[1].content
        assert all(isinstance(block, TextContent) for block in blocks)
        assert blocks[-1].text == exc.notice
        # The original objects stay untouched.
        assert messages[1].content[0].text == "see"

    def test_returns_none_when_nothing_matches(self):
        from amrita_core.builtins.agent.react_base import (
            _relax_unsupported_tool_results,
        )

        exc = UnsupportedContentError(
            protocol="openai", scope="tool_result", tool_call_ids=("missing",)
        )
        assert _relax_unsupported_tool_results(self._messages(), exc) is None
