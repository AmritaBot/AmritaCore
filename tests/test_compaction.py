"""History compaction: the ContextCompactor policy object, its nodes, and
message normalization."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.backends import LegacyBackend
from amrita_core.components.compaction import (
    MANAGE_CONTEXT,
    ContextCompactor,
    should_manage_context,
    split_history,
)
from amrita_core.components.llm import LLM_COMPLETION, _shrink_context
from amrita_core.components.normalize import NORMALIZE_MESSAGES, flatten_content
from amrita_core.config import AmritaConfig, LLMConfig
from amrita_core.contexts import (
    AbilityState,
    MemoryContext,
    RespState,
    WorkingState,
)
from amrita_core.exceptions import ContextOverflowError, is_context_overflow_error
from amrita_core.types import (
    CONTENT_LIST_TYPE,
    Function,
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
                    ToolCall(id="t1", function=Function(name="f", arguments="{}"))
                ],
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

    def test_enabled_tracks_the_strategy(self):
        config = AmritaConfig()
        assert ContextCompactor(config=config).enabled is True
        config.llm.context_strategy = "slide"
        assert ContextCompactor(config=config).enabled is True
        config.llm.context_strategy = "none"
        assert ContextCompactor(config=config).enabled is False

    def test_strategy_reads_the_config(self):
        config = AmritaConfig()
        assert ContextCompactor(config=config).strategy == "compact"
        config.llm.context_strategy = "slide"
        assert ContextCompactor(config=config).strategy == "slide"

    def test_needs_management_needs_a_measurement(self):
        config = AmritaConfig()
        config.llm.compaction_trigger_ratio = 1.0
        config.llm.memory_length_limit = 0
        compactor = ContextCompactor(config=config, preset=_preset(max_context=100))
        assert compactor.needs_management(None) is False
        assert compactor.needs_management(MemoryModel()) is False

    def test_message_limit_reads_the_config(self):
        config = AmritaConfig()
        config.llm.memory_length_limit = 42
        assert ContextCompactor(config=config).message_limit == 42


class TestSlideTargetGuard:
    """`slide_target_ratio` and `compaction_trigger_ratio` only mean anything
    as a pair: a target at or above the trigger trims the history straight
    back onto the trigger, so the ordering is enforced rather than documented.
    """

    def test_rejects_a_target_at_the_trigger(self):
        with pytest.raises(ValidationError):
            LLMConfig(compaction_trigger_ratio=0.5, slide_target_ratio=0.5)

    def test_rejects_a_target_above_the_trigger(self):
        with pytest.raises(ValidationError):
            LLMConfig(compaction_trigger_ratio=0.4, slide_target_ratio=0.6)

    def test_accepts_a_target_below_the_trigger(self):
        config = LLMConfig(compaction_trigger_ratio=0.8, slide_target_ratio=0.6)
        assert config.slide_target_ratio == 0.6


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
        config.llm.context_strategy = "none"
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
        assert (
            should_manage_context.func(ability=ability, mem=MemoryContext(memory))
            is True
        )

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
            await MANAGE_CONTEXT.func(  # pyright: ignore[reportGeneralTypeIssues]
                ability=ability, mem=mem, resp=RespState()
            )
        assert memory.abstract == "folded"
        assert len(memory.messages) == 2

    def test_slide_trims_to_the_ceiling_without_any_usage(self):
        """The fallback has to trim under `slide`, not merely fire the node.

        A gateway that reports no usage is the case `memory_length_limit`
        exists for; reporting `True` from `needs_management` and then doing
        nothing leaves that history unbounded.
        """
        config = AmritaConfig()
        config.llm.context_strategy = "slide"
        config.llm.memory_length_limit = 4
        compactor = ContextCompactor(config=config, preset=_preset(max_context=10**6))
        memory = self._history(10)
        assert memory.usage is None
        assert compactor.needs_management(memory) is True
        assert compactor.slide(memory.messages, None) == 6
        assert len(memory.messages) == 4

    def test_slide_trims_to_the_ceiling_below_the_token_trigger(self):
        config = AmritaConfig()
        config.llm.context_strategy = "slide"
        config.llm.memory_length_limit = 4
        compactor = ContextCompactor(config=config, preset=_preset(max_context=10**6))
        memory = self._history(10)
        memory.usage = _usage(10)
        assert compactor.needs_management(memory) is True
        assert compactor.slide(memory.messages, memory.usage.prompt_tokens) == 6
        assert len(memory.messages) == 4

    def test_slide_stays_put_below_the_ceiling(self):
        config = AmritaConfig()
        config.llm.context_strategy = "slide"
        config.llm.memory_length_limit = 4
        compactor = ContextCompactor(config=config, preset=_preset(max_context=10**6))
        memory = self._history(2)
        assert compactor.slide(memory.messages, None) == 0
        assert len(memory.messages) == 2

    def test_slide_ignores_the_ceiling_when_it_is_disabled(self):
        config = AmritaConfig()
        config.llm.context_strategy = "slide"
        config.llm.memory_length_limit = 0
        compactor = ContextCompactor(config=config, preset=_preset(max_context=10**6))
        memory = self._history(50)
        assert compactor.slide(memory.messages, None) == 0

    @pytest.mark.asyncio
    async def test_node_slides_on_the_fallback(self):
        config = AmritaConfig()
        config.llm.context_strategy = "slide"
        config.llm.memory_length_limit = 4
        ability = _ability(config, _preset(max_context=10**6))
        mem = MemoryContext(self._history(10))
        await MANAGE_CONTEXT.func(  # pyright: ignore[reportGeneralTypeIssues]
            ability=ability, mem=mem, resp=RespState()
        )
        assert mem.memory is not None
        assert len(mem.memory.messages) == 4
        assert mem.memory.usage is None


class TestSummaryOutputBudget:
    """The summarizer needs its own output ceiling.

    A reasoning model spends its output budget on thinking before it emits any
    content, so a summary call capped by a small ``max_output`` returns an empty
    answer and the fold silently does nothing.
    """

    def test_raises_the_ceiling_below_the_configured_budget(self):
        config = AmritaConfig()
        config.llm.compaction_max_tokens = 2048
        compactor = ContextCompactor(config=config, preset=_preset(max_output=200))

        assert compactor.summary_preset is not None
        assert compactor.summary_preset.max_output == 2048
        # The chat preset itself is untouched.
        assert compactor.preset is not None
        assert compactor.preset.max_output == 200

    def test_keeps_a_ceiling_that_is_already_high_enough(self):
        config = AmritaConfig()
        config.llm.compaction_max_tokens = 2048
        preset = _preset(max_output=8192)
        compactor = ContextCompactor(config=config, preset=preset)

        assert compactor.summary_preset is preset

    def test_zero_inherits_the_preset_value(self):
        config = AmritaConfig()
        config.llm.compaction_max_tokens = 0
        preset = _preset(max_output=200)
        compactor = ContextCompactor(config=config, preset=preset)

        assert compactor.summary_preset is preset

    def test_no_preset_stays_none(self):
        config = AmritaConfig()
        compactor = ContextCompactor(config=config, preset=None)

        assert compactor.summary_preset is None

    def test_falls_back_to_the_global_max_tokens(self):
        config = AmritaConfig()
        config.llm.compaction_max_tokens = 2048
        config.llm.max_tokens = 100
        compactor = ContextCompactor(config=config, preset=_preset())

        assert compactor.summary_preset is not None
        assert compactor.summary_preset.max_output == 2048


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
        assert (
            should_manage_context.func(ability=ability, mem=MemoryContext(memory))
            is True
        )

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
        assert (
            should_manage_context.func(ability=ability, mem=MemoryContext(memory))
            is False
        )

    def test_false_without_a_measurement(self):
        ability = _ability(None, _preset(max_context=1))
        memory = MemoryModel(
            messages=[Message(role="user", content="u1")],
        )
        assert (
            should_manage_context.func(ability=ability, mem=MemoryContext(memory))
            is False
        )

    def test_false_when_disabled(self):
        config = AmritaConfig()
        config.llm.context_strategy = "none"
        ability = _ability(config, _preset(max_context=1))
        memory = MemoryModel(
            messages=[
                Message(role="user", content="u1"),
                Message(role="assistant", content="a1"),
                Message(role="user", content="u2"),
            ],
            usage=_usage(10**6),
        )
        assert (
            should_manage_context.func(ability=ability, mem=MemoryContext(memory))
            is False
        )

    def test_false_when_there_is_nothing_to_fold(self):
        ability = _ability(None, _preset(max_context=1))
        memory = MemoryModel(
            messages=[Message(role="user", content="u1")], usage=_usage(10**6)
        )
        assert (
            should_manage_context.func(ability=ability, mem=MemoryContext(memory))
            is False
        )


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
            await MANAGE_CONTEXT.func(  # pyright: ignore[reportGeneralTypeIssues]
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
            await MANAGE_CONTEXT.func(  # pyright: ignore[reportGeneralTypeIssues]
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
            await MANAGE_CONTEXT.func(  # pyright: ignore[reportGeneralTypeIssues]
                ability=_ability(), mem=mem, resp=RespState()
            )
        assert len(memory.messages) == 1
        assert memory.usage is not None

    @pytest.mark.asyncio
    async def test_missing_memory_raises(self):
        with pytest.raises(RuntimeError, match="LOAD_STATE"):
            await MANAGE_CONTEXT.func(  # pyright: ignore[reportGeneralTypeIssues]
                ability=_ability(), mem=MemoryContext(None), resp=RespState()
            )


class TestSlide:
    """The `slide` policy: drop the oldest messages instead of summarizing."""

    @staticmethod
    def _history(turns: int, body: str = "x" * 40) -> MemoryModel:
        messages: CONTENT_LIST_TYPE = []
        for index in range(turns):
            messages.append(Message(role="user", content=f"u{index} {body}"))
            messages.append(Message(role="assistant", content=f"a{index} {body}"))
        return MemoryModel(messages=messages)

    @staticmethod
    def _compactor(
        *,
        window: int = 1000,
        trigger: float = 1.0,
        target: float = 0.5,
    ) -> ContextCompactor:
        config = AmritaConfig()
        config.llm.compaction_trigger_ratio = trigger
        config.llm.slide_target_ratio = target
        return ContextCompactor(config=config, preset=_preset(max_context=window))

    def test_slide_target_sits_below_the_threshold(self):
        compactor = self._compactor(window=1000, trigger=1.0, target=0.5)
        assert compactor.threshold == 1000
        assert compactor.slide_target == 500

    def test_estimate_sums_back_to_the_reported_total(self):
        memory = self._history(3)
        compactor = self._compactor(window=10**6)
        estimates = compactor._estimate(memory.messages, 900)
        assert len(estimates) == len(memory.messages)
        # Weighted shares are normalized against the reported total, so the
        # only error is in how the total is distributed.
        assert sum(estimates) == 900

    def test_estimate_weights_long_messages_higher(self):
        memory = MemoryModel(
            messages=[
                Message(role="user", content="short"),
                Message(role="assistant", content="y" * 400),
            ]
        )
        compactor = self._compactor(window=10**6)
        small, large = compactor._estimate(memory.messages, 1000)
        assert large > small

    def test_slide_drops_the_oldest_messages(self):
        memory = self._history(4)
        compactor = self._compactor(window=1000, trigger=1.0, target=0.5)
        dropped = compactor.slide(memory.messages, 1000)
        assert dropped > 0
        # Whatever survives starts a clean turn.
        assert memory.messages[0].role == "user"
        assert len(memory.messages) == len(self._history(4).messages) - dropped

    def test_slide_is_a_noop_below_the_threshold(self):
        memory = self._history(4)
        before = list(memory.messages)
        compactor = self._compactor(window=1000, trigger=1.0)
        assert compactor.slide(memory.messages, 10) == 0
        assert memory.messages == before

    def test_slide_never_empties_the_history(self):
        memory = self._history(3)
        compactor = self._compactor(window=1000, trigger=1.0, target=0.001)
        compactor.slide(memory.messages, 10**6)
        assert memory.messages

    def test_safe_cut_retreats_to_the_previous_turn(self):
        """A cut landing mid-turn must retreat so tool pairs stay together."""
        messages: CONTENT_LIST_TYPE = [
            Message(role="user", content="u1"),
            Message(role="assistant", content="a1"),
            Message(role="user", content="u2"),
            Message(role="assistant", content="a2"),
            Message(role="user", content="u3"),
        ]
        compactor = self._compactor()
        # Cutting at index 3 would strip the question but keep the answer.
        assert compactor._safe_cut(messages, 2) == 2
        assert compactor._safe_cut(messages, 3) == 2

    def test_safe_cut_advances_when_retreating_would_drop_nothing(self):
        """An oversized first turn must not make the cut a silent no-op."""
        messages: CONTENT_LIST_TYPE = [
            Message(role="user", content="u1"),
            Message(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(id="c1", function=Function(name="f", arguments="{}"))
                ],
            ),
            ToolResult(role="tool", name="f", content="r1", tool_call_id="c1"),
            Message(role="user", content="u2"),
        ]
        compactor = self._compactor()
        # Index 1 and 2 sit inside the first turn; retreating would be index 0.
        assert compactor._safe_cut(messages, 1) == 3
        assert compactor._safe_cut(messages, 2) == 3

    def test_safe_cut_skips_a_dangling_tool_result(self):
        """A history that arrives broken must not be sent on broken.

        The assistant that declared ``c1`` is gone, so the orphaned result at
        the head is invalid wherever the turn boundary sits — it has to be
        stepped over.
        """
        messages: CONTENT_LIST_TYPE = [
            # The assistant that declared c1 was dropped by an older version.
            ToolResult(role="tool", name="f", content="orphan", tool_call_id="c1"),
            Message(role="user", content="u1"),
            Message(role="assistant", content="a1"),
        ]
        compactor = self._compactor()
        assert compactor._safe_cut(messages, 0) == 1

    def test_safe_cut_keeps_a_paired_tool_result(self):
        """A result whose call survives is valid and must not be skipped."""
        messages: CONTENT_LIST_TYPE = [
            Message(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(id="c1", function=Function(name="f", arguments="{}"))
                ],
            ),
            ToolResult(role="tool", name="f", content="r1", tool_call_id="c1"),
            Message(role="user", content="u1"),
        ]
        compactor = self._compactor()
        assert compactor._safe_cut(messages, 0) == 0

    def test_slide_keeps_tool_pairs_intact(self):
        messages: CONTENT_LIST_TYPE = [
            Message(role="user", content="u1 " + "x" * 100),
            Message(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(id="c1", function=Function(name="f", arguments="{}"))
                ],
            ),
            ToolResult(role="tool", name="f", content="r1", tool_call_id="c1"),
            Message(role="assistant", content="a1"),
            Message(role="user", content="u2"),
            Message(role="assistant", content="a2"),
        ]
        memory = MemoryModel(messages=messages)
        compactor = self._compactor(window=1000, trigger=1.0, target=0.5)
        compactor.slide(memory.messages, 1000)
        declared = {
            tc.id
            for msg in memory.messages
            if isinstance(msg, Message) and msg.tool_calls
            for tc in msg.tool_calls
        }
        for msg in memory.messages:
            if isinstance(msg, ToolResult):
                assert msg.tool_call_id in declared

    def test_payload_stays_valid_after_slide(self):
        """The gateway validator is the oracle: a slid payload must pass it.

        ``libchat._validate_msg_list`` is exactly what every outbound request
        goes through, so round-tripping the survivors through it proves the
        cut cannot produce an orphaned tool result or a dangling call.
        """
        from amrita_core.libchat import _validate_msg_list

        messages: CONTENT_LIST_TYPE = [
            Message(role="user", content="u1 " + "x" * 200),
            Message(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(id="c1", function=Function(name="f", arguments="{}")),
                    ToolCall(id="c2", function=Function(name="g", arguments="{}")),
                ],
            ),
            ToolResult(role="tool", name="f", content="r1 " * 20, tool_call_id="c1"),
            ToolResult(role="tool", name="g", content="r2 " * 20, tool_call_id="c2"),
            Message(role="assistant", content="a1"),
            Message(role="user", content="u2 " + "x" * 200),
            Message(role="assistant", content="a2"),
        ]
        memory = MemoryModel(messages=messages)
        compactor = self._compactor(window=1000, trigger=1.0, target=0.5)
        dropped = compactor.slide(memory.messages, 1000)
        assert dropped > 0

        # Raises ValueError if any pairing invariant is broken.
        validated = _validate_msg_list(
            [Message(role="system", content="sys"), *memory.messages]
        )
        assert validated[0].role == "system"
        # The surviving tail is untouched, in order.
        assert [m.content for m in validated[1:]] == [
            m.content for m in memory.messages
        ]

    def test_should_compact_is_false_under_slide(self):
        """Sliding must never trigger a summary call."""
        memory = self._history(4, body="x" * 200)
        memory.usage = _usage(1000)
        compactor = self._compactor(window=1000, trigger=1.0)
        compactor.config.llm.context_strategy = "slide"
        assert compactor.needs_management(memory) is True
        assert compactor.should_compact(memory) is False

    @pytest.mark.asyncio
    async def test_node_dispatches_to_slide(self):
        config = AmritaConfig()
        config.llm.context_strategy = "slide"
        config.llm.compaction_trigger_ratio = 1.0
        config.llm.slide_target_ratio = 0.5
        memory = self._history(4, body="x" * 200)
        memory.usage = _usage(1000)
        mem = MemoryContext(memory)
        with patch.object(
            ContextCompactor,
            "summarize",
            new=AsyncMock(side_effect=AssertionError("slide must not summarize")),
        ):
            await MANAGE_CONTEXT.func(  # pyright: ignore[reportGeneralTypeIssues]
                ability=_ability(config, _preset(max_context=1000)),
                mem=mem,
                resp=RespState(),
            )
        assert memory.abstract == ""
        assert memory.usage is None
        assert memory.messages[0].role == "user"
        assert len(memory.messages) < len(self._history(4, body="x" * 200).messages)

    def test_safe_cut_refuses_a_stranded_result(self):
        """A result whose declaring call sits in the dropped prefix is invalid
        wherever the boundary lands, so no cut is taken: sending the payload
        on would cost the whole request.
        """
        messages: CONTENT_LIST_TYPE = [
            Message(role="user", content="u1"),
            Message(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(id="c1", function=Function(name="f", arguments="{}"))
                ],
            ),
            Message(role="user", content="u2"),
            ToolResult(role="tool", name="f", content="r1", tool_call_id="c1"),
            Message(role="assistant", content="a2"),
        ]
        compactor = self._compactor()
        assert compactor._safe_cut(messages, 2) == 0


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

    @pytest.mark.asyncio
    async def test_slides_instead_of_folding_under_the_slide_policy(self):
        """Overflow recovery follows the policy: `slide` never pays for a
        summary call, and never rewrites a history it was told to keep
        verbatim.
        """
        config = AmritaConfig()
        config.llm.context_strategy = "slide"
        wok = WorkingState(context_wrap=_wrap_with_history())
        with patch(
            "amrita_core.components.llm.ContextCompactor.fold", new=AsyncMock()
        ) as folded:
            recovered = await _shrink_context(
                _ability(config, _preset(max_context=100000)), wok, RespState()
            )
        assert recovered is True
        folded.assert_not_awaited()
        wrap = wok.context_wrap
        assert wrap is not None
        assert len(wrap.memory) < 5
        assert wrap.memory[0].role == "user"
        assert not any(
            str(message.content).startswith("[Summary of earlier conversation]")
            for message in wrap.memory
        )
