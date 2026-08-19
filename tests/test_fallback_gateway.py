"""Tests for the gateway-level preset fallback in ``amrita_core.libchat``.

The fallback loop lives in the gateway functions (``call_completion`` /
``tools_caller`` / ``call_embedding``) rather than in the ``LLM_COMPLETION``
workflow node.  On failure each gateway call fires a concrete
``FallbackContext`` subclass (``CompletionFallbackContext`` /
``ToolsFallbackContext`` / ``EmbeddingFallbackContext``); a matcher may swap
``event.preset`` to retry with an alternative preset.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from amrita_sense.hook.matcher import Matcher

from amrita_core.config import AmritaConfig
from amrita_core.hook.event import (
    CompletionFallbackContext,
    EmbeddingFallbackContext,
    FallbackContext,
    ToolsFallbackContext,
)
from amrita_core.hook.exception import FallbackFailed
from amrita_core.libchat import call_completion, call_embedding, tools_caller
from amrita_core.tools.models import ToolFunctionSchema
from amrita_core.types import Message, ModelPreset, UniResponse


def _make_preset(name: str) -> ModelPreset:
    return ModelPreset(
        model=f"model-{name}",
        name=name,
        api_key="test-key",
        protocol="test-protocol",
    )


def _make_tools() -> list[ToolFunctionSchema]:
    return [
        ToolFunctionSchema.model_validate(
            {
                "function": {
                    "name": "get_weather",
                    "description": "Get weather info",
                    "parameters": {"type": "object", "properties": {}},
                }
            }
        )
    ]


@pytest.fixture
def config() -> AmritaConfig:
    return AmritaConfig()


@pytest.fixture
def preset_a() -> ModelPreset:
    return _make_preset("preset-a")


@pytest.fixture
def preset_b() -> ModelPreset:
    return _make_preset("preset-b")


def _expire(matcher: Matcher) -> None:
    matcher._dead_at = datetime.now() - timedelta(minutes=1)


class TestCompletionFallback:
    """Fallback inside the ``call_completion`` gateway (async generator)."""

    @pytest.mark.asyncio
    async def test_switches_preset_and_retries(self, config, preset_a, preset_b):
        """First attempt fails; matcher swaps preset; second attempt succeeds."""
        matcher = Matcher("PRESET_FALLBACK", priority=1)

        async def switch_preset(ev: FallbackContext):
            assert isinstance(ev, CompletionFallbackContext)
            ev.preset = preset_b

        matcher.handle()(switch_preset)
        try:
            async def ok_stream():
                yield "Hello"
                yield UniResponse(content="Hello", tool_calls=[], usage=None)

            side_effect = [RuntimeError("boom"), lambda: ok_stream()]

            with patch(
                "amrita_core.libchat._call_with_reflection",
                side_effect=side_effect,
            ) as mock_call:
                chunks = []
                async for chunk in call_completion(
                    [Message(role="user", content="Hi")], preset_a, config
                ):
                    chunks.append(chunk)

            assert chunks[0] == "Hello"
            assert isinstance(chunks[-1], UniResponse)
            assert mock_call.call_count == 2
            # The second attempt used the replacement preset.
            assert mock_call.call_args_list[1].args[0] is preset_b
        finally:
            _expire(matcher)

    @pytest.mark.asyncio
    async def test_no_matcher_raises_fallback_failed(self, config, preset_a):
        """Without a matcher swapping the preset, FallbackFailed is raised."""
        with patch(
            "amrita_core.libchat._call_with_reflection",
            side_effect=RuntimeError("boom"),
        ):
            with pytest.raises(FallbackFailed, match="No preset fallback"):
                async for _ in call_completion(
                    [Message(role="user", content="Hi")], preset_a, config
                ):
                    pass

    @pytest.mark.asyncio
    async def test_exhausted_attempts_raise_fallback_failed(self, config, preset_a, preset_b):
        """Swapping presets but never succeeding exhausts max_fallbacks."""
        matcher = Matcher("PRESET_FALLBACK", priority=1)

        async def keep_swapping(ev: FallbackContext):
            # Always provide a *new* preset object so the loop keeps retrying
            # until max_fallbacks is exhausted.
            ev.preset = _make_preset(f"alt-{ev.term}")

        matcher.handle()(keep_swapping)
        try:
            with patch(
                "amrita_core.libchat._call_with_reflection",
                side_effect=RuntimeError("boom"),
            ) as mock_call:
                with pytest.raises(FallbackFailed, match="Max preset fallbacks"):
                    async for _ in call_completion(
                        [Message(role="user", content="Hi")], preset_a, config
                    ):
                        pass
                # initial + max_fallbacks retries all failed
                assert mock_call.call_count == config.llm.max_fallbacks
        finally:
            _expire(matcher)


class TestToolsFallback:
    """Fallback inside the ``tools_caller`` gateway."""

    @pytest.mark.asyncio
    async def test_switches_preset_and_retries(self, config, preset_a, preset_b):
        matcher = Matcher("PRESET_FALLBACK", priority=1)

        async def switch_preset(ev: FallbackContext):
            assert isinstance(ev, ToolsFallbackContext)
            assert ev.tools is not None
            assert ev.tools[0].function.name == "get_weather"
            ev.preset = preset_b

        matcher.handle()(switch_preset)
        try:
            ok_resp = UniResponse(content=None, tool_calls=[], usage=None)

            with patch(
                "amrita_core.libchat._call_with_reflection",
                side_effect=[RuntimeError("boom"), ok_resp],
            ) as mock_call:
                result = await tools_caller(
                    [Message(role="user", content="Weather?")],
                    _make_tools(),
                    preset_a,
                    config=config,
                )

            assert result is ok_resp
            assert mock_call.call_count == 2
            assert mock_call.call_args_list[1].args[0] is preset_b
        finally:
            _expire(matcher)

    @pytest.mark.asyncio
    async def test_no_matcher_raises_fallback_failed(self, config, preset_a):
        with patch(
            "amrita_core.libchat._call_with_reflection",
            side_effect=RuntimeError("boom"),
        ):
            with pytest.raises(FallbackFailed, match="No preset fallback"):
                await tools_caller(
                    [Message(role="user", content="Weather?")],
                    _make_tools(),
                    preset_a,
                    config=config,
                )


class TestEmbeddingFallback:
    """Fallback inside the ``call_embedding`` gateway."""

    @pytest.mark.asyncio
    async def test_switches_preset_and_retries(self, config, preset_a, preset_b):
        matcher = Matcher("PRESET_FALLBACK", priority=1)

        async def switch_preset(ev: FallbackContext):
            assert isinstance(ev, EmbeddingFallbackContext)
            ev.preset = preset_b

        matcher.handle()(switch_preset)
        try:
            ok_result = [0.1, 0.2, 0.3]

            with patch(
                "amrita_core.libchat._call_with_reflection",
                side_effect=[RuntimeError("boom"), ok_result],
            ) as mock_call:
                result = await call_embedding(
                    ["hello world"], preset_a, config
                )

            assert result == ok_result
            assert mock_call.call_count == 2
            assert mock_call.call_args_list[1].args[0] is preset_b
        finally:
            _expire(matcher)

    @pytest.mark.asyncio
    async def test_no_matcher_raises_fallback_failed(self, config, preset_a):
        with patch(
            "amrita_core.libchat._call_with_reflection",
            side_effect=RuntimeError("boom"),
        ):
            with pytest.raises(FallbackFailed, match="No preset fallback"):
                await call_embedding(["hello world"], preset_a, config)

    @pytest.mark.asyncio
    async def test_single_string_rejected(self, config, preset_a):
        with pytest.raises(TypeError, match="sequence of strings"):
            await call_embedding("hello", preset_a, config)  # type: ignore[arg-type]


class TestFallbackEventTypes:
    """The concrete events share PRESET_FALLBACK but stay distinguishable."""

    @pytest.mark.asyncio
    async def test_event_hierarchy(self, config, preset_a):
        from amrita_core.hook.event import EventTypeEnum

        ctx_completion = CompletionFallbackContext(
            preset_a, RuntimeError("x"), config, [], 1
        )
        ctx_tools = ToolsFallbackContext(
            preset_a, RuntimeError("x"), config, [], 1, tools=_make_tools()
        )
        ctx_embedding = EmbeddingFallbackContext(
            preset_a, RuntimeError("x"), config, ["text"], 1
        )

        for ctx in (ctx_completion, ctx_tools, ctx_embedding):
            assert isinstance(ctx, FallbackContext)
            assert ctx.get_event_type() is EventTypeEnum.PRESET_FALLBACK

        assert not isinstance(ctx_completion, ToolsFallbackContext)
        assert not isinstance(ctx_tools, EmbeddingFallbackContext)
        assert ctx_tools.tools is not None
        assert ctx_embedding.context == ["text"]

    def test_fail_raises_fallback_failed(self, config, preset_a):
        ctx = CompletionFallbackContext(
            preset_a, RuntimeError("x"), config, [], 1
        )
        with pytest.raises(FallbackFailed):
            ctx.fail("no fallback")


class TestFallbackFailedException:
    """FallbackFailed is a RuntimeError subclass for broad exception handling."""

    def test_is_runtime_error(self):
        assert issubclass(FallbackFailed, RuntimeError)
