from __future__ import annotations

import asyncio
import contextlib
import json
import re
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import TYPE_CHECKING, Any, Literal, cast

from amrita_sense.exceptions import StreamStateError
from amrita_sense.hook.matcher import MatcherFactory
from amrita_sense.logging import debug_log, logger
from amrita_sense.streaming import SuspendObjectStream
from jinja2 import Template
from typing_extensions import Self, override

if TYPE_CHECKING:
    from amrita_sense.hook.event import ConstructableEvent

    from amrita_core.builtins.agent.state import Phase

from amrita_core.agent.context import StrategyContext
from amrita_core.agent.strategy import AgentStrategy
from amrita_core.builtins.agent.events import (
    StepAbortError,
    StepToolCallEvent,
    StepToolReturnEvent,
)
from amrita_core.builtins.agent.state import AgentRunState, DAGNode
from amrita_core.contents import MessageMetadataPayload, MessageWithMetadata
from amrita_core.libchat import (
    call_completion,
    get_last_response,
    tools_caller,
)
from amrita_core.tools.models import ToolChoice, ToolFunctionSchema
from amrita_core.types import (
    CONTENT_LIST_TYPE_ITEM,
    Function,
    Message,
    TextContent,
    ToolCall,
    ToolResult,
    UniResponse,
)

from ..consts import (
    BUILTIN_TOOLS_NAME,
    REASONING_CONTENT_TEMPLATE,
    REASONING_TEMPLATE,
    REFLECTION_TEMPLATE,
    STRUCTURED_REASONING_TEMPLATE,
)
from ..tools import (
    REASONING_TOOL,
    REFLECTION_TOOL,
    STOP_TOOL,
    UPDATE_STEP_TOOL,
)
from ..types import (
    AgentLoopErrorMetadata,
    AgentReasoningChunkMetadata,
    AgentReasoningMetadata,
    AgentReflectionMetadata,
    AgentStructuredReasoningChunkMetadata,
    AgentToolCallMetadata,
    AgentToolPredictionMetadata,
)


def _resolve_tool_name(tool: ToolFunctionSchema | dict) -> str:
    """Resolve the function name from a tool schema (object or dict form)."""
    if isinstance(tool, dict):
        return tool.get("function", {}).get("name", "")
    return tool.function.name


