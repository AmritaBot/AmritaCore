"""Tests for the native step-loop (NATIVE instruction set) built-in ReAct.

Covers:
- ``AgentRunState`` semantics (begin_step, stall detection, DAG readiness).
- Step lifecycle hooks (intro_step / leave_step) on ReActAgentStrategy.
- Stall detection → give-up prompt injection (once per Step).
- ``_summarize_step`` degradation path.
- ``_handle_update_step`` plan revisions.
- ``STEP_REACT_BLOCK`` / ``STEP_BODY`` NATIVE rendering.
"""

import pytest

from amrita_core.agent.context import StrategyContext
from amrita_core.builtins.agent.state import (
    AgentRunState,
    DAGNode,
    DecomposeDecision,
    StepSummary,
    TokenBudget,
)
from amrita_core.builtins.workflows import STEP_BODY, STEP_REACT_BLOCK
from amrita_core.config import AmritaConfig, FunctionConfig, LLMConfig
from amrita_core.types import Function, Message, SendMessageWrap

# AgentRunState


class TestAgentRunState:
    def test_begin_step_resets_per_step_state(self):
        rs = AgentRunState()
        rs.begin_step("execute")
        assert rs.step_index == 1
        assert rs.current_phase == "execute"
        assert rs.step_tool_signatures == []
        assert rs.stall_injected is False

    def test_stall_detection_identical_signatures(self):
        rs = AgentRunState()
        rs.begin_step("execute")
        for _ in range(3):
            rs.record_tool_call("search(123)")
        assert rs.is_stalled(3) is True
        assert rs.is_stalled(4) is False

    def test_stall_detection_mixed_signatures(self):
        rs = AgentRunState()
        rs.begin_step("execute")
        rs.record_tool_call("search(1)")
        rs.record_tool_call("search(2)")
        rs.record_tool_call("search(1)")
        assert rs.is_stalled(3) is False

    def test_would_stall_pre_execution(self):
        """would_stall predicts the stall *before* the call is recorded."""
        rs = AgentRunState()
        rs.begin_step("execute")
        trigger = 3
        # 0 recorded → no stall possible.
        assert rs.would_stall("search(1)", trigger) is False
        rs.record_tool_call("search(1)")
        # 1 recorded → still below trigger-1 window.
        assert rs.would_stall("search(1)", trigger) is False
        rs.record_tool_call("search(1)")
        # 2 recorded (= trigger-1) and all identical → recording a 3rd
        # identical signature would trip the detector.
        assert rs.would_stall("search(1)", trigger) is True
        # A different signature does not trip it.
        assert rs.would_stall("search(2)", trigger) is False
        # Threshold 1 never cancels (no window to compare).
        assert rs.would_stall("search(1)", 1) is False

    def test_would_stall_interleaved_not_cancelled(self):
        """read → edit → read pattern must NOT be cancelled."""
        rs = AgentRunState()
        rs.begin_step("execute")
        rs.record_tool_call("read(a)")
        rs.record_tool_call("edit(a)")
        # Only the last trigger-1 entries matter: ["edit(a)"] ≠ "read(a)".
        assert rs.would_stall("read(a)", 3) is False
        # But read → read → read is.
        rs2 = AgentRunState()
        rs2.begin_step("execute")
        rs2.record_tool_call("read(a)")
        rs2.record_tool_call("read(a)")
        assert rs2.would_stall("read(a)", 3) is True

    def test_dag_readiness(self):
        rs = AgentRunState()
        rs.plan = [
            DAGNode(id="a", description="first", depends_on=[]),
            DAGNode(id="b", description="second", depends_on=["a"]),
            DAGNode(id="c", description="third", depends_on=["a", "b"]),
        ]
        # Only 'a' is ready initially.
        assert rs.next_ready_node() is not None
        assert rs.next_ready_node().id == "a"  # type: ignore[union-attr]

        rs.current_step_id = "a"
        rs.complete_current_node()
        assert rs.next_ready_node().id == "b"  # type: ignore[union-attr]

        rs.current_step_id = "b"
        rs.complete_current_node()
        assert rs.next_ready_node().id == "c"  # type: ignore[union-attr]

        rs.current_step_id = "c"
        rs.complete_current_node()
        assert rs.next_ready_node() is None
        assert rs.all_plan_done() is True

    def test_simple_mode_no_plan(self):
        rs = AgentRunState()
        rs.simple_mode = True
        assert rs.plan is None
        assert rs.all_plan_done() is True

    def test_token_budget_update(self):
        budget = TokenBudget()
        usage = type(
            "U", (), {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        )()
        budget.update(usage)
        assert budget.prompt_tokens == 10
        assert budget.completion_tokens == 5
        assert budget.total_tokens == 15
        budget.update(None)  # no-op
        assert budget.prompt_tokens == 10

    def test_decompose_decision_and_summary_models(self):
        d = DecomposeDecision(needs_decomposition=True, dag=[DAGNode(id="s1")])
        assert d.needs_decomposition is True
        s = StepSummary(verb="Reviewed", object="codebase")
        assert s.verb == "Reviewed"
        assert s.object == "codebase"


# NATIVE workflow rendering


class TestNativeWorkflowRender:
    def test_step_body_renders(self):
        rendered = STEP_BODY.render()
        assert len(rendered) > 0

    def test_step_react_block_renders(self):
        rendered = STEP_REACT_BLOCK.render()
        assert len(rendered) > 0

    def test_native_loop_executes_once(self):
        """Minimal NATIVE_DO smoke test: condition False → body runs once."""
        from amrita_sense.instructions.native import NATIVE_DO
        from amrita_sense.node import Node
        from amrita_sense.runtime.workflow import WorkflowInterpreter

        @Node()
        def cond() -> bool:
            return False

        @Node()
        def body() -> str:
            return "exec"

        rendered = NATIVE_DO(body).WHILE(cond).extract().render()
        results = []

        async def main():
            interp = WorkflowInterpreter(rendered)
            async for r in interp.run_step_by():
                results.append(r)

        import asyncio

        asyncio.run(main())
        assert "exec" in results


# Strategy-level step lifecycle (ReActAgentStrategy)


@pytest.fixture
def strategy():
    from unittest.mock import AsyncMock, MagicMock

    from amrita_core.builtins.agent.react_comm import ReActAgentStrategy
    from amrita_core.chatmanager import ChatObject

    config = AmritaConfig()
    config.function_config = FunctionConfig()
    config.llm = LLMConfig()
    config.builtin.loop_reasoning_trigger = 2

    chat_obj = MagicMock(spec=ChatObject)
    chat_obj.session_id = "test-session"
    chat_obj.preset = "default-preset"
    chat_obj.config = config
    chat_obj.io_stream = MagicMock()
    chat_obj.io_stream.yield_response = AsyncMock()
    chat_obj.io_stream.set_queue_done = AsyncMock()

    train_msg = Message(role="system", content="Test system message")
    user_msg = Message(role="user", content="test user input")
    original_context = SendMessageWrap(
        train=train_msg,
        memory=[user_msg],
        user_query=user_msg,
    )
    ctx = StrategyContext(
        user_input="test user input",
        original_context=original_context,
        chat_object=chat_obj,
    )
    st = ReActAgentStrategy(ctx)
    st.tools_manager = MagicMock()
    st.tools_manager.tools_meta = MagicMock(return_value={})
    return st


class TestStrategyStepLifecycle:
    def test_intro_step_advances_state(self, strategy):
        # Node-driven: in simple mode intro_step uses the implicit "execute"
        # Step regardless of the phase argument.
        asyncio_run(strategy.intro_step("analyze"))
        rs = strategy.run_state
        assert rs is not None
        assert rs.step_index == 1
        assert rs.current_phase == "execute"

    def test_intro_step_node_driven(self, strategy):
        """Plan mode: intro_step picks the next ready DAG node (topological)."""
        rs = strategy._init_run_state()
        rs.plan = [
            DAGNode(id="a", description="first", depends_on=[]),
            DAGNode(id="b", description="second", depends_on=["a"]),
        ]
        asyncio_run(strategy.intro_step("node"))
        assert rs.step_index == 1
        assert rs.current_phase == "a"
        assert rs.current_step_id == "a"

        # Complete node a; next intro picks b.
        rs.complete_current_node()
        asyncio_run(strategy.intro_step("node"))
        assert rs.step_index == 2
        assert rs.current_phase == "b"
        assert rs.current_step_id == "b"

    def test_record_signature_and_stall(self, strategy):
        asyncio_run(strategy.intro_step("execute"))
        from amrita_core.types import ToolCall

        for _ in range(3):
            strategy._record_tool_signature(
                ToolCall(
                    id="t1",
                    function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
                )
            )
        assert strategy._detect_step_stall() is True

    def test_give_up_prompt_injected_once(self, strategy):
        asyncio_run(strategy.intro_step("execute"))
        from amrita_core.types import ToolCall

        for _ in range(3):
            strategy._record_tool_signature(
                ToolCall(
                    id="t1",
                    function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
                )
            )
        assert strategy._detect_step_stall() is True
        asyncio_run(strategy._inject_give_up_prompt())
        asyncio_run(strategy._inject_give_up_prompt())  # second call must be a no-op
        rs = strategy.run_state
        assert rs.stall_injected is True
        # Exactly one user message appended with the give-up text.
        user_msgs = [
            m
            for m in strategy.ctx.message.unwrap(exclude_system=True)
            if getattr(m, "role", None) == "user"
            and "Give up when there are no solutions." in getattr(m, "content", "")
        ]
        assert len(user_msgs) == 1

    def test_summarize_step_degradation(self, strategy):
        """_summarize_step falls back gracefully when the LLM output is bad."""
        import asyncio
        from unittest.mock import patch

        asyncio_run(strategy.intro_step("execute"))

        async def fake_bad_generator():
            from amrita_core.types import UniResponse

            yield UniResponse(content="not json at all", tool_calls=None, usage=None)

        with patch(
            "amrita_core.builtins.agent.react_comm.call_completion",
            return_value=fake_bad_generator(),
        ):
            asyncio.run(strategy._summarize_step())
        rs = strategy.run_state
        assert rs.last_summary is not None
        assert rs.last_summary.verb == "Completed"  # degradation fallback
        assert rs.last_summary.object == "execute"

    def test_update_step_replan(self, strategy):
        asyncio_run(strategy.intro_step("analyze"))
        rs = strategy.run_state
        rs.plan = [DAGNode(id="a", description="old")]
        asyncio_run(
            strategy._handle_update_step(
                {"action": "replan", "dag": [{"id": "x", "description": "new"}]}
            )
        )
        assert [n.id for n in rs.plan] == ["x"]
        assert rs.plan_revision == 1

    def test_update_step_mark_done_and_remove(self, strategy):
        asyncio_run(strategy.intro_step("analyze"))
        rs = strategy.run_state
        rs.plan = [
            DAGNode(id="a", description="first"),
            DAGNode(id="b", description="second"),
        ]
        rs.current_step_id = "a"
        asyncio_run(strategy._handle_update_step({"action": "mark_done"}))
        assert rs.completed_step_ids == ["a"]
        asyncio_run(
            strategy._handle_update_step({"action": "remove_step", "node_id": "b"})
        )
        assert [n.id for n in rs.plan] == ["a"]

    # Step metadata emission (phase 2: push meta messages to the stream)

    def _captured_metadata(self, strategy):
        """All (content, metadata) pairs pushed via io_stream.yield_response."""
        return [
            call.args[0].get_full_content()["metadata"]
            for call in strategy.ctx.chat_object.io_stream.yield_response.call_args_list
            if hasattr(call.args[0], "get_full_content")
        ]

    def test_intro_emits_step_metadata(self, strategy):
        asyncio_run(strategy.intro_step("analyze"))
        metas = self._captured_metadata(strategy)
        assert any(
            m.get("type") == "step"
            and m.get("extra_type") == "intro"
            and m.get("phase") == "execute"
            and m.get("step_index") == 1
            for m in metas
        )

    def test_intro_node_emits_step_metadata(self, strategy):
        """Plan mode intro emits metadata with the DAG node id as phase."""
        rs = strategy._init_run_state()
        rs.plan = [DAGNode(id="search-web", description="Search the web")]
        asyncio_run(strategy.intro_step("node"))
        metas = self._captured_metadata(strategy)
        assert any(
            m.get("type") == "step"
            and m.get("extra_type") == "intro"
            and m.get("phase") == "search-web"
            and m.get("current_step_id") == "search-web"
            for m in metas
        )

    def test_simple_mode_skips_plan_verify_metadata(self, strategy):
        asyncio_run(strategy.intro_step("analyze"))  # triggers decomposition
        rs = strategy.run_state
        rs.simple_mode = True
        asyncio_run(strategy.intro_step("plan"))
        asyncio_run(strategy.intro_step("verify"))
        metas = self._captured_metadata(strategy)
        # Simple-mode plan/verify intro events must NOT be emitted.
        assert not any(
            m.get("extra_type") == "intro" and m.get("phase") in ("plan", "verify")
            for m in metas
        )

    def test_leave_execute_emits_summary_metadata(self, strategy):
        from unittest.mock import AsyncMock, patch

        asyncio_run(strategy.intro_step("execute"))
        rs = strategy.run_state
        rs.last_summary = StepSummary(verb="Reviewed", object="codebase")

        with patch.object(strategy, "_summarize_step", new=AsyncMock()):
            asyncio_run(strategy.leave_step("execute"))
        metas = self._captured_metadata(strategy)
        leave_metas = [
            m
            for m in metas
            if m.get("type") == "step" and m.get("extra_type") == "leave"
        ]
        assert leave_metas, "expected a step-leave metadata event"
        last = leave_metas[-1]
        assert last["phase"] == "execute"
        assert last["summary_verb"] == "Reviewed"
        assert last["summary_object"] == "codebase"

    def test_stall_emits_stall_metadata(self, strategy):
        asyncio_run(strategy.intro_step("execute"))
        rs = strategy.run_state
        for _ in range(3):
            rs.record_tool_call("search(123)")
        assert rs.is_stalled(2) is True
        asyncio_run(strategy._inject_give_up_prompt())
        metas = self._captured_metadata(strategy)
        assert any(
            m.get("type") == "step"
            and m.get("extra_type") == "stall"
            and m.get("injected") is True
            and m.get("signatures") == ["search(123)", "search(123)", "search(123)"]
            for m in metas
        )

    def test_after_iteration_injects_give_up_on_stall(self, strategy):
        """after_iteration (per-iteration hook) stops a stalled loop in place."""
        from amrita_core.types import ToolCall

        asyncio_run(strategy.intro_step("execute"))
        rs = strategy.run_state
        assert rs.stall_injected is False

        # One round below the trigger threshold (trigger=2) → no injection.
        strategy._record_tool_signature(
            ToolCall(
                id="t0",
                function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
            )
        )
        asyncio_run(strategy.after_iteration())
        assert rs.stall_injected is False
        assert rs.exec_finished is False

        # Second identical signature crosses the trigger → give-up injected
        # and the loop termination flags are set.
        strategy._record_tool_signature(
            ToolCall(
                id="t1",
                function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
            )
        )
        asyncio_run(strategy.after_iteration())
        assert rs.stall_injected is True
        assert rs.exec_finished is True

        # Idempotent: further after_iteration calls must not re-inject.
        strategy._record_tool_signature(
            ToolCall(
                id="t2",
                function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
            )
        )
        asyncio_run(strategy.after_iteration())
        user_msgs = [
            m
            for m in strategy.ctx.message.unwrap(exclude_system=True)
            if getattr(m, "role", None) == "user"
            and "Give up when there are no solutions." in getattr(m, "content", "")
        ]
        assert len(user_msgs) == 1

    # Thinking-mode round-trip (DeepSeek requires reasoning_content back)

    def test_append_tool_result_carries_reasoning_content(self, strategy):
        """Assistant tool-call messages must carry the provider reasoning back.

        DeepSeek thinking mode rejects payloads whose assistant messages drop
        the ``reasoning_content`` (HTTP 400 "must be passed back to the API").
        """
        from amrita_core.types import ToolCall, UniResponse

        asyncio_run(strategy.intro_step("execute"))
        tool_call = ToolCall(
            id="t1",
            function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
        )
        response_msg = UniResponse(
            content=None,
            tool_calls=[tool_call],
            reasoning_content="thinking about the search",
        )
        asyncio_run(
            strategy._append_tool_result_to_context(tool_call, "result", response_msg)
        )
        msgs = strategy.ctx.message.unwrap(exclude_system=True)
        assistant_msgs = [m for m in msgs if m.role == "assistant"]
        assert assistant_msgs, "expected an assistant tool-call message"
        assert assistant_msgs[-1].reasoning_content == "thinking about the search"

    def test_append_tool_result_without_reasoning(self, strategy):
        """No reasoning_content → assistant message simply omits it."""
        from amrita_core.types import ToolCall, UniResponse

        asyncio_run(strategy.intro_step("execute"))
        tool_call = ToolCall(
            id="t1",
            function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
        )
        response_msg = UniResponse(content=None, tool_calls=[tool_call])
        asyncio_run(
            strategy._append_tool_result_to_context(tool_call, "result", response_msg)
        )
        msgs = strategy.ctx.message.unwrap(exclude_system=True)
        assistant_msgs = [m for m in msgs if m.role == "assistant"]
        assert assistant_msgs[-1].reasoning_content is None

    # Pre-execution cancellation (tool returns "Cancelled: ..." on stall)

    def test_should_cancel_tool_call_on_repeating_window(self, strategy):
        from amrita_core.types import ToolCall

        asyncio_run(strategy.intro_step("execute"))

        def make_call(i):
            return ToolCall(
                id=f"t{i}",
                function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
            )

        # trigger=2 (fixture). First call: recorded, not cancelled.
        c1 = make_call(1)
        strategy._record_tool_signature(c1)
        assert strategy._should_cancel_tool_call(c1) is False
        # Second identical call: stall window formed → cancel.
        c2 = make_call(2)
        strategy._record_tool_signature(c2)
        assert strategy._should_cancel_tool_call(c2) is True

    def test_should_cancel_after_stall_injected(self, strategy):
        from amrita_core.types import ToolCall

        asyncio_run(strategy.intro_step("execute"))
        rs = strategy.run_state
        rs.stall_injected = True
        tool_call = ToolCall(
            id="t1",
            function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
        )
        # Once stalled, every further call is cancelled.
        assert strategy._should_cancel_tool_call(tool_call) is True


# Step lifecycle events (mutable events + StepAbortError control flow)


class TestStepLifecycleEvents:
    @pytest.fixture
    def strategy(self):
        from unittest.mock import AsyncMock, MagicMock

        from amrita_core.builtins.agent.react_comm import ReActAgentStrategy
        from amrita_core.chatmanager import ChatObject

        config = AmritaConfig()
        config.function_config = FunctionConfig()
        config.llm = LLMConfig()
        config.builtin.loop_reasoning_trigger = 2

        chat_obj = MagicMock(spec=ChatObject)
        chat_obj.session_id = "test-session"
        chat_obj.preset = "default-preset"
        chat_obj.config = config
        chat_obj.io_stream = MagicMock()
        chat_obj.io_stream.yield_response = AsyncMock()
        chat_obj.io_stream.set_queue_done = AsyncMock()

        train_msg = Message(role="system", content="Test system message")
        user_msg = Message(role="user", content="test user input")
        original_context = SendMessageWrap(
            train=train_msg,
            memory=[user_msg],
            user_query=user_msg,
        )
        ctx = StrategyContext(
            user_input="test user input",
            original_context=original_context,
            chat_object=chat_obj,
        )
        st = ReActAgentStrategy(ctx)
        st.tools_manager = MagicMock()
        st.tools_manager.tools_meta = MagicMock(return_value={})
        return st

    def test_intro_event_phase_override(self, strategy):
        """A matcher can redirect the Step phase via the mutable event."""
        from amrita_sense.hook.matcher import Matcher

        from amrita_core.builtins.agent.events import StepIntroEvent

        rs = strategy._init_run_state()

        matcher = Matcher("agent.step_intro", priority=1)

        async def override_phase(ev: StepIntroEvent):
            ev.override_phase = "custom-phase"

        matcher.handle()(override_phase)
        try:
            asyncio_run(strategy.intro_step("execute"))
            assert rs.current_phase == "custom-phase"
        finally:
            matcher._dead_at = datetime_now()

    def test_leave_event_summary_override(self, strategy):
        """A matcher can override the subject-predicate summary."""
        from unittest.mock import AsyncMock, patch

        from amrita_sense.hook.matcher import Matcher

        from amrita_core.builtins.agent.events import StepLeaveEvent

        rs = strategy._init_run_state()

        matcher = Matcher("agent.step_leave", priority=1)

        async def override_summary(ev: StepLeaveEvent):
            ev.override_verb = "Reviewed"
            ev.override_object = "codebase"

        matcher.handle()(override_summary)
        try:
            asyncio_run(strategy.intro_step("execute"))
            with patch.object(strategy, "_summarize_step", new=AsyncMock()):
                asyncio_run(strategy.leave_step("execute"))
            assert rs.last_summary is not None
            assert rs.last_summary.verb == "Reviewed"
            assert rs.last_summary.object == "codebase"
        finally:
            matcher._dead_at = datetime_now()

    def test_iteration_event_abort_ends_step(self, strategy):
        """StepAbortError from a matcher ends the Step (exec_finished)."""
        from amrita_sense.hook.matcher import Matcher

        from amrita_core.builtins.agent.events import (
            StepAbortError,
            StepIterationEvent,
        )

        rs = strategy._init_run_state()

        matcher = Matcher("agent.step_iteration", priority=1)

        async def abort(ev: StepIterationEvent):
            raise StepAbortError("stop now")

        matcher.handle()(abort)
        try:
            asyncio_run(strategy.intro_step("execute"))
            assert rs.exec_finished is False
            asyncio_run(strategy.after_iteration())
            assert rs.exec_finished is True
        finally:
            matcher._dead_at = datetime_now()

    def test_iteration_event_end_step_flag(self, strategy):
        """A matcher can end the Step by setting end_step=True."""
        from amrita_sense.hook.matcher import Matcher

        from amrita_core.builtins.agent.events import StepIterationEvent

        rs = strategy._init_run_state()

        matcher = Matcher("agent.step_iteration", priority=1)

        async def end_step(ev: StepIterationEvent):
            ev.end_step = True

        matcher.handle()(end_step)
        try:
            asyncio_run(strategy.intro_step("execute"))
            asyncio_run(strategy.after_iteration())
            assert rs.exec_finished is True
        finally:
            matcher._dead_at = datetime_now()

    # Tool-call events (pre-call rewrite/cancel, post-call rewrite/skip)

    def test_tool_call_event_cancel(self, strategy):
        """A matcher can cancel a regular tool call before execution."""
        from amrita_sense.hook.matcher import Matcher

        from amrita_core.builtins.agent.events import StepToolCallEvent
        from amrita_core.types import ToolCall

        matcher = Matcher("agent.tool_call", priority=1)

        async def cancel_call(ev: StepToolCallEvent):
            ev.cancel = True

        matcher.handle()(cancel_call)
        tool_call = ToolCall(
            id="t1",
            function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
        )
        try:
            args, cancel = asyncio_run(strategy._trigger_tool_call_event(tool_call))
            assert cancel is True
            assert args == "{}"
        finally:
            matcher._dead_at = datetime_now()

    def test_tool_call_event_abort(self, strategy):
        """StepAbortError from a pre-call matcher cancels the call."""
        from amrita_sense.hook.matcher import Matcher

        from amrita_core.builtins.agent.events import (
            StepAbortError,
            StepToolCallEvent,
        )
        from amrita_core.types import ToolCall

        matcher = Matcher("agent.tool_call", priority=1)

        async def abort(ev: StepToolCallEvent):
            raise StepAbortError("stop tool")

        matcher.handle()(abort)
        tool_call = ToolCall(
            id="t1",
            function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
        )
        try:
            args, cancel = asyncio_run(strategy._trigger_tool_call_event(tool_call))
            assert cancel is True
            assert args == "{}"
        finally:
            matcher._dead_at = datetime_now()

    def test_tool_call_event_rewrites_arguments(self, strategy):
        """A matcher can rewrite tool arguments before execution."""
        from amrita_sense.hook.matcher import Matcher

        from amrita_core.builtins.agent.events import StepToolCallEvent
        from amrita_core.types import ToolCall

        matcher = Matcher("agent.tool_call", priority=1)

        async def rewrite(ev: StepToolCallEvent):
            ev.arguments = '{"q": "patched"}'

        matcher.handle()(rewrite)
        tool_call = ToolCall(
            id="t1",
            function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
        )
        try:
            args, cancel = asyncio_run(strategy._trigger_tool_call_event(tool_call))
            assert cancel is False
            assert args == '{"q": "patched"}'
        finally:
            matcher._dead_at = datetime_now()

    def test_tool_return_event_rewrites_result(self, strategy):
        """A matcher can rewrite the tool result before append."""
        from amrita_sense.hook.matcher import Matcher

        from amrita_core.builtins.agent.events import StepToolReturnEvent
        from amrita_core.types import ToolCall

        matcher = Matcher("agent.tool_return", priority=1)

        async def rewrite(ev: StepToolReturnEvent):
            ev.result = "patched result"

        matcher.handle()(rewrite)
        tool_call = ToolCall(
            id="t1",
            function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
        )
        try:
            result, skip_append = asyncio_run(
                strategy._trigger_tool_return_event(tool_call, "raw result")
            )
            assert skip_append is False
            assert result == "patched result"
        finally:
            matcher._dead_at = datetime_now()

    def test_tool_return_event_skip_append(self, strategy):
        """A matcher can skip writing the result back to context."""
        from amrita_sense.hook.matcher import Matcher

        from amrita_core.builtins.agent.events import StepToolReturnEvent
        from amrita_core.types import ToolCall

        matcher = Matcher("agent.tool_return", priority=1)

        async def skip(ev: StepToolReturnEvent):
            ev.skip_append = True

        matcher.handle()(skip)
        tool_call = ToolCall(
            id="t1",
            function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
        )
        try:
            result, skip_append = asyncio_run(
                strategy._trigger_tool_return_event(tool_call, "raw result")
            )
            assert skip_append is True
            assert result == "raw result"
        finally:
            matcher._dead_at = datetime_now()

    def test_tool_return_event_abort(self, strategy):
        """StepAbortError from a post-call matcher skips the append."""
        from amrita_sense.hook.matcher import Matcher

        from amrita_core.builtins.agent.events import (
            StepAbortError,
            StepToolReturnEvent,
        )
        from amrita_core.types import ToolCall

        matcher = Matcher("agent.tool_return", priority=1)

        async def abort(ev: StepToolReturnEvent):
            raise StepAbortError("skip result")

        matcher.handle()(abort)
        tool_call = ToolCall(
            id="t1",
            function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
        )
        try:
            result, skip_append = asyncio_run(
                strategy._trigger_tool_return_event(tool_call, "raw result")
            )
            assert skip_append is True
            assert result == "raw result"
        finally:
            matcher._dead_at = datetime_now()

    def test_exec_one_cancel_short_circuits_call(self, strategy):
        """Cancelled tool calls never reach call_tool."""
        from unittest.mock import AsyncMock, patch

        from amrita_sense.hook.matcher import Matcher

        from amrita_core.builtins.agent.events import StepToolCallEvent
        from amrita_core.types import ToolCall, UniResponse

        matcher = Matcher("agent.tool_call", priority=1)

        async def cancel_call(ev: StepToolCallEvent):
            ev.cancel = True

        matcher.handle()(cancel_call)
        tool_call = ToolCall(
            id="t1",
            function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
        )
        response_msg = UniResponse(content=None, tool_calls=[tool_call])
        try:
            with patch.object(strategy, "call_tool", new=AsyncMock()) as call_tool:
                should_continue = asyncio_run(strategy._execute_tool_loop(response_msg))
            assert should_continue is True
            call_tool.assert_not_awaited()
        finally:
            matcher._dead_at = datetime_now()

    def test_exec_one_skips_append_on_skip_flag(self, strategy):
        """skip_append=True → nothing is written back to the context."""
        from unittest.mock import AsyncMock, patch

        from amrita_sense.hook.matcher import Matcher

        from amrita_core.builtins.agent.events import StepToolReturnEvent
        from amrita_core.types import ToolCall, UniResponse

        matcher = Matcher("agent.tool_return", priority=1)

        async def skip(ev: StepToolReturnEvent):
            ev.skip_append = True

        matcher.handle()(skip)
        tool_call = ToolCall(
            id="t1",
            function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
        )
        response_msg = UniResponse(content=None, tool_calls=[tool_call])
        try:
            with patch.object(
                strategy, "call_tool", new=AsyncMock(return_value="raw result")
            ):
                asyncio_run(strategy._execute_tool_loop(response_msg))
            tool_msgs = [
                m
                for m in strategy.ctx.message.unwrap(exclude_system=True)
                if getattr(m, "role", None) == "tool"
            ]
            assert not any(
                getattr(m, "content", None) == "raw result" for m in tool_msgs
            )
        finally:
            matcher._dead_at = datetime_now()


# Peer input (reverse stream): send_to_producer → drained at Step boundary


class TestPeerInputDrain:
    """Peer messages pushed via the reverse stream land in the context."""

    @pytest.fixture
    def strategy(self):
        from unittest.mock import MagicMock

        from amrita_sense.streaming import SuspendObjectStream

        from amrita_core.builtins.agent.react_comm import ReActAgentStrategy
        from amrita_core.chatmanager import ChatObject

        config = AmritaConfig()
        config.function_config = FunctionConfig()
        config.llm = LLMConfig()
        config.builtin.loop_reasoning_trigger = 2

        chat_obj = MagicMock(spec=ChatObject)
        chat_obj.session_id = "test-session"
        chat_obj.preset = "default-preset"
        chat_obj.config = config
        # Real bidirectional stream: yield_response buffers internally
        # (no consumer attached) and the reverse channel stays usable.
        chat_obj.io_stream = SuspendObjectStream()

        train_msg = Message(role="system", content="Test system message")
        user_msg = Message(role="user", content="test user input")
        original_context = SendMessageWrap(
            train=train_msg,
            memory=[user_msg],
            user_query=user_msg,
        )
        ctx = StrategyContext(
            user_input="test user input",
            original_context=original_context,
            chat_object=chat_obj,
            io_stream=chat_obj.io_stream,
        )
        st = ReActAgentStrategy(ctx)
        st.tools_manager = MagicMock()
        st.tools_manager.tools_meta = MagicMock(return_value={})
        return st

    def test_peer_messages_drained_at_step_boundary(self, strategy):
        """Messages pushed before intro_step appear in the context."""

        stream = strategy.io_stream
        asyncio_run(stream.send_to_producer("human says hi"))
        asyncio_run(stream.send_to_producer({"key": "value"}))

        asyncio_run(strategy.intro_step("execute"))

        msgs = strategy.ctx.message.unwrap(exclude_system=True)
        peer_msgs = [m for m in msgs if "[peer message]" in getattr(m, "content", "")]
        assert len(peer_msgs) == 2
        assert peer_msgs[0].content == "[peer message]\nhuman says hi"
        assert peer_msgs[1].content == "[peer message]\n{'key': 'value'}"

    def test_no_peer_messages_is_noop(self, strategy):
        """Empty reverse stream: intro_step leaves the context untouched."""
        asyncio_run(strategy.intro_step("execute"))
        msgs = strategy.ctx.message.unwrap(exclude_system=True)
        peer_msgs = [m for m in msgs if "[peer message]" in getattr(m, "content", "")]
        assert peer_msgs == []

    def test_peer_messages_after_close_are_dropped(self, strategy):
        """After on_post_process, later peer pushes never reach the context."""
        asyncio_run(strategy.on_post_process())
        asyncio_run(strategy.intro_step("execute"))
        msgs = strategy.ctx.message.unwrap(exclude_system=True)
        peer_msgs = [m for m in msgs if "[peer message]" in getattr(m, "content", "")]
        assert peer_msgs == []


def datetime_now():
    from datetime import datetime, timedelta

    return datetime.now() - timedelta(seconds=1)


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)


