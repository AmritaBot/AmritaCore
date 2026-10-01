"""History compaction: the ContextCompactor policy object, its nodes, and
message normalization."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.backends import LegacyBackend
from amrita_core.components.compaction import (
    COMPACT,
    ContextCompactor,
    should_compact,
    split_history,
)
from amrita_core.components.llm import LLM_COMPLETION
from amrita_core.components.normalize import NORMALIZE_MESSAGES, flatten_content
from amrita_core.config import AmritaConfig
from amrita_core.contexts import (
    AbilityState,
    MemoryContext,
    RespState,
    WorkingState,
)
from amrita_core.exceptions import ContextOverflowError, is_context_overflow_error
from amrita_core.types import (
    CONTENT_LIST_TYPE,
    MemoryModel,
    Message,
    ModelPreset,
    SendMessageWrap,
    TextContent,
    ToolCall,
    ToolResult,
    UniResponse,
    UniResponseUsage,
)


def _preset(max_context: int | None = None, max_output: int | None = None):
    return ModelPreset(
        model="test-model",
        name="test-preset",
        api_key="fake-key",
        max_context=max_context,
        max_output=max_output,
    )


def _ability(
    config: AmritaConfig | None = None, preset: ModelPreset | None = None
) -> AbilityState:
    backend = LegacyBackend()
    return AbilityState(
        config=config or AmritaConfig(),
        slot=BackendSlots(backend, backend, backend),
        preset=preset,
    )


def _usage(prompt_tokens: int) -> UniResponseUsage[int]:
    return UniResponseUsage(
        prompt_tokens=prompt_tokens, completion_tokens=0, total_tokens=prompt_tokens
    )


class TestSplitHistory:
    def test_cuts_at_the_newest_user_message(self):
        messages: CONTENT_LIST_TYPE = [
            Message(role="user", content="u1"),
            Message(role="assistant", content="a1"),
            Message(role="user", content="u2"),
            Message(role="assistant", content="a2"),
        ]
        prefix, tail = split_history(messages)
        assert [m.content for m in prefix] == ["u1", "a1"]
        assert [m.content for m in tail] == ["u2", "a2"]

    def test_keeps_tool_pairs_together(self):
        messages: CONTENT_LIST_TYPE = [
            Message(role="user", content="u1"),
            Message(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(id="t1", function={"name": "f", "arguments": "{}"})
                ],  # pyright: ignore[reportArgumentType]
            ),
            ToolResult(role="tool", name="f", content="r1", tool_call_id="t1"),
            Message(role="user", content="u2"),
        ]
        prefix, tail = split_history(messages)
        assert len(prefix) == 3
        assert [m.role for m in tail] == ["user"]

    def test_nothing_to_fold_without_an_older_turn(self):
        messages: CONTENT_LIST_TYPE = [Message(role="user", content="u1")]
        prefix, tail = split_history(messages)
        assert prefix == []
        assert len(tail) == 1

    def test_nothing_to_fold_without_any_user_message(self):
        messages: CONTENT_LIST_TYPE = [Message(role="assistant", content="a1")]
        prefix, _ = split_history(messages)
        assert prefix == []


class TestThreshold:
    def test_follows_the_preset_window(self):
        config = AmritaConfig()
        config.llm.compaction_trigger_ratio = 0.5
        compactor = ContextCompactor(config=config, preset=_preset(max_context=1000))
        assert compactor.budget == 1000
        assert compactor.threshold == 500

    def test_falls_back_to_the_global_window(self):
        config = AmritaConfig()
        config.llm.session_tokens_windows = 4000
        config.llm.compaction_trigger_ratio = 0.25
        compactor = ContextCompactor(config=config)
        assert compactor.budget == 4000
        assert compactor.threshold == 1000

    def test_preset_without_a_window_uses_the_global_window(self):
        config = AmritaConfig()
        config.llm.session_tokens_windows = 800
        config.llm.compaction_trigger_ratio = 1.0
        compactor = ContextCompactor(config=config, preset=_preset())
        assert compactor.threshold == 800

    def test_enabled_tracks_the_config_switch(self):
        config = AmritaConfig()
        assert ContextCompactor(config=config).enabled is True
        config.llm.enable_compaction = False
        assert ContextCompactor(config=config).enabled is False

    def test_should_compact_needs_a_measurement(self):
        config = AmritaConfig()
        config.llm.compaction_trigger_ratio = 1.0
        config.llm.memory_length_limit = 0
        compactor = ContextCompactor(config=config, preset=_preset(max_context=100))
        assert compactor.should_compact(None) is False
        assert compactor.should_compact(MemoryModel()) is False

    def test_message_limit_reads_the_config(self):
        config = AmritaConfig()
        config.llm.memory_length_limit = 42
        assert ContextCompactor(config=config).message_limit == 42


class TestMessageLimitFallback:
    """The token trigger needs the provider to report usage; the message-count
    fallback covers gateways that report none."""

    @staticmethod
    def _history(count: int) -> MemoryModel:
        messages: CONTENT_LIST_TYPE = []
        for index in range(count):
            role = "user" if index % 2 == 0 else "assistant"
            messages.append(Message(role=role, content=f"m{index}"))
        return MemoryModel(messages=messages)

    def test_fires_without_any_usage_report(self):
        config = AmritaConfig()
        config.llm.memory_length_limit = 4
        compactor = ContextCompactor(config=config, preset=_preset(max_context=10**6))
        memory = self._history(4)
        assert memory.usage is None
        assert compactor.should_compact(memory) is True

    def test_stays_below_the_limit(self):
        config = AmritaConfig()
        config.llm.memory_length_limit = 5
        compactor = ContextCompactor(config=config, preset=_preset(max_context=10**6))
        assert compactor.should_compact(self._history(4)) is False

    def test_zero_disables_the_fallback(self):
        config = AmritaConfig()
        config.llm.memory_length_limit = 0
        compactor = ContextCompactor(config=config, preset=_preset(max_context=10**6))
        assert compactor.should_compact(self._history(50)) is False

    def test_disabled_compaction_wins_over_the_fallback(self):
        config = AmritaConfig()
        config.llm.enable_compaction = False
        config.llm.memory_length_limit = 2
        compactor = ContextCompactor(config=config, preset=_preset(max_context=10**6))
        assert compactor.should_compact(self._history(10)) is False

    def test_still_needs_a_foldable_prefix(self):
        config = AmritaConfig()
        config.llm.memory_length_limit = 1
        compactor = ContextCompactor(config=config, preset=_preset(max_context=10**6))
        memory = MemoryModel(messages=[Message(role="user", content="only turn")])
        assert compactor.should_compact(memory) is False

    def test_node_sees_the_fallback(self):
        config = AmritaConfig()
        config.llm.memory_length_limit = 4
        ability = _ability(config, _preset(max_context=10**6))
        memory = self._history(4)
        assert should_compact.func(ability=ability, mem=MemoryContext(memory)) is True

    @pytest.mark.asyncio
    async def test_fallback_compacts_and_clears_usage(self):
        config = AmritaConfig()
        config.llm.memory_length_limit = 4
        ability = _ability(config, _preset(max_context=10**6))
        memory = self._history(4)
        mem = MemoryContext(memory)
        with patch.object(
            ContextCompactor,
            "summarize",
            new=AsyncMock(return_value="folded"),
        ):
            await COMPACT.func(  # pyright: ignore[reportGeneralTypeIssues]
                ability=ability, mem=mem, resp=RespState()
            )
        assert memory.abstract == "folded"
        assert len(memory.messages) == 2


class TestShouldCompact:
    def test_true_once_the_prompt_fills_the_threshold(self):
        config = AmritaConfig()
        config.llm.compaction_trigger_ratio = 1.0
        ability = _ability(config, _preset(max_context=100))
        memory = MemoryModel(
            messages=[
                Message(role="user", content="u1"),
                Message(role="assistant", content="a1"),
                Message(role="user", content="u2"),
            ],
            usage=_usage(100),
        )
        assert should_compact.func(ability=ability, mem=MemoryContext(memory)) is True

    def test_false_below_the_threshold(self):
        config = AmritaConfig()
        config.llm.compaction_trigger_ratio = 1.0
        ability = _ability(config, _preset(max_context=100))
        memory = MemoryModel(
            messages=[
                Message(role="user", content="u1"),
                Message(role="assistant", content="a1"),
                Message(role="user", content="u2"),
            ],
            usage=_usage(99),
        )
        assert should_compact.func(ability=ability, mem=MemoryContext(memory)) is False

    def test_false_without_a_measurement(self):
        ability = _ability(None, _preset(max_context=1))
        memory = MemoryModel(
            messages=[Message(role="user", content="u1")],
        )
        assert should_compact.func(ability=ability, mem=MemoryContext(memory)) is False

    def test_false_when_disabled(self):
        config = AmritaConfig()
        config.llm.enable_compaction = False
        ability = _ability(config, _preset(max_context=1))
        memory = MemoryModel(
            messages=[
                Message(role="user", content="u1"),
                Message(role="assistant", content="a1"),
                Message(role="user", content="u2"),
            ],
            usage=_usage(10**6),
        )
        assert should_compact.func(ability=ability, mem=MemoryContext(memory)) is False

    def test_false_when_there_is_nothing_to_fold(self):
        ability = _ability(None, _preset(max_context=1))
        memory = MemoryModel(
            messages=[Message(role="user", content="u1")], usage=_usage(10**6)
        )
        assert should_compact.func(ability=ability, mem=MemoryContext(memory)) is False


class TestCompact:
    @pytest.mark.asyncio
    async def test_folds_the_prefix_into_the_abstract(self):
        memory = MemoryModel(
            messages=[
                Message(role="user", content="u1"),
                Message(role="assistant", content="a1"),
                Message(role="user", content="u2"),
                Message(role="assistant", content="a2"),
            ],
            usage=_usage(500),
        )
        mem = MemoryContext(memory)
        with patch.object(
            ContextCompactor,
            "summarize",
            new=AsyncMock(return_value="a short summary"),
        ):
            # `Node.func` is typed sync-or-async, so the await cannot be proven.
            await COMPACT.func(  # pyright: ignore[reportGeneralTypeIssues]
                ability=_ability(), mem=mem, resp=RespState()
            )
        assert memory.abstract == "a short summary"
        assert [m.content for m in memory.messages] == ["u2", "a2"]
        assert memory.usage is None

    @pytest.mark.asyncio
    async def test_empty_summary_leaves_memory_untouched(self):
        memory = MemoryModel(
            messages=[
                Message(role="user", content="u1"),
                Message(role="assistant", content="a1"),
                Message(role="user", content="u2"),
            ],
            usage=_usage(500),
        )
        before = list(memory.messages)
        mem = MemoryContext(memory)
        with patch.object(
            ContextCompactor,
            "summarize",
            new=AsyncMock(return_value=""),
        ):
            await COMPACT.func(  # pyright: ignore[reportGeneralTypeIssues]
                ability=_ability(), mem=mem, resp=RespState()
            )
        assert memory.messages == before
        assert memory.abstract == ""
        assert memory.usage is not None

    @pytest.mark.asyncio
    async def test_no_prefix_is_a_noop(self):
        memory = MemoryModel(
            messages=[Message(role="user", content="u1")], usage=_usage(500)
        )
        mem = MemoryContext(memory)
        with patch.object(
            ContextCompactor,
            "summarize",
            new=AsyncMock(side_effect=AssertionError("must not summarize")),
        ):
            await COMPACT.func(  # pyright: ignore[reportGeneralTypeIssues]
                ability=_ability(), mem=mem, resp=RespState()
            )
        assert len(memory.messages) == 1
        assert memory.usage is not None

    @pytest.mark.asyncio
    async def test_missing_memory_raises(self):
        with pytest.raises(RuntimeError, match="LOAD_STATE"):
            await COMPACT.func(  # pyright: ignore[reportGeneralTypeIssues]
                ability=_ability(), mem=MemoryContext(None), resp=RespState()
            )


class TestSummarize:
    @pytest.mark.asyncio
    async def test_merges_the_previous_summary_into_the_prompt(self):
        captured: list[CONTENT_LIST_TYPE] = []

        async def fake_generator():
            yield UniResponse(content="  merged  ", tool_calls=None, usage=None)

        def fake_call(messages, **kwargs):
            captured.append(messages)
            return fake_generator()

        compactor = ContextCompactor(config=AmritaConfig(), preset=_preset())
        with patch(
            "amrita_core.components.compaction.call_completion",
            side_effect=fake_call,
        ):
            summary = await compactor.summarize(
                [Message(role="user", content="new turn")], "old summary"
            )
        assert summary == "merged"
        prompt = "".join(str(m.content) for m in captured[0] if isinstance(m, Message))
        assert "old summary" in prompt
        assert "new turn" in prompt

    @pytest.mark.asyncio
    async def test_empty_response_yields_an_empty_string(self):
        async def fake_generator():
            yield UniResponse(content="", tool_calls=None, usage=None)

        compactor = ContextCompactor(config=AmritaConfig(), preset=_preset())
        with patch(
            "amrita_core.components.compaction.call_completion",
            return_value=fake_generator(),
        ):
            summary = await compactor.summarize(
                [Message(role="user", content="new turn")]
            )
        assert summary == ""

    @pytest.mark.asyncio
    async def test_custom_instruction_reaches_the_summarizer(self):
        captured: list[CONTENT_LIST_TYPE] = []

        async def fake_generator():
            yield UniResponse(content="ok", tool_calls=None, usage=None)

        def fake_call(messages, **kwargs):
            captured.append(messages)
            return fake_generator()

        compactor = ContextCompactor(
            config=AmritaConfig(), preset=_preset(), instruction="CUSTOM PROMPT"
        )
        with patch(
            "amrita_core.components.compaction.call_completion",
            side_effect=fake_call,
        ):
            await compactor.summarize([Message(role="user", content="x")])
        assert captured[0][0].content == "CUSTOM PROMPT"

    @pytest.mark.asyncio
    async def test_fold_returns_the_tail_and_the_summary(self):
        async def fake_generator():
            yield UniResponse(content="folded", tool_calls=None, usage=None)

        compactor = ContextCompactor(config=AmritaConfig(), preset=_preset())
        messages: CONTENT_LIST_TYPE = [
            Message(role="user", content="u1"),
            Message(role="assistant", content="a1"),
            Message(role="user", content="u2"),
        ]
        with patch(
            "amrita_core.components.compaction.call_completion",
            return_value=fake_generator(),
        ):
            result = await compactor.fold(messages, "prior")
        assert result is not None
        assert result.summary == "folded"
        assert [m.content for m in result.messages] == ["u2"]

    @pytest.mark.asyncio
    async def test_fold_returns_none_without_a_prefix(self):
        compactor = ContextCompactor(config=AmritaConfig(), preset=_preset())
        result = await compactor.fold([Message(role="user", content="u1")])
        assert result is None


class TestNormalizeMessages:
    def test_flattens_text_blocks_for_user_messages(self):
        message = Message(
            role="user",
            content=[
                TextContent(type="text", text="hello "),
                TextContent(type="text", text="world"),
            ],
        )
        assert flatten_content(message) is True
        assert message.content == "hello world"

    def test_leaves_assistant_messages_alone(self):
        message = Message(
            role="assistant",
            content=[TextContent(type="text", text="hello")],
        )
        assert flatten_content(message) is False
        assert isinstance(message.content, list)

    def test_leaves_string_content_alone(self):
        message = Message(role="user", content="plain")
        assert flatten_content(message) is False
        assert message.content == "plain"

    def test_unknown_block_type_raises(self):
        message = Message(role="user", content=[])
        message.content = [{"type": "nonsense"}]
        with pytest.raises(ValueError, match="Invalid content type"):
            flatten_content(message)

    def test_node_skips_when_multimodal_is_enabled(self):
        config = AmritaConfig()
        config.llm.enable_multi_modal = True
        memory = MemoryModel(
            messages=[
                Message(
                    role="user",
                    content=[TextContent(type="text", text="hello")],
                )
            ]
        )
        NORMALIZE_MESSAGES.func(ability=_ability(config), mem=MemoryContext(memory))
        assert isinstance(memory.messages[0].content, list)

    def test_node_flattens_when_multimodal_is_disabled(self):
        config = AmritaConfig()
        config.llm.enable_multi_modal = False
        memory = MemoryModel(
            messages=[
                Message(
                    role="user",
                    content=[TextContent(type="text", text="hello")],
                )
            ]
        )
        NORMALIZE_MESSAGES.func(ability=_ability(config), mem=MemoryContext(memory))
        assert memory.messages[0].content == "hello"

    def test_node_requires_loaded_memory(self):
        config = AmritaConfig()
        config.llm.enable_multi_modal = False
        with pytest.raises(RuntimeError, match="LOAD_STATE"):
            NORMALIZE_MESSAGES.func(ability=_ability(config), mem=MemoryContext(None))


class TestOverflowDetection:
    @pytest.mark.parametrize(
        "message",
        [
            "This model's maximum context length is 128000 tokens.",
            "context_length_exceeded",
            "prompt is too long: 213459 tokens > 200000 maximum",
            "Input length and `max_tokens` exceed context limit",
            "too many tokens",
        ],
    )
    def test_known_provider_phrasings_match(self, message):
        assert is_context_overflow_error(RuntimeError(message)) is True

    @pytest.mark.parametrize(
        "message",
        ["connection reset by peer", "401 unauthorized", "rate limit exceeded"],
    )
    def test_unrelated_failures_do_not_match(self, message):
        assert is_context_overflow_error(RuntimeError(message)) is False


def _wrap_with_history() -> SendMessageWrap:
    """Wrap whose `memory` has a foldable prefix ahead of the newest turn."""
    return SendMessageWrap.validate_messages(
        [
            Message(role="system", content="sys"),
            Message(role="user", content="old u"),
            Message(role="assistant", content="old a"),
            Message(role="user", content="older u"),
            Message(role="assistant", content="older a"),
            Message(role="user", content="current u"),
        ]
    )


class TestOverflowRecovery:
    def _intp(self) -> MagicMock:
        intp = MagicMock()
        intp.object_io.yield_response = AsyncMock()
        return intp

    @pytest.mark.asyncio
    async def test_compacts_and_retries_once(self):
        seen: list[CONTENT_LIST_TYPE] = []

        def fake_call(messages, **kwargs):
            seen.append(messages)
            attempt = len(seen)

            async def overflow():
                raise ContextOverflowError("maximum context length is 128000 tokens")
                yield  # pragma: no cover

            async def ok():
                yield UniResponse(content="final", tool_calls=None, usage=_usage(7))

            return overflow() if attempt == 1 else ok()

        wok = WorkingState(context_wrap=_wrap_with_history())
        mem = MemoryContext(MemoryModel())
        resp = RespState()
        with (
            patch("amrita_core.components.llm.call_completion", side_effect=fake_call),
            patch(
                "amrita_core.components.llm.ContextCompactor.summarize",
                new=AsyncMock(return_value="folded summary"),
            ),
        ):
            await LLM_COMPLETION.func(  # pyright: ignore[reportGeneralTypeIssues]
                ability=_ability(None, _preset(max_context=100000)),
                mem=mem,
                wok=wok,
                intp=self._intp(),
                resp=resp,
            )
        assert len(seen) == 2  # failed call, then the retry
        assert resp.response is not None
        assert resp.response.content == "final"
        assert mem.memory is not None
        assert mem.memory.usage is not None
        wrap = wok.context_wrap
        assert wrap is not None
        assert wrap.memory[0].content == (
            "[Summary of earlier conversation]\nfolded summary"
        )
        assert [m.content for m in wrap.memory[1:]] == ["older u", "older a"]

    @pytest.mark.asyncio
    async def test_error_propagates_when_recovery_disabled(self):
        config = AmritaConfig()
        config.llm.enable_overflow_recovery = False

        def fake_call(messages, **kwargs):
            async def overflow():
                raise ContextOverflowError("maximum context length is 128000 tokens")
                yield  # pragma: no cover

            return overflow()

        with (
            patch("amrita_core.components.llm.call_completion", side_effect=fake_call),
            pytest.raises(ContextOverflowError),
        ):
            await LLM_COMPLETION.func(  # pyright: ignore[reportGeneralTypeIssues]
                ability=_ability(config, _preset(max_context=100000)),
                mem=MemoryContext(MemoryModel()),
                wok=WorkingState(context_wrap=_wrap_with_history()),
                intp=self._intp(),
                resp=RespState(),
            )

    @pytest.mark.asyncio
    async def test_error_propagates_when_nothing_can_be_folded(self):
        def fake_call(messages, **kwargs):
            async def overflow():
                raise ContextOverflowError("maximum context length is 128000 tokens")
                yield  # pragma: no cover

            return overflow()

        wrap = SendMessageWrap.validate_messages(
            [
                Message(role="system", content="sys"),
                Message(role="user", content="current u"),
            ]
        )
        with (
            patch("amrita_core.components.llm.call_completion", side_effect=fake_call),
            pytest.raises(ContextOverflowError),
        ):
            await LLM_COMPLETION.func(  # pyright: ignore[reportGeneralTypeIssues]
                ability=_ability(None, _preset(max_context=100000)),
                mem=MemoryContext(MemoryModel()),
                wok=WorkingState(context_wrap=wrap),
                intp=self._intp(),
                resp=RespState(),
            )
