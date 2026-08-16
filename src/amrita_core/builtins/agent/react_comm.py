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
from amrita_core.builtins.agent.state import DecomposeDecision, StepSummary
from amrita_core.builtins.types import (
    AgentStepCompressMetadata,
    AgentStepDecomposeMetadata,
    AgentStepIntroMetadata,
    AgentStepLeaveMetadata,
    AgentStepStallMetadata,
)
from amrita_core.consts import ABSTRACT_INSTRUCTION
from amrita_core.libchat import (
    call_completion,
    get_last_response,
    text_generator,
    tools_caller,
)
from amrita_core.tools.models import ToolFunctionSchema
from amrita_core.types import (
    Function,
    Message,
    SendMessageWrap,
    ToolCall,
    ToolResult,
    UniResponse,
)

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

    # Step lifecycle implementation (native step loop): decomposition,
    # stall give-up, per-Step summary, between-Step token-driven compression.

    async def _decide_decomposition(self) -> None:
        """Analyze phase: ask the LLM whether to decompose the task into a DAG.

        Simple QA / simple tasks run directly (``simple_mode=True``) without
        decomposition.  Complex tasks produce a DAG (semantic layer only — the
        workflow itself stays linear).
        """
        rs = self._init_run_state()
        prompt: list = [
            Message(
                role="system",
                content=(
                    "# Task Decomposition Decision\n"
                    "Decide whether this task needs multi-step execution.\n"
                    "\n"
                    "## Use SIMPLE mode (needs_decomposition=false) when:\n"
                    "SIMPLE mode is still ReAct — the normal tool loop runs;\n"
                    "it just is not step-driven (no DAG decomposition).\n"
                    "Most requests, including routine questions and simple\n"
                    "tasks, belong here.\n"
                    "- Chitchat, greetings, or casual conversation\n"
                    "- A direct question answerable from the conversation context\n"
                    "- A single tool call suffices (lookup, calculation, format conversion)\n"
                    "- Summarizing or rephrasing content already available\n"
                    "- The user asks for a direct answer without further work\n"
                    "\n"
                    "## Use STEP mode (needs_decomposition=true, DAG) ONLY when:\n"
                    "- Multiple dependent steps are required\n"
                    "- Information must be gathered first, then used to produce the result\n"
                    "- Research or multi-source synthesis\n"
                    "\n"
                    "## Rules\n"
                    "- NEVER create a single-node DAG; if one step covers the task, use simple mode.\n"
                    '- DAG node ids are short semantic names ("search-web", "read-docs", "write-summary"), never step-1/step-2.\n'
                    'Output strictly as JSON: {"needs_decomposition": bool, "dag": [...], "reason": "..."}\n'
                    "\n"
                    "## Examples\n"
                    "Example 1 (simple):\n"
                    "User: What is 2+2?\n"
                    'Output: {"needs_decomposition": false, "dag": [], "reason": "Simple arithmetic; answer directly."}\n'
                    "\n"
                    "Example 2 (complex):\n"
                    "User: Summarize the repo docs: first list all doc files, then read each one, then write a summary.\n"
                    'Output: {"needs_decomposition": true, '
                    '"dag": [{"id": "list-files", "description": "List all doc files", "depends_on": []}, '
                    '{"id": "read-docs", "description": "Read each doc file", "depends_on": ["list-files"]}, '
                    '{"id": "write-summary", "description": "Write the summary", "depends_on": ["read-docs"]}], '
                    '"reason": "Reading depends on listing; writing depends on reading."}'
                ),
            ),
            *self.ctx.message.unwrap(exclude_system=True),
            Message(
                role="user",
                content=(
                    "Now decide whether the above task needs decomposition. "
                    "Output ONLY the JSON object, nothing else: "
                    '{"needs_decomposition": bool, "dag": [...], "reason": "..."}'
                ),
            ),
        ]
        try:
            resp = await get_last_response(
                call_completion(
                    prompt, preset=self.preset, config=self.config, usage=self.usage
                )
            )
            # Empty response (some providers return '' when thinking is
            # engaged) — degrade immediately instead of parsing garbage.
            if not (resp.content or "").strip():
                req_id = getattr(resp.metadata, "original_request_id", None)
                logger.warning(
                    f"Empty decomposition response (request_id={req_id}, "
                    f"thinking_content={bool(resp.reasoning_content)}); "
                    "fallback: Sorry, no response was returned"
                )
                raise ValueError("empty decomposition response")
            decision = DecomposeDecision.model_validate_json(resp.content)
        except Exception as e:
            logger.warning(f"Decomposition decision failed, running directly: {e!s}")
            decision = DecomposeDecision(needs_decomposition=False)

        rs.simple_mode = not decision.needs_decomposition
        rs.plan = decision.dag if decision.needs_decomposition else None
        logger.debug(
            f"Decompose decision: simple_mode={rs.simple_mode}, "
            f"plan={[n.id for n in (rs.plan or [])]}"
        )
        # Push the decomposition decision metadata.
        dag_ids = [n.id for n in (rs.plan or [])]
        dag_desc = {n.id: n.description for n in (rs.plan or [])}
        dag_desc_str = (
            ", ".join(f"{n.id} ({n.description})" for n in (rs.plan or []))
            if rs.plan
            else ""
        )
        await self._emit_step_event(
            content=(
                "[step] decompose: "
                + (
                    "simple mode (no DAG)"
                    if rs.simple_mode
                    else f"DAG [{dag_desc_str}]"
                )
                + f" — {decision.reason}"
            ),
            metadata=AgentStepDecomposeMetadata(
                type="step",
                extra_type="decompose",
                needs_decomposition=decision.needs_decomposition,
                simple_mode=rs.simple_mode,
                dag=dag_ids,
                descriptions=dag_desc,
                reason=decision.reason,
            ),
        )

    def _record_tool_signature(self, tool_call: ToolCall) -> None:
        """Record a tool-call signature in the current Step (stall detection)."""
        rs = self._init_run_state()
        try:
            sig = f"{tool_call.function.name}({hash(tool_call.function.arguments)})"
        except Exception:
            sig = tool_call.function.name
        rs.record_tool_call(sig)

    def _inject_plan_status(self) -> None:
        """Inject the current plan snapshot into the context (plan mode only).

        Called at every Step intro so the model always sees the *current*
        plan — including revisions made by ``update_step`` mid-run.  The
        snapshot is appended only when it changed (plain text, no DSML
        tags), keeping the context lean and pairing intact: a ``user``
        message at a Step boundary never splits a tool-call/result pair.

        The note tells the model the plan is only a hint: revise it ONLY
        when the plan turns out to be wrong (a step is redundant, missing,
        or the task changed) — not for its own sake.  Normal step progress
        is handled automatically by the framework (``leave_step`` marks the
        node done), so ``mark_done`` is never needed from the model side.
        """
        rs = self._init_run_state()
        if rs.simple_mode or not rs.plan:
            return
        done = set(rs.completed_step_ids)
        lines = []
        for node in rs.plan:
            state = "done" if node.id in done else "pending"
            if node.id == rs.current_step_id:
                state = "current"
            lines.append(f"- {node.id} [{state}]: {node.description}")
        snapshot = "[Plan status]\n" + "\n".join(lines)
        if snapshot == self._last_plan_snapshot:
            return
        self._last_plan_snapshot = snapshot
        note = (
            "\nThis plan is only a hint for structuring your work. "
            "The framework advances it automatically as you complete steps. "
            "Call update_step ONLY when the plan turns out to be wrong: a "
            "step is redundant, missing, the task changed, or a step cannot "
            "be completed because its tool keeps failing (persistent ERROR "
            "results). Never revise for its own sake. When a tool fails, "
            "retry at most once; if it keeps failing, revise the plan "
            "(remove_step the broken step or replan) and answer with what "
            "you have. Use remove_step / add_step / replan to fix it; do "
            "NOT use mark_done (the framework marks steps done for you)."
        )
        self.ctx.message.append(Message(role="user", content=snapshot + note))
        logger.debug(f"Plan status injected into context ({len(lines)} nodes).")

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
        # Lifecycle hook: matchers may end the Step early (end_step=True) or
        # raise StepAbortError to force-terminate the iteration loop.
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
        # Giving up on this Step means the whole task is abandoned:
        # end the task loop (task_cond checks exec_finished / stall_injected).
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
        """Leave-step: ask the LLM for a short subject-predicate phrase.

        The phrase is split into ``verb`` (past tense) + ``object`` (noun
        phrase), e.g. ``Reviewed`` + ``codebase``.  Stored in
        ``run_state.last_summary`` and feeds the next Step's ``<last_step>``.
        """

        rs = self._init_run_state()
        prompt: list = [
            Message(
                role="system",
                content=(
                    "# Step Summary\n"
                    "Summarize what was accomplished in this step using a short "
                    "subject-predicate phrase: a verb (past tense) + an object phrase. "
                    'Output strictly as JSON: {"verb": "...", "object": "..."}\n'
                    "\n"
                    "## Examples\n"
                    "Example 1 (research step):\n"
                    "Step: the assistant searched the web for the latest version, "
                    "then read the changelog page, then answered with the version number.\n"
                    'Output: {"verb": "Retrieved", "object": "latest version number"}\n'
                    "\n"
                    "Example 2 (computation step):\n"
                    "Step: the assistant called the calculator tool with 2+2 and got 4.\n"
                    'Output: {"verb": "Calculated", "object": "2+2 result"}'
                ),
            ),
            *self.ctx.message.unwrap(exclude_system=True),
            Message(
                role="user",
                content=(
                    "Now summarize the step above. "
                    'Output ONLY the JSON object, nothing else: {"verb": "...", "object": "..."}'
                ),
            ),
        ]
        try:
            resp = await get_last_response(
                call_completion(
                    prompt, preset=self.preset, config=self.config, usage=self.usage
                )
            )
            # Empty response (some providers return '' when thinking is
            # engaged) — degrade immediately instead of parsing garbage.
            if not (resp.content or "").strip():
                req_id = getattr(resp.metadata, "original_request_id", None)
                logger.warning(
                    f"Empty summary response (request_id={req_id}, "
                    f"thinking_content={bool(resp.reasoning_content)}); "
                    "fallback: Sorry, no response was returned"
                )
                raise ValueError("empty summary response")
            rs.last_summary = StepSummary.model_validate_json(resp.content)
        except Exception as e:
            logger.warning(f"Step summary failed, falling back: {e!s}")
            rs.last_summary = StepSummary(
                verb="Completed", object=rs.current_phase or ""
            )

    async def _compress_history_between_steps(self) -> None:
        """Between-Step compression: summarize completed-Step history when
        the real API prompt-token usage exceeds the configured threshold.

        The pairing is closed at Step boundaries, so folding the oldest
        ``memory`` prefix into one summary message is safe here: assistant
        messages with ``tool_calls`` are folded together with their
        consecutive ``ToolResult`` messages, keeping the remaining context
        well-formed.  The token baseline is reset after compression.
        """
        rs = self._init_run_state()
        # Refresh the current Step's prompt window before threshold checks.
        rs.tokens.refresh_window(self.usage, rs.step_started_ts)
        threshold = self.config.llm.memory_abstract_threshold
        if threshold <= 0 or rs.tokens.prompt_tokens <= threshold:
            return
        logger.info(
            f"Prompt tokens {rs.tokens.prompt_tokens} > threshold {threshold}; "
            "compressing history between Steps."
        )
        trigger_tokens = rs.tokens.prompt_tokens
        msg_wrap = self.ctx.message
        history = msg_wrap.memory
        # Fold the oldest proportion of the history, keeping recent context.
        proportion = self.config.llm.memory_abstract_proportion
        index = int(len(history) * proportion)
        if index <= 0:
            rs.tokens.reset()
            rs.step_started_ts = time.time()
            return
        # Walk the boundary forward past tool pairs so the kept context is
        # well-formed (every assistant(tool_calls) keeps its ToolResults).
        idx = 0
        while idx < index and idx < len(history):
            element = history[idx]
            if getattr(element, "tool_calls", None) is not None:
                next_idx = idx + 1
                while (
                    next_idx < len(history)
                    and getattr(history[next_idx], "role", None) == "tool"
                ):
                    next_idx += 1
                idx = next_idx
            else:
                idx += 1
        if idx <= 0:
            rs.tokens.reset()
            rs.step_started_ts = time.time()
            return
        dropped = history[:idx]
        kept = history[idx:]
        # Ask the LLM for a summary of the folded messages.
        prompt: list = [
            Message(role="system", content=ABSTRACT_INSTRUCTION),
            Message(
                role="user",
                content=(
                    "Make a summary of full informations in message list:"
                    + "\n\n```text\n"
                    + "".join(
                        f"{it}\n" for it in text_generator(dropped, split_role=True)
                    )
                    + "\n```"
                ),
            ),
        ]
        try:
            resp = await get_last_response(
                call_completion(
                    prompt, preset=self.preset, config=self.config, usage=self.usage
                )
            )
            summary = (resp.content or "").strip()
            if not summary:
                raise ValueError("empty compression response")
        except Exception as e:
            logger.warning(f"History compression failed, keeping history: {e!s}")
            rs.tokens.reset()
            rs.step_started_ts = time.time()
            return
        # Replace the folded history with a single summary message.
        msg_wrap.memory = [
            Message(
                role="user",
                content=f"[Summary of previous steps]\n{summary}",
            ),
            *kept,
        ]
        # Push the compression metadata.
        await self._emit_step_event(
            content=(
                "[step] compress: prompt tokens "
                f"{trigger_tokens} > threshold {threshold}; "
                "history between Steps summarized."
            ),
            metadata=AgentStepCompressMetadata(
                type="step",
                extra_type="compress",
                prompt_tokens=trigger_tokens,
                threshold=threshold,
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
        # The native step loop always enters through intro_step — expose the
        # plan-revision built-in exactly here (idempotent).
        self._ensure_step_tools()
        await self._drain_peer_input()
        rs = self._init_run_state()
        if rs.step_index == 0 and rs.plan is None and not rs.simple_mode:
            # First Step ever: decide whether to decompose.
            await self._decide_decomposition()

        if rs.simple_mode or not rs.plan:
            # Bare run: one implicit execute Step ("execute").
            rs.begin_step("execute")
        else:
            node = rs.next_ready_node()
            if node is None:
                # Plan done or unready deps: fall back to a boundary Step.
                rs.begin_step("verify")
            else:
                rs.begin_node(node)
        # Refresh the Step's prompt-token window from the ledger proxy.
        rs.tokens.refresh_window(self.usage, rs.step_started_ts)
        # Keep the model aware of the current plan (idempotent snapshot) so
        # it can autonomously revise the plan via update_step mid-run.
        self._inject_plan_status()

        # Lifecycle hook: matchers may redirect the phase name
        # (override_phase) before the Step starts.
        intro_ev = StepIntroEvent.constructor(rs)
        await self._trigger_step_event(intro_ev)
        if intro_ev.override_phase and rs.current_phase != intro_ev.override_phase:
            rs.current_phase = intro_ev.override_phase
            logger.info(
                f"Step #{rs.step_index} phase overridden by matcher: "
                f"-> {intro_ev.override_phase}"
            )

        # Push the step-intro metadata.
        # Resolve the current node description (plan mode only).
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
        # Stall detection is also done per-iteration inside the loop; here it
        # is the idempotent fallback when the loop exits without stalling.
        if self._detect_step_stall() and not rs.stall_injected:
            await self._inject_give_up_prompt()
        # Subject-predicate summary of what this Step accomplished.
        await self._summarize_step()
        # Mark the DAG node done (no-op in simple mode).
        rs.complete_current_node()

        # Lifecycle hook: matchers may override the summary produced above
        # (override_verb / override_object).
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
        # Compression happens between Steps (pairing closed here); the
        # auxiliary call usage is accounted via the ledger proxy.
        await self._compress_history_between_steps()

    @override
    async def _append_tool_result_to_context(
        self,
        tool_call: ToolCall,
        func_response: str,
        response_msg: UniResponse[None, list[ToolCall] | None],
    ):
        """ReAct strategy: append assistant message with only this tool_call paired with its ToolResult.

        This follows OpenAI's ToolCall-ToolResult pairing requirement where every
        assistant message with tool_calls must be followed by corresponding tool messages.
        Only a single ToolCall is included per assistant message to prevent the
        "insufficient tool messages following tool_calls message" API error when the
        model returns multiple tool_calls in one response.

        The fabricated assistant message mirrors the provider's response
        verbatim: every field (``reasoning_content``, ``reasoning_signature``
        and any extra — ``Message`` allows extra) is carried over as-is via
        :meth:`_assistant_fields_from_response`, never hard-coded.
        """
        self._record_tool_signature(tool_call)
        msg_list = self.ctx.message
        msg_list.append(
            Message(
                role="assistant",
                content=response_msg.content if response_msg else None,
                tool_calls=[tool_call],
                **self._assistant_fields_from_response(response_msg),
            )
        )
        msg_list.append(
            ToolResult(
                role="tool",
                name=tool_call.function.name,
                content=func_response,
                tool_call_id=tool_call.id,
            )
        )
        # Deterministic failure guidance: a hard ERROR result is an objective
        # plan failure — teach the model to revise instead of retrying forever.
        self._maybe_inject_tool_failure_hint(tool_call, func_response)

    @override
    def _maybe_inject_tool_failure_hint(
        self, tool_call: ToolCall, func_response: str
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
        if not func_response.startswith("ERROR"):
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
        response_msg: UniResponse[None, list[ToolCall] | None],
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
        response_msg: UniResponse[None, list[ToolCall] | None] | None = None,
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
            f"Starting round {self.call_count} tool call, current message count: {len(msg_list)}"
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

        response_msg: UniResponse[None, list[ToolCall] | None] = await tools_caller(
            msg_list.unwrap(),
            tools,
            tool_choice=self._resolve_tool_choice(
                "required"
                if (config.llm.require_tools and not self._suggested_stop)
                else "auto"
            ),
            preset=self.preset,
            usage=self.usage,
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