# Token budget (real per-run budget injected from config)


class TestTokenBudget:
    def test_exhausted_without_budget(self):
        """No budget configured → never exhausted."""
        budget = TokenBudget()
        budget.update(
            type(
                "U",
                (),
                {"prompt_tokens": 10**9, "completion_tokens": 0, "total_tokens": 0},
            )()
        )
        assert budget.exhausted is False

    def test_exhausted_reaches_budget(self):
        budget = TokenBudget(budget=100)
        budget.update(
            type(
                "U",
                (),
                {"prompt_tokens": 50, "completion_tokens": 0, "total_tokens": 0},
            )()
        )
        assert budget.exhausted is False
        budget.update(
            type(
                "U",
                (),
                {"prompt_tokens": 50, "completion_tokens": 0, "total_tokens": 0},
            )()
        )
        assert budget.exhausted is True

    def test_budget_injected_from_config(self, strategy):
        """_init_run_state injects config.function_config.agent_step_token_budget."""
        strategy.config.function_config.agent_step_token_budget = 200
        rs = strategy._init_run_state()
        assert rs.tokens.budget == 200
        assert rs.tokens.exhausted is False


# Between-Step history compression (real implementation)


class TestBetweenStepCompression:
    @pytest.fixture
    def strategy_with_history(self, strategy):
        """Strategy whose context has a few folded history messages."""
        from amrita_core.types import ToolCall, ToolResult

        wrap = strategy.ctx.message
        # Old history that will be folded: user → assistant(tool_calls) → tool.
        wrap.memory = [
            Message(role="user", content="old turn 1"),
            Message(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(
                        id="t1",
                        function=Function(
                            name="search",
                            arguments='{"q": "old"}',
                        ),
                    )
                ],
            ),
            ToolResult(
                role="tool", name="search", content="old result", tool_call_id="t1"
            ),
            Message(role="user", content="old turn 2"),
        ]
        strategy.config.llm.memory_abstract_threshold = 100
        return strategy

    @staticmethod
    def _bind_ledger(strategy, stream_id="compress-test"):
        """Register a real run ledger and return its proxy for the strategy."""
        from amrita_core.usage import UsageRegistry

        strategy.ctx.usage = UsageRegistry.register(stream_id)
        return strategy.ctx.usage

    def test_noop_below_threshold(self, strategy_with_history):
        """Below the threshold → no LLM call, history untouched."""
        from unittest.mock import patch

        from amrita_core.types import UniResponseUsage

        st = strategy_with_history
        rs = st._init_run_state()
        proxy = self._bind_ledger(st)
        rs.step_started_ts = 1000.0
        proxy.record(
            UniResponseUsage(prompt_tokens=50, completion_tokens=0, total_tokens=50)
        )

        async def fake_generator():
            raise AssertionError("LLM must not be called below threshold")

        with patch(
            "amrita_core.builtins.agent.react_comm.call_completion",
            return_value=fake_generator(),
        ):
            asyncio_run(st._compress_history_between_steps())
        assert len(st.ctx.message.memory) == 4  # untouched
        from amrita_core.usage import UsageRegistry

        UsageRegistry.unregister(st.ctx.usage.stream_id)

    def test_noop_when_threshold_none(self, strategy_with_history):
        """memory_abstract_threshold=None (default) → never compresses."""
        from unittest.mock import patch

        from amrita_core.types import UniResponseUsage

        st = strategy_with_history
        st.config.llm.memory_abstract_threshold = None
        rs = st._init_run_state()
        proxy = self._bind_ledger(st)
        rs.step_started_ts = 1000.0
        proxy.record(
            UniResponseUsage(
                prompt_tokens=10**6, completion_tokens=0, total_tokens=10**6
            )
        )

        async def fake_generator():
            raise AssertionError("LLM must not be called without threshold")

        with patch(
            "amrita_core.builtins.agent.react_comm.call_completion",
            return_value=fake_generator(),
        ):
            asyncio_run(st._compress_history_between_steps())
        assert len(st.ctx.message.memory) == 4
        from amrita_core.usage import UsageRegistry

        UsageRegistry.unregister(st.ctx.usage.stream_id)

    def test_compresses_history_and_resets_baseline(self, strategy_with_history):
        """Above threshold → LLM summary replaces the folded prefix.

        The prompt window is driven by the ledger proxy: the Step's usage is
        recorded via the proxy and ``refresh_window`` picks it up before the
        threshold check.
        """
        from unittest.mock import patch

        from amrita_core.types import UniResponse, UniResponseUsage

        st = strategy_with_history
        rs = st._init_run_state()
        proxy = self._bind_ledger(st)
        rs.step_started_ts = 1000.0
        proxy.record(
            UniResponseUsage(prompt_tokens=150, completion_tokens=0, total_tokens=150)
        )

        async def fake_generator():
            yield UniResponse(
                content="summarized old turns",
                tool_calls=None,
                usage=UniResponseUsage(
                    prompt_tokens=10, completion_tokens=5, total_tokens=15
                ),
            )

        with patch(
            "amrita_core.builtins.agent.react_comm.call_completion",
            return_value=fake_generator(),
        ):
            asyncio_run(st._compress_history_between_steps())
        memory = st.ctx.message.memory
        # user + assistant(tool_calls) + ToolResult folded → summary + tail.
        assert len(memory) == 2
        assert "[Summary of previous steps]" in memory[0].content
        assert memory[1].content == "old turn 2"
        # The summary LLM call usage is recorded by libchat's gateway layer;
        # the baseline prompt window is reset after compression.
        assert rs.tokens.prompt_tokens == 0
        from amrita_core.usage import UsageRegistry

        UsageRegistry.unregister(st.ctx.usage.stream_id)

    def test_budget_survives_baseline_reset(self, strategy_with_history):
        """reset() keeps the configured budget — exhausted stays live."""
        from unittest.mock import patch

        from amrita_core.types import UniResponse, UniResponseUsage

        st = strategy_with_history
        st.config.function_config.agent_step_token_budget = 200
        rs = st._init_run_state()
        proxy = self._bind_ledger(st, "compress-budget")
        rs.step_started_ts = 1000.0
        proxy.record(
            UniResponseUsage(prompt_tokens=150, completion_tokens=0, total_tokens=150)
        )

        async def fake_generator():
            yield UniResponse(
                content="summarized",
                tool_calls=None,
                usage=None,
            )

        with patch(
            "amrita_core.builtins.agent.react_comm.call_completion",
            return_value=fake_generator(),
        ):
            asyncio_run(st._compress_history_between_steps())
        assert rs.tokens.prompt_tokens == 0
        assert rs.tokens.budget == 200  # budget survives the reset
        # The next Step can still hit the budget.
        rs.tokens.prompt_tokens = 200
        assert rs.tokens.exhausted is True
        from amrita_core.usage import UsageRegistry

        UsageRegistry.unregister(st.ctx.usage.stream_id)

    def test_fold_keeps_tool_pairing_intact(self, strategy_with_history):
        """The kept tail must stay well-formed: no dangling tool message."""
        from unittest.mock import patch

        from amrita_core.types import (
            ToolCall,
            ToolResult,
            UniResponse,
            UniResponseUsage,
        )

        st = strategy_with_history
        wrap = st.ctx.message
        # Tail: assistant(tool_calls) + its ToolResult (must be kept together).
        wrap.memory = [
            Message(role="user", content="old turn"),
            Message(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(
                        id="t2",
                        function=Function(name="read", arguments="{}"),
                    )
                ],
            ),
            ToolResult(
                role="tool", name="read", content="kept result", tool_call_id="t2"
            ),
        ]
        rs = st._init_run_state()
        proxy = self._bind_ledger(st, "compress-pair")
        rs.step_started_ts = 1000.0
        proxy.record(
            UniResponseUsage(prompt_tokens=200, completion_tokens=0, total_tokens=200)
        )

        async def fake_generator():
            yield UniResponse(
                content="folded the old turn",
                tool_calls=None,
                usage=None,
            )

        with patch(
            "amrita_core.builtins.agent.react_comm.call_completion",
            return_value=fake_generator(),
        ):
            asyncio_run(st._compress_history_between_steps())
        memory = st.ctx.message.memory
        # Summary + assistant(tool_calls) + ToolResult — pairing preserved.
        assert len(memory) == 3
        assert memory[0].role == "user"
        assert memory[1].tool_calls is not None
        assert memory[2].role == "tool"
        from amrita_core.usage import UsageRegistry

        UsageRegistry.unregister(st.ctx.usage.stream_id)

    def test_empty_summary_keeps_history(self, strategy_with_history):
        """LLM returns empty → history untouched, baseline reset (no retry loop)."""
        from unittest.mock import patch

        from amrita_core.types import UniResponse

        st = strategy_with_history
        rs = st._init_run_state()
        rs.tokens.prompt_tokens = 150

        async def fake_generator():
            yield UniResponse(content="", tool_calls=None, usage=None)

        with patch(
            "amrita_core.builtins.agent.react_comm.call_completion",
            return_value=fake_generator(),
        ):
            asyncio_run(st._compress_history_between_steps())
        assert len(st.ctx.message.memory) == 4  # kept
        assert rs.tokens.prompt_tokens == 0  # baseline reset
