from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, Literal

from amrita_sense.logging import logger
from typing_extensions import override

from amrita_core.builtins.agent.events import (
    StepAbortError,
    StepIntroEvent,
    StepIterationEvent,
    StepLeaveEvent,
)
from amrita_core.builtins.agent.state import StepSummary
from amrita_core.builtins.types import (
    AgentStepCompressMetadata,
    AgentStepIntroMetadata,
    AgentStepLeaveMetadata,
    AgentStepStallMetadata,
)
from amrita_core.components.compaction import ContextCompactor
from amrita_core.tools.models import ToolFunctionSchema
from amrita_core.types import (
    Function,
    Message,
    SendMessageWrap,
    ToolCall,
    ToolResult,
    UniResponse,
)
from amrita_core.types.tool import TOOL_RESULT_CONTENT, content_text

if TYPE_CHECKING:
    from amrita_core.builtins.agent.state import Phase

from ..tools import REASONING_TOOL
from .react_base import BaseReActAgentStrategy


def _resolve_tool_name(tool: ToolFunctionSchema | dict) -> str:
    """Resolve the function name from a tool schema (object or dict form)."""
    if isinstance(tool, dict):
        return tool.get("function", {}).get("name", "")
    return tool.function.name


class ReActAgentStrategy(BaseReActAgentStrategy):
    """ReAct Agent Strategy for dynamic tool execution and reasoning.

    This strategy implements the standard ReAct (Reasoning + Acting) pattern,
    combining iterative reasoning with external tool execution to solve complex tasks.
    It supports both RAG (Retrieval-Augmented Generation) and general agent workflows
    within a unified 'agent-mixed' execution framework.

    Core Capabilities:
    - **Dynamic Tool Calling**: Automatically selects and executes appropriate tools
      based on context and task requirements through structured ToolCall-ToolResult
      message pairs.
    - **Iterative Reasoning**: Supports multi-step reasoning cycles where the agent
      can analyze intermediate results, adjust strategies, and continue execution
      until task completion or maximum iteration limit.
    - **Reasoning Mode Integration**: Integrates with configurable reasoning modes
      ('reasoning', 'reasoning-required') to enable explicit thought process tracking
      before tool execution, improving transparency and controllability.
    - **Loop Detection & Recovery**: Implements automatic detection of reasoning loops
      (excessive duplicate reasoning calls) and provides recovery mechanisms by
      injecting guidance messages to break infinite cycles.
    - **Structured Message Flow**: Maintains strict adherence to OpenAI-compatible
      message formats with proper ToolCall-ToolResult pairing, ensuring compatibility
      with standard LLM providers.
    """

    @override
    async def _append_reasoning(
        self,
        tool_call: ToolCall,
        reasoning_content: UniResponse[str, None],
    ):
        """ReAct strategy specific reasoning handler with ToolCall-ToolResult pairing.

        The reasoning text is stored in ``Message.reasoning_content`` (never in
        ``content`` or ``ToolResult.content``) so that:

        - ``_apply_thinking_filter`` (``content_mode="never"``) can strip it;
        - ``content_mode="by-tool"`` validation no longer fails;
        - the Anthropic adapter can round-trip it into a ``thinking`` block.

        The paired ``ToolResult`` only carries a placeholder to satisfy the
        OpenAI ToolCall-ToolResult pairing requirement.
        """
        self.reasoning_pc += 1
        reasoning = (
            reasoning_content.content or reasoning_content.reasoning_content or ""
        )
        msg: SendMessageWrap = self.ctx.get_original_context()

        msg.append(
            Message(
                role="assistant",
                content=None,
                tool_calls=[tool_call],
                reasoning_content=reasoning,
            )
        )
        msg.append(
            ToolResult(
                role="tool",
                name=tool_call.function.name,
                content="<REASONING_COMPLETED>",
                tool_call_id=tool_call.id,
            )
        )

    # Step lifecycle implementation (native step loop): decomposition, stall give-up, per-Step summary, between-Step token-driven compression.

    async def _decide_decomposition(self) -> None:
        """Analyze phase: ask the model whether to decompose into a DAG.

        The call, its degradation path and the emitted metadata live in
        ``step_nodes.decide_decomposition``; the workflow runs the same
        function through the ``STEP_DECOMPOSE`` node.
        """
        from amrita_core.components import step_nodes

        await step_nodes.decide_decomposition(self)

    def _record_tool_signature(self, tool_call: ToolCall) -> None:
        """Record a tool-call signature in the current Step (stall detection)."""
        rs = self._init_run_state()
        try:
            sig = f"{tool_call.function.name}({hash(tool_call.function.arguments)})"
        except Exception:
            sig = tool_call.function.name
        rs.record_tool_call(sig)

    def _inject_plan_status(self) -> None:
        """Inject the current plan snapshot (plan mode only, idempotent).

        Shared with the ``STEP_PLAN_STATUS`` node: both suppress a snapshot
        identical to the previous one, so the graph path and a direct caller
        cannot double-inject.
        """
        from amrita_core.components import step_nodes

        step_nodes.inject_plan_status(self)

    def _detect_step_stall(self) -> bool:
        """True when the last N tool signatures within this Step are identical."""
        rs = self._init_run_state()
        trigger = self.config.builtin.loop_reasoning_trigger
        return rs.is_stalled(trigger)

    @override
    def _should_cancel_tool_call(self, tool_call: ToolCall) -> bool:
        """Cancel the call when it trips the stall detector.

        Called by ``_exec_one`` *after* the signature was recorded, so
        ``is_stalled`` already includes this call: when the repeating window
        has formed (this call is the ``threshold``-th identical one), the
        tool is NOT executed — the caller returns a ``"Cancelled: ..."``
        result so the model learns the call was rejected instead of looping
        on a normal result.  The give-up user message is still injected
        afterwards by ``after_iteration`` (retained as the context-level
        signal).
        """
        rs = self._init_run_state()
        if rs.stall_injected or rs.exec_finished:
            return True
        trigger = self.config.builtin.loop_reasoning_trigger
        return rs.is_stalled(trigger)

    @override
    async def after_iteration(self) -> None:
        """Per-iteration stall check (runs inside the execute loop).

        Called by ``STEP_EXEC`` after every successful tool round.  If the
        tool-call signatures within this Step are stuck in a loop, inject the
        give-up prompt and set ``stall_injected`` / ``exec_finished`` so that
        ``iter_cond`` terminates the iteration loop immediately — without
        burning more tokens on repeated tool calls.
        """
        rs = self._init_run_state()
        if rs.stall_injected or rs.exec_finished:
            return
        # Lifecycle hook: matchers may end the Step early (end_step=True) or raise StepAbortError to force-terminate the iteration loop.
        ev = StepIterationEvent.constructor(rs)
        try:
            await self._trigger_step_event(ev, exception_ignored=(StepAbortError,))
        except StepAbortError:
            logger.info("Step iteration aborted by lifecycle matcher.")
            rs.exec_finished = True
            rs.stall_injected = True
            return
        if ev.end_step:
            rs.exec_finished = True
            return
        if self._detect_step_stall():
            await self._inject_give_up_prompt()

    async def _inject_give_up_prompt(self) -> None:
        """Inject a user-role "give up" prompt *inside* the current Step.

        Called once per Step; after injection the workflow condition
        ``iter_cond`` returns False so the Step ends immediately.
        """
        rs = self._init_run_state()
        if rs.stall_injected:
            return
        self.ctx.message.append(
            Message(
                role="user",
                content=(
                    "<BEGIN_OF_EXTRA>\n\n"
                    "You have been calling the same tool repeatedly without "
                    "making progress — the task is now ABANDONED.\n\n"
                    "ANSWER DIRECTLY:\n"
                    "- Use ONLY the information you have already gathered in "
                    "this conversation.\n"
                    "- Any additional tool call is ILLEGAL and will be "
                    "rejected. Do NOT output tool-call syntax.\n"
                    "- Write your final answer to the user as plain text now, "
                    "and state clearly what you could and could not "
                    "accomplish.\n"
                    "(Give up when there are no solutions.)\n\n"
                    "<END_OF_EXTRA>\n"
                ),
            )
        )
        rs.stall_injected = True
        # Giving up on this Step means the whole task is abandoned: end the task loop (task_cond checks exec_finished / stall_injected).
        rs.exec_finished = True
        logger.warning("Stall detected — injected give-up prompt inside Step.")
        # Push the stall-recovery metadata.
        await self._emit_step_event(
            content=(
                "[step] stall detected: repeated tool calls "
                f"{rs.step_tool_signatures[-3:]}; injected give-up prompt."
            ),
            metadata=AgentStepStallMetadata(
                type="step",
                extra_type="stall",
                signatures=rs.step_tool_signatures[-3:],
                injected=True,
            ),
        )

    async def _summarize_step(self) -> None:
        """Leave-step: short subject-predicate summary, degrading on failure.

        The graph runs ``Try(STEP_SUMMARY).CATCH(Exception, STEP_SUMMARY_FALLBACK)``;
        a direct caller gets the same fallback here.
        """
        from amrita_core.components import step_nodes

        try:
            await step_nodes.summarize_step(self)
        except Exception as e:
            logger.warning(f"Step summary failed, falling back: {e!s}")
            step_nodes.apply_summary_fallback(self)

    async def _compress_history_between_steps(self) -> None:
        """Between-Step history management when the real API prompt-token
        usage exceeds the configured threshold.

        The threshold comes from the preset's attention window, the same source
        the between-turn handling uses, so one number describes one model.
        The pairing is closed at Step boundaries, so dropping the oldest part
        of the history is safe here: the cut lands on a ``user`` message,
        keeping every assistant tool call next to its tool results.

        Dispatches on ``context_strategy``. ``compact`` replaces the prefix
        with one summary message; ``slide`` drops it outright. The token
        baseline is reset either way.
        """
        rs = self._init_run_state()
        compactor = ContextCompactor(
            config=self.config,
            preset=self.preset,
            usage=self.usage,
        )
        if not compactor.enabled:
            return
        # Refresh the current Step's prompt window before threshold checks.
        rs.tokens.refresh_window(self.usage, rs.step_started_ts)
        if rs.tokens.prompt_tokens <= compactor.threshold:
            return
        trigger_tokens = rs.tokens.prompt_tokens
        msg_wrap = self.ctx.message

        if compactor.strategy == "slide":
            dropped = compactor.slide(msg_wrap.memory, trigger_tokens)
            if dropped <= 0:
                rs.tokens.reset()
                rs.step_started_ts = time.time()
                return
            logger.info(
                f"Prompt tokens {trigger_tokens} > threshold "
                f"{compactor.threshold}; slid {dropped} messages out between Steps."
            )
            rs.tokens.reset()
            rs.step_started_ts = time.time()
            await self._emit_step_event(
                content=(
                    "[step] slide: prompt tokens "
                    f"{trigger_tokens} > threshold {compactor.threshold}; "
                    f"dropped the {dropped} oldest messages."
                ),
                metadata=AgentStepCompressMetadata(
                    type="step",
                    extra_type="compress",
                    prompt_tokens=trigger_tokens,
                    threshold=compactor.threshold,
                ),
            )
            return

        logger.info(
            f"Prompt tokens {trigger_tokens} > threshold "
            f"{compactor.threshold}; compressing history between Steps."
        )
        try:
            result = await compactor.fold(msg_wrap.memory)
        except Exception as e:
            logger.warning(f"History compression failed, keeping history: {e!s}")
            result = None
        if result is None:
            rs.tokens.reset()
            rs.step_started_ts = time.time()
            return
        # Replace the folded history with a single summary message.
        msg_wrap.memory = [
            Message(
                role="user",
                content=f"[Summary of previous steps]\n{result.summary}",
            ),
            *result.messages,
        ]
        # Push the compression metadata.
        await self._emit_step_event(
            content=(
                "[step] compress: prompt tokens "
                f"{trigger_tokens} > threshold {compactor.threshold}; "
                "history between Steps summarized."
            ),
            metadata=AgentStepCompressMetadata(
                type="step",
                extra_type="compress",
                prompt_tokens=trigger_tokens,
                threshold=compactor.threshold,
            ),
        )
        rs.tokens.reset()  # reset baseline after compression

    @override
    async def intro_step(self, phase: "Phase" = "execute") -> None:
        """Enter a Step boundary — driven by the plan's topological order.

        In plan mode (decomposed task) the next ready DAG node is picked via
        ``next_ready_node()`` and becomes the current Step.  In simple mode
        (bare run) a single implicit ``"execute"`` Step is used.

        Pending peer messages are drained first so the incoming Step sees
        them as the latest context (see ``_drain_peer_input``).
        """
        # The native step loop always enters through intro_step - expose the plan-revision built-in exactly here (idempotent).
        self._ensure_step_tools()
        await self._drain_peer_input()
        rs = self._init_run_state()
        # On the graph path NEEDS_DECOMPOSITION and the STEP_BEGIN_* branches
        # already ran; both helpers are no-ops when the state says so.
        from amrita_core.components import step_nodes

        await step_nodes.maybe_decompose(self)
        step_nodes.begin_step_for_current_state(self)
        # Refresh the Step's prompt-token window from the ledger proxy.
        rs.tokens.refresh_window(self.usage, rs.step_started_ts)
        # Keep the model aware of the current plan (idempotent snapshot) so it can autonomously revise the plan via update_step mid-run.
        self._inject_plan_status()

        # Lifecycle hook: matchers may redirect the phase name (override_phase) before the Step starts.
        intro_ev = StepIntroEvent.constructor(rs)
        await self._trigger_step_event(intro_ev)
        if intro_ev.override_phase and rs.current_phase != intro_ev.override_phase:
            rs.current_phase = intro_ev.override_phase
            logger.info(
                f"Step #{rs.step_index} phase overridden by matcher: "
                f"-> {intro_ev.override_phase}"
            )

        # Push the step-intro metadata. Resolve the current node description (plan mode only).
        node_desc: str | None = None
        if rs.plan and rs.current_step_id:
            for node in rs.plan:
                if node.id == rs.current_step_id:
                    node_desc = node.description
                    break
        await self._emit_step_event(
            content=(
                f"[step] enter {rs.current_phase or ''} #{rs.step_index}"
                + (
                    f" ({rs.current_step_id}: {node_desc})"
                    if rs.current_step_id and node_desc
                    else f" ({rs.current_step_id})"
                    if rs.current_step_id
                    else ""
                )
            ),
            metadata=AgentStepIntroMetadata(
                type="step",
                extra_type="intro",
                phase=rs.current_phase,
                step_index=rs.step_index,
                simple_mode=rs.simple_mode,
                current_step_id=rs.current_step_id,
                description=node_desc,
            ),
        )

    @override
    async def leave_step(self, phase: "Phase | None" = None) -> None:
        """Leave a Step boundary: summarize, mark the node done, compress.

        - stall detection (inject give-up prompt) + subject-predicate summary;
        - completes the current DAG node (``complete_current_node``);
        - between-Step token accounting + history compression.
        """
        rs = self._init_run_state()
        # Stall detection is also done per-iteration inside the loop; here it is the idempotent fallback when the loop exits without stalling.
        if self._detect_step_stall() and not rs.stall_injected:
            await self._inject_give_up_prompt()
        # Subject-predicate summary of what this Step accomplished.
        await self._summarize_step()
        # Mark the DAG node done (no-op in simple mode).
        rs.complete_current_node()

        # Lifecycle hook: matchers may override the summary produced above (override_verb / override_object).
        leave_ev = StepLeaveEvent.constructor(rs)
        await self._trigger_step_event(leave_ev)
        if leave_ev.override_verb or leave_ev.override_object:
            rs.last_summary = StepSummary(
                verb=leave_ev.override_verb
                or (rs.last_summary.verb if rs.last_summary else "Completed"),
                object=leave_ev.override_object
                or (rs.last_summary.object if rs.last_summary else ""),
            )
            logger.info(
                f"Step #{rs.step_index} summary overridden by matcher: "
                f"{rs.last_summary.verb} {rs.last_summary.object}"
            )
        # Push the step-leave metadata.
        await self._emit_step_event(
            content=(
                f"[step] leave {rs.current_phase or ''} #{rs.step_index}: "
                + (
                    f"{rs.last_summary.verb} {rs.last_summary.object}"
                    if rs.last_summary is not None
                    else "(boundary only)"
                )
            ),
            metadata=AgentStepLeaveMetadata(
                type="step",
                extra_type="leave",
                phase=rs.current_phase,
                step_index=rs.step_index,
                stall_injected=rs.stall_injected,
                summary_verb=(
                    rs.last_summary.verb if rs.last_summary is not None else None
                ),
                summary_object=(
                    rs.last_summary.object if rs.last_summary is not None else None
                ),
            ),
        )
        # Compression happens between Steps (pairing closed here); the auxiliary call usage is accounted via the ledger proxy.
        await self._compress_history_between_steps()

    @override
    def _maybe_inject_tool_failure_hint(
        self, tool_call: ToolCall, func_response: TOOL_RESULT_CONTENT
    ) -> None:
        """Append a one-shot failure -> revise hint after a hard ERROR result.

        Runs right after the ToolResult was appended, so the tool-call/result
        pairing stays intact (a ``user`` message after a closed pair never
        splits it).  Only fires when the result starts with ``ERROR`` (an
        objective tool failure) and only for regular tools — built-in
        flow-control tools (STOP/REASONING) never reach this point.

        First failure: retry at most once, then revise via ``update_step``.
        Any further failure in the same Step: stop retrying, revise now.
        Parallel tool calling is left untouched — this only appends a context
        message, it never disables or alters concurrent execution.
        """
        # Error detection reads the text view; image blocks must not look like an ERR prefix.
        if not content_text(func_response).startswith("ERROR"):
            return
        rs = self._init_run_state()
        rs.tool_error_hints += 1
        if rs.tool_error_hints == 1:
            note = (
                "\n[Framework note] The tool returned a hard error. "
                "Retry it at most once. If it fails again, call update_step "
                "(action: remove_step or replan) to drop the broken step, "
                "then answer with the information you already have. "
                "Do not keep retrying a failing tool."
            )
        else:
            note = (
                "\n[Framework note] The tool failed again. Do not retry it. "
                "Call update_step now (action: remove_step or replan) to "
                "revise the plan, then answer with what you have."
            )
        self.ctx.message.append(Message(role="user", content=note))
        logger.debug(
            "Tool failure hint injected (count=%s) after ERROR result from %s.",
            rs.tool_error_hints,
            tool_call.function.name,
        )

    @override
    async def _build_stop_response_and_append(
        self,
        function_args: dict[str, Any],
        response_msg: UniResponse[str | None, list[ToolCall] | None],
        function_name: str,
        function_call_id: str,
        function_response: str,
    ):
        """ReAct strategy: append assistant message with only this STOP tool_call before its ToolResult.

        Only a single ToolCall is included in the assistant message to avoid the
        "insufficient tool messages following tool_calls message" API error.

        The fabricated assistant message mirrors the provider's response
        verbatim: every field (``reasoning_content``, ``reasoning_signature``
        and any extra — ``Message`` allows extra) is carried over as-is via
        :meth:`_assistant_fields_from_response`, never hard-coded.
        """
        self.ctx.message.append(
            Message(
                role="assistant",
                content=response_msg.content if response_msg else None,
                tool_calls=[
                    ToolCall(
                        id=function_call_id,
                        function=Function(
                            name=function_name,
                            arguments=json.dumps(function_args),
                        ),
                    )
                ],
                **self._assistant_fields_from_response(response_msg),
            )
        )
        self.ctx.message.append(
            ToolResult(
                role="tool",
                tool_call_id=function_call_id,
                name=function_name,
                content=function_response,
            )
        )

    @override
    async def _handle_error_append(
        self,
        tool_call: ToolCall,
        error_content: str,
        original_exception: BaseException | None = None,
        response_msg: UniResponse[str | None, list[ToolCall] | None] | None = None,
    ):
        """ReAct strategy: append error as an assistant+tool message pair.

        The fabricated assistant message mirrors the provider's response
        verbatim: the original ``tool_call`` plus every field (``reasoning_content``,
        ``reasoning_signature`` and any extra — ``Message`` allows extra)
        carried over as-is via :meth:`_assistant_fields_from_response`, never
        hard-coded — the failure is marked only by the ``ERR:``-prefixed
        ``ToolResult`` content.

        Args:
            tool_call: The failed tool call, kept verbatim for the round-trip.
            error_content: Formatted error message to append.
            original_exception: The original exception, or ``None`` when the
                error was captured as a string during concurrent execution.
            response_msg: The provider response whose assistant-message fields
                are carried back verbatim, or ``None``.
        """
        self.ctx.message.append(
            Message(
                role="assistant",
                content=response_msg.content if response_msg else None,
                tool_calls=[tool_call],
                **self._assistant_fields_from_response(response_msg),
            )
        )
        self.ctx.message.append(
            ToolResult(
                role="tool",
                name=tool_call.function.name,
                content=error_content,
                tool_call_id=tool_call.id,
            )
        )

    @override
    async def single_execute(
        self,
    ) -> bool:
        config = self.config
        msg_list: SendMessageWrap = self.ctx.message
        if not self.tools:
            return False
        if config.builtin.tool_calling_mode == "rag" and self.call_count > 1:
            return False

        logger.info(
            "Starting tool round; completed tool-call batches so far: "
            f"{self.call_count - 1}, current message count: {len(msg_list)}"
        )
        if (
            config.builtin.tool_calling_mode == "agent"
            and not self._is_native_thinking_enabled()
            and (
                (
                    self.call_count == 1
                    and config.builtin.agent_thought_mode == "reasoning"
                )
                or config.builtin.agent_thought_mode == "reasoning-required"
            )
        ):
            await self._generate_reasoning_msg(
                self.tools, ReActAgentStrategy._append_reasoning
            )
        elif config.builtin.tool_calling_mode == "none":
            return False
        tools = self.tools.copy()
        if config.builtin.agent_thought_mode.startswith("reasoning"):
            tools.append(REASONING_TOOL)

        if (
            self._predicted_tools
            and hasattr(config.builtin, "react_config")
            and config.builtin.react_config is not None
            and config.builtin.react_config.reasoning_aware_tools
        ):
            prioritized = [
                t for t in tools if _resolve_tool_name(t) in self._predicted_tools
            ]
            others = [
                t for t in tools if _resolve_tool_name(t) not in self._predicted_tools
            ]
            tools = prioritized + others
            logger.debug(
                f"Reasoning-aware tools:"
                f" {[_resolve_tool_name(t) for t in prioritized]}"
                f" ahead of {len(others)} others"
            )

        response_msg: UniResponse[
            str | None, list[ToolCall] | None
        ] = await self._model_round(
            msg_list.unwrap(),
            tools,
            self._resolve_tool_choice(
                "required"
                if (config.llm.require_tools and not self._suggested_stop)
                else "auto"
            ),
        )

        # Use template method for common execution flow
        return await self._execute_tool_loop(
            response_msg,
        )

    @classmethod
    def get_category(cls) -> Literal["agent-mixed"]:
        """
        Get the category of the agent strategy.

        Returns:
            The strategy category as a literal string indicating execution pattern.
        """
        return "agent-mixed"


AmritaAgentStrategy = ReActAgentStrategy  # Alias for backward compatibility

__all__ = [
    "AmritaAgentStrategy",
    "ReActAgentStrategy",
]