class BaseReActAgentStrategy(AgentStrategy, ABC):
    """
    Abstract base class for ReAct agent strategies with common execution logic.

    This class provides shared functionality for ReAct-style agents including:
    - Tool calling orchestration and execution flow control
    - Reasoning message generation and processing
    - Loop detection and recovery mechanisms
    - Tool call notification handling
    - Common error handling patterns
    - Unified stop state management via `_suggested_stop` flag

    ## Stop State Management

    The `_suggested_stop` flag controls the `tool_choice` parameter behavior:
    - When `False` (default): `tool_choice` can be set to "required" to force tool calls
    - When `True`: `tool_choice` switches to "auto", allowing the model to decide whether to call tools

    This flag is automatically set to `True` when the STOP_TOOL is invoked, enabling
    a smooth transition from mandatory tool execution to free-form response generation.

    Subclasses should implement strategy-specific behaviors like message formatting
    and context management while inheriting the core execution framework.

    ## Class Attributes

    - `agent_last_step`: Tracks the last reasoning step or action taken
    - `call_count`: Counter for tool call iterations
    - `tools`: List of available tools for the agent
    - `origin_msg`: Original user message content
    - `origin_instruction`: System instruction from training context
    - `reasoning_pc`: Reasoning process counter for loop detection
    - `_suggested_stop`: Flag indicating whether to switch tool_choice to auto mode
    """

    agent_last_step: str | None = None
    call_count = 1
    tools: list[ToolFunctionSchema]
    origin_msg: str = ""
    origin_instruction: str = ""
    reasoning_pc = 0
    _suggested_stop: bool = False  # Flag to switch tool_choice from required to auto
    _reasoning_tool_template: Template = REASONING_TEMPLATE
    _reasoning_content_template: Template = REASONING_CONTENT_TEMPLATE
    _structured_reasoning_template: Template = STRUCTURED_REASONING_TEMPLATE
    _reflection_template: Template = REFLECTION_TEMPLATE

    #  Reasoning Enhancement State
    _predicted_tools: list[str]
    """Tools predicted during structured reasoning."""

    #  Semantic step-level run state (native step loop)
    _run_state: "AgentRunState | None" = None
    """Semantic step-level run state, bridged from the framework loop state."""

    def _is_native_thinking_enabled(self) -> bool:
        """Return True when the model preset has native thinking enabled.

        Native thinking (Claude Extended Thinking, OpenAI o-series, etc.)
        may not support ``tool_choice``, so forced tool-choice values must
        be downgraded to ``"auto"`` to avoid provider errors.
        """
        preset = self.preset
        return (
            preset is not None
            and not isinstance(preset, str)
            and preset.thinking_config is not None
            and preset.thinking_config.thinking_type == "enabled"
        )

    def _resolve_tool_choice(self, desired: ToolChoice) -> ToolChoice:
        """Resolve the *actual* ``tool_choice`` to send to the provider.

        When native thinking is enabled the provider may reject forced
        values (``"required"`` or a specific tool schema).  In that case
        we fall back to ``"auto"`` and rely on prompt instructions instead.
        """
        if not self._is_native_thinking_enabled():
            return desired
        if desired == "required" or isinstance(desired, ToolFunctionSchema):
            return "auto"
        return desired  # "auto" | "none" pass through unchanged

    def __init__(self, ctx: StrategyContext):
        super().__init__(ctx)
        self.tools = []
        self.origin_instruction = self.train_content
        config = self.config
        if config.builtin.tool_calling_mode == "agent":
            self.tools.append(STOP_TOOL)
        self.tools.extend(self.tools_manager.tools_meta().values())
        #  Initialize reasoning enhancement state
        self._predicted_tools = []
        self._run_state = None
        # The plan-revision built-in (update_step) is exposed only when the
        # native step loop activates (intro_step), never in the legacy loop.
        self._step_tools_injected = False
        # Last plan snapshot injected into the context (change detection).
        self._last_plan_snapshot: str | None = None
        # Peer (reverse-stream) input: lazily opened on first Step boundary;
        # closed once (idempotent) when the agent run finishes.
        self._peer_input_gen: AsyncGenerator[Any, None] | None = None
        self._peer_input_closed: bool = False
        self.origin_msg: str = (
            "".join(
                chunk.text
                for chunk in ctx.original_context.user_query.content
                if isinstance(chunk, TextContent)
            )
            if isinstance(ctx.original_context.user_query.content, list)
            else ctx.original_context.user_query.content
        )

    # Step lifecycle (native step loop): intro/leave mark boundaries; a
    # Step may span multiple iterations, all state lives in self.run_state.

    @property
    def run_state(self) -> "AgentRunState | None":
        """Semantic step-level run state, bridged from the loop state."""
        return self._run_state

    @run_state.setter
    def run_state(self, value: "AgentRunState | None") -> None:
        self._run_state = value

    def _init_run_state(self) -> "AgentRunState":
        """Create (or reuse) the semantic run state for this strategy.

        The framework bridge (``AGENT_ENTRY``) shares one instance between
        ``AgentLoopState.run_state`` and the strategy; when running outside
        the framework (unit tests), a fresh instance is created here.
        """
        if self._run_state is None:
            self._run_state = AgentRunState()
            self._run_state.tokens.budget = (
                self.config.function_config.agent_step_token_budget
            )
        return self._run_state

    async def intro_step(self, phase: "Phase" = "analyze") -> None:
        """Enter a Step boundary (default no-op; subclasses may override).

        Pending peer messages (reverse stream) are drained and appended to
        the context before the Step starts, so the next LLM request sees
        them as the latest input.

        Args:
            phase: the reasoning phase being entered.
        """
        # Only the native step workflow calls intro_step — the legacy loop
        # never does — so this is the reliable point to expose the
        # plan-revision built-in (idempotent).
        self._ensure_step_tools()
        await self._drain_peer_input()
        rs = self._init_run_state()
        rs.begin_step(phase)

    def _ensure_step_tools(self) -> None:
        """Expose the ``update_step`` built-in once (idempotent).

        Called from ``intro_step``, which only the native step loop reaches;
        legacy runs therefore keep the original tool list.  The model needs
        to *see* the tool (plus the plan status injected at decomposition)
        before it can autonomously revise the plan mid-run.
        """
        if self._step_tools_injected:
            return
        self._step_tools_injected = True
        if UPDATE_STEP_TOOL not in self.tools:
            self.tools.append(UPDATE_STEP_TOOL)
            logger.info(
                "Step loop active: exposed 'update_step' built-in to the model."
            )

    async def _drain_peer_input(self) -> None:
        """Drain pending peer messages at a Step boundary (non-blocking).

        Consumes every object the consumer pushed over the reverse stream
        (``send_to_producer``) and appends it to the context as a ``user``
        message marked ``[peer message]``.  Messages pushed while the agent
        is inside a Step stay queued until the next boundary; messages
        pushed after the run finishes are dropped (queue closed).
        """
        if self._peer_input_closed:
            return
        stream = self.io_stream
        if not isinstance(stream, SuspendObjectStream):
            self._peer_input_closed = True
            return
        if self._peer_input_gen is None:
            try:
                self._peer_input_gen = stream.get_producer_input_generator()
            except StreamStateError:
                # Reverse stream already consumed (callback mode, another
                # consumer, ...): silently skip peer draining.
                self._peer_input_closed = True
                return
        while True:
            # Non-blocking drain: wait_for(coro, 0) would time out before the
            # coroutine even runs; a 1ms window is enough for an already
            # buffered item (anyio receive_nowait returns synchronously).
            try:
                item = await asyncio.wait_for(
                    self._peer_input_gen.__anext__(), timeout=0.001
                )
            except asyncio.TimeoutError:
                break  # No more pending messages right now.
            except StopAsyncIteration:
                self._peer_input_closed = True
                break  # Peer sent the done marker.
            self.ctx.message.append(
                Message(role="user", content=f"[peer message]\n{item}")
            )

    async def _close_peer_input(self) -> None:
        """Notify the peer that the agent run is finished (idempotent).

        After this, further ``send_to_producer`` calls from the consumer
        side fail fast instead of blocking on the queue timeout.
        """
        if self._peer_input_closed:
            return
        self._peer_input_closed = True
        stream = self.io_stream
        if not isinstance(stream, SuspendObjectStream):
            return
        with contextlib.suppress(StreamStateError):
            await stream.send_done_to_producer()

    @override
    async def on_post_process(self) -> None:
        """Agent run finished: close the peer input channel (idempotent)."""
        await self._close_peer_input()

    async def leave_step(self, phase: "Phase | None" = None) -> None:
        """Leave a Step boundary (default no-op; subclasses may override)."""
        # Hook point: token accounting, stall injection, compression and the
        # subject-predicate summary are implemented by subclasses / mixins.
        return

    async def after_iteration(self) -> None:
        """Per-iteration hook, called after each successful tool round.

        Runs *inside* the execute-phase iteration loop (STEP_EXEC), so it can
        stop the loop early — e.g. stall detection with give-up prompt
        injection — before more tokens are burned.  Default no-op; subclasses
        may override.
        """
        return

    async def _trigger_step_event(
        self,
        event: "ConstructableEvent",
        *,
        exception_ignored: tuple[type[BaseException], ...] = (),
    ) -> None:
        """Dispatch a step-lifecycle event to registered matchers.

        Handlers may mutate the event (the caller reads fields back) or raise
        an exception type listed in ``exception_ignored`` — it propagates out
        of ``trigger_event`` back to the calling lifecycle hook.
        """
        await MatcherFactory.trigger_event(event, exception_ignored=exception_ignored)

    async def _trigger_tool_call_event(self, tool_call: ToolCall) -> tuple[str, bool]:
        """Fire the pre-call event for a regular tool.

        Returns ``(arguments, cancel)`` — matchers may rewrite ``arguments``
        or set ``cancel`` (or raise :class:`StepAbortError`) to cancel the
        call without executing it.
        """
        rs = self._init_run_state()
        ev = StepToolCallEvent.constructor(
            rs,
            tool_name=tool_call.function.name,
            tool_id=tool_call.id,
            arguments=tool_call.function.arguments,
        )
        try:
            await self._trigger_step_event(ev, exception_ignored=(StepAbortError,))
        except StepAbortError:
            logger.info(f"Tool call {tool_call.function.name} aborted by matcher.")
            return (ev.arguments, True)
        return (ev.arguments, ev.cancel)

    async def _trigger_tool_return_event(
        self, tool_call: ToolCall, result: str
    ) -> tuple[str, bool]:
        """Fire the post-call event for a regular tool.

        Returns ``(result, skip_append)`` — matchers may rewrite ``result``
        or set ``skip_append`` (or raise :class:`StepAbortError`) to skip
        writing the result back to the context.
        """
        rs = self._init_run_state()
        ev = StepToolReturnEvent.constructor(
            rs,
            tool_name=tool_call.function.name,
            tool_id=tool_call.id,
            result=result,
        )
        try:
            await self._trigger_step_event(ev, exception_ignored=(StepAbortError,))
        except StepAbortError:
            logger.info(f"Tool return {tool_call.function.name} skipped by matcher.")
            return (ev.result, True)
        return (ev.result, ev.skip_append)

    async def _emit_step_event(
        self,
        content: str,
        metadata: MessageMetadataPayload,
    ) -> None:
        """Push a step-loop lifecycle event as stream metadata.

        Shared helper for the step-loop lifecycle hooks (intro_step /
        leave_step / decomposition / stall / compression); the payloads are
        the ``AgentStep*Metadata`` TypedDicts from ``builtins.types``.

        Note: distinct from ``_emit_step_metadata(step: dict)`` which emits
        a *structured-reasoning* step parsed from the model output.
        """
        await self.io_stream.yield_response(
            MessageWithMetadata(content=content, metadata=metadata)
        )

    def _record_tool_signature(self, tool_call: ToolCall) -> None:
        """Record a tool-call signature in the current Step (stall detection).

        Base implementation is a no-op; the built-in ReAct strategy records
        signatures into ``run_state.step_tool_signatures``.
        """
        return

    def _detect_step_stall(self) -> bool:
        """Check whether the current Step is stalled (duplicate tool calls).

        Base implementation always reports ``False``; the built-in ReAct
        strategy performs real signature-based detection.
        """
        return False

    def _should_cancel_tool_call(self, tool_call: ToolCall) -> bool:
        """Whether this tool call should be cancelled *before* execution.

        Base implementation always returns ``False``.  Subclasses (e.g. the
        built-in ReAct strategy) may override this to return ``True`` when
        the call would trip the stall detector — the caller then returns a
        ``"Cancelled: ..."`` result instead of executing the tool, so the
        model sees an explicit cancellation rather than a normal result.
        """
        return False

    async def _handle_update_step(self, args: dict[str, Any]) -> None:
        """Handle the ``update_step`` built-in tool.

        Updates the semantic plan in ``run_state`` only — the Sense workflow
        itself is not modified (DAG is a hint layer, execution stays linear).

        Args:
            args: tool arguments with ``action`` (replan/mark_done/add_step/
                remove_step) and optional ``dag`` / ``node`` / ``node_id``.
        """
        rs = self._init_run_state()
        action = args.get("action")

        if action == "replan" and args.get("dag"):
            rs.plan = [DAGNode.model_validate(n) for n in args["dag"]]
            rs.completed_step_ids = []
            rs.current_step_id = None
        elif action == "mark_done":
            rs.complete_current_node()
        elif action == "add_step" and args.get("node"):
            node = DAGNode.model_validate(args["node"])
            if rs.plan is None:
                rs.plan = []
            rs.plan.append(node)
        elif action == "remove_step" and args.get("node_id"):
            nid = args["node_id"]
            if rs.plan:
                rs.plan = [n for n in rs.plan if n.id != nid]
            if nid in rs.completed_step_ids:
                rs.completed_step_ids.remove(nid)
        rs.plan_revision += 1
        logger.info(
            f"update_step({action}) applied, plan_revision={rs.plan_revision}, "
            f"plan={[n.id for n in (rs.plan or [])]}, done={rs.completed_step_ids}"
        )

    async def _generate_reasoning_content(
        self, tool_call: ToolCall, reasoning_trigger_msg: list[CONTENT_LIST_TYPE_ITEM]
    ) -> UniResponse[str, None]:
        tools = [
            {
                "name": tool.function.name,
                "description": tool.function.description,
            }
            for tool in self.tools
        ]
        resp_msg: dict[str, Any] = json.loads(tool_call.function.arguments)
        last_step: str = resp_msg.get("last_step", "(Err: Not given)")
        summary: str = resp_msg.get("summary", "(Err: Not given)")
        self.agent_last_step = last_step

        await self.io_stream.yield_response(
            MessageWithMetadata(
                summary,
                AgentReasoningMetadata(
                    type="reasoning",
                    extra_type="pre_resolve",
                    last_step=last_step,
                    summary=summary,
                ),
            )
        )

        use_structured = self._should_use_structured_reasoning()
        predict_tools = self._should_predict_tools()

        if use_structured:
            depth = self.config.builtin.react_config.reasoning_depth
            template_content = await asyncio.to_thread(
                self._structured_reasoning_template.render,
                tools=tools,
                last_step=last_step,
                summary=summary,
                stg=self,
                depth=depth,
                predict_tools=predict_tools,
            )
        else:
            template_content = await asyncio.to_thread(
                self._reasoning_content_template.render,
                tools=tools,
                last_step=last_step,
                summary=summary,
                stg=self,
            )

        reasoning_trigger_msg[0] = Message(
            role="system",
            content=template_content,
        )

        # Custom yield wrapper that emits reasoning chunk metadata during
        # streaming (per-step metadata emitted post-hoc after parsing).
        def _yield_wrapper(chunk):
            if isinstance(chunk, str):
                return MessageWithMetadata(
                    chunk,
                    metadata=AgentReasoningChunkMetadata(
                        type="text",
                        extra_type="reasoning_chunk",
                        content=chunk,
                    ),
                )
            return chunk

        ct: UniResponse[str, None] = await get_last_response(
            call_completion(
                reasoning_trigger_msg,
                preset=self.preset,
                config=self.config,
                usage=self.usage,
            ),
            yield_to=self.io_stream,
            yield_to_wrapper=_yield_wrapper,
        )

        # Prefer `content` (template output), fall back to the provider's
        # native `reasoning_content` field.
        reasoning_text = ct.content or ct.reasoning_content or ""
        if use_structured:
            # Parse steps for metadata tracking
            steps = self._parse_reasoning_steps(reasoning_text)
            if steps:
                # Emit per-step metadata for front-end consumption
                for step in steps:
                    await self._emit_step_metadata(step)

            if predict_tools:
                predicted = self._parse_tool_prediction(reasoning_text)
                if predicted:
                    self._predicted_tools = predicted
                    await self.io_stream.yield_response(
                        MessageWithMetadata(
                            content=f"[ToolPrediction] Expecting: {', '.join(predicted)}",
                            metadata=AgentToolPredictionMetadata(
                                type="tool_prediction",
                                extra_type="reasoning_prediction",
                                predicted_tools=predicted,
                                predicted_next_action="See reasoning steps",
                            ),
                        )
                    )
        return ct

    def _should_use_structured_reasoning(self) -> bool:
        """Check whether structured reasoning should be used."""
        config = self.config
        return (
            hasattr(config, "builtin")
            and hasattr(config.builtin, "react_config")
            and config.builtin.react_config is not None
            and config.builtin.react_config.structured_reasoning
        )

    def _should_predict_tools(self) -> bool:
        """Check whether tool prediction during reasoning should be used."""
        config = self.config
        return self._should_use_structured_reasoning() and (
            hasattr(config.builtin.react_config, "tool_prediction")
            and config.builtin.react_config.tool_prediction
        )

    def _should_enable_reflection(self) -> bool:
        """Check whether post-reasoning reflection should be used."""
        config = self.config
        return (
            hasattr(config, "builtin")
            and hasattr(config.builtin, "react_config")
            and config.builtin.react_config is not None
            and config.builtin.react_config.enable_reflection
        )

    @staticmethod
    def _parse_reasoning_steps(text: str) -> list[dict[str, str | None]]:
        """Parse structured reasoning output into step dictionaries.

        Extracts ``[Step N/M] [phase]`` markers and their associated content.
        (``[TOOL_PREDICTION]`` blocks are parsed separately in ``_parse_tool_prediction``.)

        Returns:
            List of dicts with keys: step_idx, total, phase, content
        """

        # Match [Step N/M] [phase] blocks
        step_pattern = re.compile(
            r"\[Step\s+(\d+)(?:/(\d+))?\]\s*\[(\w+)\]\s*\n(.*?)(?=\n\[Step\s+\d|\n\[TOOL_PREDICTION\]|\Z)",
            re.DOTALL,
        )
        steps: list[dict[str, str | None]] = [
            {
                "step_idx": m.group(1),
                "total": m.group(2),
                "phase": m.group(3),
                "content": m.group(4).strip(),
            }
            for m in step_pattern.finditer(text)
        ]

        return steps

    @staticmethod
    def _parse_tool_prediction(text: str) -> list[str] | None:
        """Parse the [TOOL_PREDICTION] block from structured reasoning output."""
        pred_match = re.search(
            r"\[TOOL_PREDICTION\]\s*\ntools:\s*(.+?)\nnext_action:\s*(.+?)(?:\n|\Z)",
            text,
            re.IGNORECASE,
        )
        if pred_match:
            tools_str = pred_match.group(1).strip()
            # Split by comma, strip whitespace
            return [t.strip() for t in tools_str.split(",") if t.strip()]
        return None

    async def _emit_step_metadata(self, step: dict[str, str | None]) -> None:
        """Emit a structured reasoning step as stream metadata."""
        phase_str = step.get("phase")
        phase: Literal["analyze", "plan", "execute", "verify"] | None = (
            phase_str if phase_str in ("analyze", "plan", "execute", "verify") else None
        )
        step_idx_raw = step.get("step_idx", "0")
        step_idx = int(step_idx_raw) if step_idx_raw is not None else 0
        total_raw = step.get("total")
        total = int(total_raw) if total_raw is not None else None
        await self.io_stream.yield_response(
            MessageWithMetadata(
                content=cast(str, step.get("content", "")),
                metadata=AgentStructuredReasoningChunkMetadata(
                    type="text",
                    extra_type="structured_reasoning_step",
                    step_index=step_idx,
                    total_steps=total,
                    sub_problem=None,
                    phase=phase,
                ),
            )
        )

    async def _run_reflection(
        self,
        reason_context: list[CONTENT_LIST_TYPE_ITEM],
    ) -> list[dict[str, str]]:
        """Run the post-reasoning reflection flow.

        Calls ``verify_reasoning`` tool up to ``reflection_depth`` times,
        streaming each result as ``AgentReflectionMetadata``.

        Returns:
            List of reflection result dicts with keys:
            check_type, result, detail
        """
        config = self.config
        max_rounds = config.builtin.react_config.reflection_depth
        reflection_results: list[dict[str, str]] = []

        for _ in range(max_rounds):
            # Build system message via Jinja2 (CPU-bound, run in thread)
            reflection_system_msg = await asyncio.to_thread(
                self._reflection_template.render,
                last_step=self.agent_last_step or "No previous step",
                original_msg=self.origin_msg,
            )
            msg_list: list[CONTENT_LIST_TYPE_ITEM] = [
                Message(role="system", content=reflection_system_msg),
                *reason_context,
            ]

            tool_response = await tools_caller(
                msg_list,
                [REFLECTION_TOOL],
                tool_choice=self._resolve_tool_choice(REFLECTION_TOOL),
                preset=self.preset,
                usage=self.usage,
            )
            if not tool_response.tool_calls:
                break

            tc: ToolCall = tool_response.tool_calls[0]
            try:
                args: dict[str, str] = json.loads(tc.function.arguments)
            except json.JSONDecodeError as exc:
                logger.warning(
                    f"Failed to parse reflection tool arguments: {exc!s}. "
                    f"Raw: {tc.function.arguments!r}"
                )
                continue
            check_type: str = args.get("check_type", "self_check")
            result: str = args.get("result", "warning")
            detail: str = args.get("detail", "")

            reflection_results.append(
                {
                    "check_type": check_type,
                    "result": result,
                    "detail": detail,
                }
            )

            # Stream reflection result to user
            await self.io_stream.yield_response(
                MessageWithMetadata(
                    content=f"[Reflection] {check_type}: {result}",
                    metadata=AgentReflectionMetadata(
                        type="reflection",
                        extra_type=check_type,
                        reflection_type=cast(
                            Literal[
                                "self_check",
                                "contradiction_check",
                                "completeness_check",
                            ],
                            check_type,
                        ),
                        result=cast(Literal["pass", "warning", "fail"], result),
                        detail=detail,
                    ),
                )
            )

            logger.info(f"Reflection {check_type}: {result} — {detail}")

            # If any reflection passes, we consider it satisfactory
            if result == "pass":
                break

        return reflection_results

    async def _generate_reasoning_msg(
        self,
        tools_ctx: list[ToolFunctionSchema],
        /,
        then: Callable[
            [
                Self,
                ToolCall,
                UniResponse[str, None],
            ],
            Awaitable[Any],
        ],
    ):
        last_step = self.agent_last_step or "No previous step"
        original_msg = self.origin_msg
        reasoning_trigger_msg: list[CONTENT_LIST_TYPE_ITEM] = [
            Message(
                role="system",
                content=self._reasoning_tool_template.render(
                    stg=self,
                    last_step=last_step,
                    original_msg=original_msg,
                ),
            ),
            *self.ctx.message.unwrap(exclude_system=True),
        ]
        tool_response: UniResponse[None, list[ToolCall] | None] = await tools_caller(
            reasoning_trigger_msg,
            [REASONING_TOOL, *tools_ctx],
            tool_choice=self._resolve_tool_choice(REASONING_TOOL),
            preset=self.preset,
            usage=self.usage,
        )
        if not tool_response.tool_calls:
            logger.warning(
                "No tool calls returned from reasoning trigger"
                " (native thinking may have suppressed tool_choice=REASONING_TOOL)"
            )
            return
        tool_call: ToolCall = tool_response.tool_calls[0]
        response = await self._generate_reasoning_content(
            tool_call, reasoning_trigger_msg
        )

        await then(self, tool_call, response)

    @staticmethod
    def _build_stop_response(function_args: dict[str, Any]) -> str:
        """Build the stop tool response message.

        Args:
            function_args: Arguments passed to the stop tool

        Returns:
            The instruction message for final answer generation
        """
        func_response = (
            "<BEGIN_OF_INSTRUCTIONS>\n"
            + "You have indicated readiness to provide the final answer. "
            + "Please now generate the final, comprehensive response for the user."
            + "You must NOT call any tools again."
            + "\n<END_OF_INSTRUCTIONS>"
        )
        if "result" in function_args:
            debug_log(f"[Done] {function_args['result']}")
            func_response += f"\nWork summary :\n{function_args['result']}"
        return func_response

    def _check_and_handle_loop_reasoning(self) -> str | None:
        """Check if loop reasoning threshold has been exceeded and build prompt.

        Returns:
            Prompt message if loop is detected, None otherwise
        """
        config = self.config
        if self.reasoning_pc > config.builtin.loop_reasoning_trigger:
            prompt = f"Loop reasoning triggered. Trying to give up the tool call at ChatObject `{self.stream_id}`."
            logger.error(prompt)
            self.ctx.message.append(
                Message(
                    role="user",
                    content="<BEGIN_OF_EXTRA>\n\n"
                    + "You had called too many duplicate reasoning, which may indicate that you are stuck in a loop."
                    + "Please try to give up the current tool calling and directly answer the user query based on the information you have."
                    + "\n\n<END_OF_EXTRA>\n",
                )
            )
            return prompt
        return None

    async def _notify_tool_calls(
        self,
        result_msg_list: list[ToolResult],
        function_name: str,
        tool_call_id: str,
    ):
        """Send tool call completion notifications to user.

        Args:
            result_msg_list: List of tool results to notify
            function_name: Name of the called function
            tool_call_id: ID of the tool call
        """
        config = self.config
        if config.builtin.agent_tool_call_notice == "notify":
            for rslt in result_msg_list:
                await self.io_stream.yield_response(
                    MessageWithMetadata(
                        content=f"Called tool {rslt.name}\n",
                        metadata=AgentToolCallMetadata(
                            type="function_call",
                            extra_type=None,
                            function_name=function_name,
                            is_done=True,
                            tool_id=tool_call_id,
                            err=None,
                        ),
                    )
                )

    async def _build_stop_response_and_append(
        self,
        function_args: dict[str, Any],
        response_msg: UniResponse[None, list[ToolCall] | None],
        function_name: str,
        function_call_id: str,
        function_response: str,
    ):
        """Build stop response and append to message list (strategy-specific).

        Subclasses can override this to customize how the stop response is handled.
        Default implementation does nothing - subclasses should implement their own logic.

        Args:
            function_args: Arguments passed to the stop tool
            response_msg: The original response message
            function_name: Name of the function being called
            function_call_id: ID of the function call
            function_response: Response from the function
        """
        pass

    @abstractmethod
    async def _append_reasoning(
        self, tool_call: ToolCall, reasoning_content: UniResponse[str, None]
    ):
        """Append reasoning content to context (strategy-specific).

        Subclasses must implement this to define how reasoning results are added to context.

        Args:
            tool_call: The tool call object containing the reasoning request
            reasoning_content: The response containing the generated reasoning content
        """
        ...

    async def _handle_loop_reasoning_cleanup(self, prompt: str):
        """Clean up strategy-specific state when loop reasoning is detected.

        Subclasses can override this to perform cleanup operations.

        Args:
            prompt: The loop detection prompt message
        """
        pass

    async def _run_tool_calls_concurrently(
        self,
        tool_calls: list[ToolCall],
    ) -> list[tuple[ToolCall, str, BaseException | None]]:
        """Execute multiple tool calls concurrently via asyncio.gather.

        Built-in flow-control tools (REASONING, STOP) are dispatched to their
        specialised handlers inside each coroutine.  Regular tools use
        :meth:`call_tool`.  One failure does not cancel the others.
        Results are returned in the same order as the input list.

        Subclasses may override this to change the execution strategy (e.g. add
        throttling, retries, or switch to sequential fallback).

        Args:
            tool_calls: ToolCall objects to execute concurrently.  Callers should
                order them so that built-in tools appear **after** regular tools
                so that the side-effects of built-in handlers do not race with
                the context modifications produced by regular-tool result
                processing.

        Returns:
            List of ``(tool_call, result_string, original_exception)`` tuples.
            ``original_exception`` is the exception instance when an error
            occurred, ``None`` otherwise.  On error ``result_string`` is
            formatted as ``"ERR: Tool {name} execution failed\\n{error}"``.
        """

        async def _exec_one(tc: ToolCall) -> tuple[ToolCall, str, BaseException | None]:
            fn = tc.function.name
            # Record the tool-call signature for per-Step stall detection
            # (covers built-in and regular tools uniformly).
            self._record_tool_signature(tc)
            try:
                # Cancel the call before execution when it would trip the
                # stall detector (explicit cancellation, not a normal result).
                if self._should_cancel_tool_call(tc):
                    return (
                        tc,
                        "Cancelled: Reach the max limit of repeatly calling tool.",
                        None,
                    )
                if fn == REASONING_TOOL.function.name:
                    content: UniResponse[
                        str, None
                    ] = await self._generate_reasoning_content(
                        tc, self.ctx.original_context.unwrap()
                    )
                    await self._append_reasoning(tc, content)
                    return (tc, content.content, None)
                if fn == UPDATE_STEP_TOOL.function.name:
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    await self._handle_update_step(args)
                    # Echo the revised plan back so the model can confirm the
                    # change without waiting for the next Step intro.
                    rs = self._init_run_state()
                    plan_desc = (
                        ", ".join(n.id for n in (rs.plan or []))
                        if rs.plan
                        else "(none)"
                    )
                    return (
                        tc,
                        (
                            "<STEP_PLAN_UPDATED> revised plan: "
                            f"{plan_desc}; done: {rs.completed_step_ids}"
                        ),
                        None,
                    )
                if fn == STOP_TOOL.function.name:
                    args: dict[str, Any] = json.loads(tc.function.arguments)
                    self.agent_last_step = "Stopped"
                    self.reasoning_pc = 0
                    self._suggested_stop = True
                    logger.info("Agent work has been terminated.")

                    if self._should_enable_reflection():
                        logger.debug("Running post-reasoning reflection...")
                        reason_ctx = self.ctx.original_context.unwrap()
                        reflection_results = await self._run_reflection(reason_ctx)
                        failures = [
                            r for r in reflection_results if r["result"] == "fail"
                        ]
                        if failures:
                            correction_msg = (
                                "<BEGIN_OF_REFLECTION_CORRECTION>\n"
                                + "Your reasoning was checked and the following issues were found:\n"
                                + "\n".join(
                                    f"- [{r['check_type']}] {r['detail']}"
                                    for r in failures
                                )
                                + "\nPlease re-examine your reasoning and correct these issues "
                                + "before providing the final answer.\n"
                                + "<END_OF_REFLECTION_CORRECTION>"
                            )
                            self.ctx.message.append(
                                Message(role="user", content=correction_msg)
                            )
                            # Empty result → caller skips stop response.
                            return (tc, "", None)

                    result = self._build_stop_response(args)
                    return (tc, result, None)

                # Regular tool: pre-call event (rewrite/cancel), execute,
                # then post-call event (rewrite/skip append).
                args_str, cancel = await self._trigger_tool_call_event(tc)
                if cancel:
                    return (
                        tc,
                        "Cancelled: Reach the max limit of repeatly calling tool.",
                        None,
                    )
                # Apply any argument rewrite from the matcher.
                if args_str != tc.function.arguments:
                    tc = ToolCall(
                        id=tc.id,
                        function=Function(
                            name=tc.function.name,
                            arguments=args_str,
                        ),
                    )
                result = await self.call_tool(tc)
                result, skip_append = await self._trigger_tool_return_event(tc, result)
                if skip_append:
                    return (tc, "", None)
                return (tc, result, None)
            except Exception as e:
                error_content = await self._handle_tool_error_common(fn, e, tc.id)
                return (tc, error_content, e)

        return await asyncio.gather(*[_exec_one(tc) for tc in tool_calls])

    async def _execute_tool_loop(
        self,
        response_msg: UniResponse[None, list[ToolCall] | None],
    ) -> bool:
        """Execute the main tool calling loop.

        All tool calls are executed concurrently via
        :meth:`_run_tool_calls_concurrently`.  Built-in tools are ordered last
        so that their message-list side-effects (reasoning append, stop
        response) are applied after regular-tool results.

        Args:
            response_msg: The response from tools_caller containing tool calls.

        Returns:
            True if execution should continue, False if it should stop.
        """
        if not (tool_calls := response_msg.tool_calls):
            return False

        # Built-in tools last so their side-effects don't race with regular tools.
        tool_calls.sort(
            key=lambda tc: (
                tc.function.name
                in (REASONING_TOOL.function.name, STOP_TOOL.function.name)
            )
        )

        #  Notify "calling" for every tool
        for tc in tool_calls:
            await self.io_stream.yield_response(
                MessageWithMetadata(
                    content=f"Calling function {tc.function.name}\n",
                    metadata=AgentToolCallMetadata(
                        type="function_call",
                        extra_type=None,
                        function_name=tc.function.name,
                        is_done=False,
                        tool_id=tc.id,
                        err=None,
                    ),
                )
            )

        concurrent_results: list[
            tuple[ToolCall, str, BaseException | None]
        ] = await self._run_tool_calls_concurrently(tool_calls)

        #  Append results sequentially
        result_msg_list: list[ToolResult] = []
        should_continue = True  # default: keep looping (old `ret` semantics)
        for tc, func_response, exc in concurrent_results:
            function_name = tc.function.name
            is_reasoning = function_name == REASONING_TOOL.function.name
            is_stop = function_name == STOP_TOOL.function.name

            if is_reasoning:
                if func_response.startswith("ERR:"):
                    # Reasoning generation failed (raised inside the
                    # concurrent runner); surface the error, don't swallow.
                    self.reasoning_pc = 0
                    await self._handle_error_append(
                        function_name,
                        func_response,
                        tc.id,
                        original_exception=exc,
                        response_msg=response_msg,
                    )
                else:
                    # _run_tool_calls_concurrently already called _append_reasoning.
                    should_continue = True
                continue

            if is_stop:
                if not func_response:
                    # Reflection failed — correction already injected, continue.
                    continue
                await self._build_stop_response_and_append(
                    json.loads(tc.function.arguments),
                    response_msg,
                    function_name,
                    tc.id,
                    func_response,
                )
            elif func_response.startswith("ERR:"):
                self.reasoning_pc = 0
                await self._handle_error_append(
                    function_name,
                    func_response,
                    tc.id,
                    original_exception=exc,
                    response_msg=response_msg,
                )
            else:
                self.reasoning_pc = 0
                await self._append_tool_result_to_context(
                    tc, func_response, response_msg
                )

            logger.debug(f"Function {function_name} returned: {func_response}")
            result_msg_list.append(
                ToolResult(
                    role="tool",
                    content=func_response,
                    name=function_name,
                    tool_call_id=tc.id,
                )
            )
            self.call_count += 1

            prompt = self._check_and_handle_loop_reasoning()
            if prompt is not None:
                await self._handle_loop_reasoning_cleanup(prompt)
                await self.io_stream.yield_response(
                    MessageWithMetadata(
                        content=prompt,
                        metadata=AgentLoopErrorMetadata(
                            type="error",
                            extra_type="loop_reasoning",
                            chat_object_id=self.stream_id,
                            error=prompt,
                        ),
                    )
                )
                # Stop early — don't process remaining results.
                should_continue = False
                break

        #  Notify once with the complete result list.
        if result_msg_list:
            await self._notify_tool_calls(
                result_msg_list,
                result_msg_list[-1].name,
                result_msg_list[-1].tool_call_id,
            )

        return should_continue

    async def _handle_error_append(
        self,
        function_name: str,
        error_content: str,
        tool_call_id: str,
        original_exception: BaseException | None = None,
        response_msg: UniResponse[None, list[ToolCall] | None] | None = None,
    ):
        """Handle appending error messages to context (strategy-specific).

        Args:
            function_name: Name of the failed function.
            error_content: Formatted error message to append.
            tool_call_id: ID of the failed tool call.
            original_exception: The original exception, or ``None`` when the error
                was captured as a string during concurrent execution.
            response_msg: The provider response, used to carry ``reasoning_content``
                back on the fabricated assistant message (thinking-mode round-trip).
        """
        ...

    @abstractmethod
    async def _append_tool_result_to_context(
        self,
        tool_call: ToolCall,
        func_response: str,
        response_msg: UniResponse[None, list[ToolCall] | None],
    ):
        """Append tool result to context (strategy-specific).

        Subclasses must implement this to define how tool results are added to context.
        Subclasses should use self.ctx.message to access the message list.

        Args:
            tool_call: The tool call object
            func_response: The function execution result
            response_msg: The original response message
        """
        ...

    async def _handle_tool_error_common(
        self,
        function_name: str,
        err: BaseException,
        tool_call_id: str,
    ) -> str:
        """Common error handling logic for tool execution failures.

        Args:
            function_name: Name of the failed function
            err: The exception that occurred
            tool_call_id: ID of the tool call

        Returns:
            Error message string
        """
        logger.opt(raw=True, exception=err, colors=True).error(
            f"Function {function_name} execution failed: {err}"
        )
        config = self.config
        if (
            config.builtin.tool_calling_mode == "agent"
            and function_name not in BUILTIN_TOOLS_NAME
            and config.builtin.agent_tool_call_notice
        ):
            await self.io_stream.yield_response(
                MessageWithMetadata(
                    content=f"Error: {function_name} failed.",
                    metadata=AgentToolCallMetadata(
                        type="function_call",
                        extra_type=None,
                        function_name=function_name,
                        is_done=True,
                        tool_id=tool_call_id,
                        err=err,
                    ),
                )
            )
        return f"ERR: Tool {function_name} execution failed\n{err!s}"

    @override
    async def on_exception(self, exc: BaseException) -> None:
        """No action to do, because we had already handled the exception in the agent strategy"""
        return


class NoActionAgentStrategy(AgentStrategy):
    """No action agent strategy. Use this strategy to give up the tool calling proces."""

    async def run(self) -> None:
        """No action"""
        return

    @override
    async def on_exception(self, exc: BaseException) -> None:
        """No action to do, because we had already handled the exception in the agent strategy"""
        return

    @classmethod
    def get_category(
        cls,
    ) -> Literal["workflow"]:
        return "workflow"


__all__ = [
    "BaseReActAgentStrategy",
    "NoActionAgentStrategy",
]
