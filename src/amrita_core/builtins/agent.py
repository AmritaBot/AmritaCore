from __future__ import annotations

import asyncio
import json
import re
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, Literal, cast

from amrita_sense.logging import debug_log, logger
from jinja2 import Template
from typing_extensions import Self, override

from amrita_core.agent.context import StrategyContext
from amrita_core.agent.strategy import AgentStrategy
from amrita_core.contents import MessageWithMetadata
from amrita_core.libchat import (
    call_completion,
    get_last_response,
    tools_caller,
)
from amrita_core.types import (
    CONTENT_LIST_TYPE_ITEM,
    Function,
    Message,
    SendMessageWrap,
    TextContent,
    ToolCall,
    ToolResult,
    UniResponse,
)
from amrita_core.utils import gather_usage

from .consts import (
    BUILTIN_TOOLS_NAME,
    HYBRID_TEMPLATE,
    REASONING_CONTENT_TEMPLATE,
    REASONING_TEMPLATE,
    REFLECTION_TEMPLATE,
    STRUCTURED_REASONING_TEMPLATE,
)
from .tools import (
    PROCESS_MESSAGE,
    REASONING_TOOL,
    REFLECTION_TOOL,
    STOP_TOOL,
)
from .types import (
    AgentLoopErrorMetadata,
    AgentReasoningChunkMetadata,
    AgentReasoningMetadata,
    AgentReflectionMetadata,
    AgentStructuredReasoningChunkMetadata,
    AgentToolCallMetadata,
    AgentToolPredictionMetadata,
)


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
    tools: list[Any]
    origin_msg: str = ""
    origin_instruction: str = ""
    reasoning_pc = 0
    _suggested_stop: bool = False  # Flag to switch tool_choice from required to auto
    _reasoning_tool_template: Template = REASONING_TEMPLATE
    _reasoning_content_template: Template = REASONING_CONTENT_TEMPLATE
    _structured_reasoning_template: Template = STRUCTURED_REASONING_TEMPLATE
    _reflection_template: Template = REFLECTION_TEMPLATE

    #  Reasoning Enhancement State
    _predicted_tools: list[str]  # Tools predicted during structured reasoning

    def __init__(self, ctx: StrategyContext):
        super().__init__(ctx)
        self.tools = []
        self.origin_instruction = self.chat_object.train.content
        config = self.chat_object.config
        if config.builtin.tool_calling_mode == "agent":
            self.tools.append(STOP_TOOL.model_dump())
        self.tools.extend(self.tools_manager.tools_meta_dict().values())
        #  Initialize reasoning enhancement state
        self._predicted_tools = []
        self.origin_msg: str = (
            "".join(
                chunk.text
                for chunk in ctx.original_context.user_query.content
                if isinstance(chunk, TextContent)
            )
            if isinstance(ctx.original_context.user_query.content, list)
            else ctx.original_context.user_query.content
        )

    async def _generate_reasoning_content(
        self, tool_call: ToolCall, reasoning_trigger_msg: list[CONTENT_LIST_TYPE_ITEM]
    ) -> UniResponse[str, None]:
        tools = [
            {
                "name": tool["function"]["name"],
                "description": tool["function"]["description"],
            }
            for tool in self.tools
        ]
        resp_msg: dict[str, Any] = json.loads(tool_call.function.arguments)
        last_step: str = resp_msg["last_step"]
        summary: str = resp_msg["summary"]
        self.agent_last_step = last_step

        await self.chat_object.io_stream.yield_response(
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
            depth = self.chat_object.config.builtin.react_config.reasoning_depth
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

        # Custom yield wrapper that emits reasoning chunk metadata during streaming.
        # Note: accurate per-step metadata is emitted post-hoc by _emit_step_metadata
        # once the full structured reasoning text has been parsed.
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
                preset=self.ctx.chat_object.preset,
                config=self.chat_object.config,
            ),
            yield_to=self.ctx.chat_object.io_stream,
            yield_to_wrapper=_yield_wrapper,
        )

        #  Post-process structured reasoning
        if use_structured:
            reasoning_text = ct.content
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
                    await self.chat_object.io_stream.yield_response(
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

        self.chat_object.extra_usage = gather_usage(
            self.chat_object.extra_usage, ct.usage
        )
        return ct

    def _should_use_structured_reasoning(self) -> bool:
        """Check whether structured reasoning should be used."""
        config = self.chat_object.config
        return (
            hasattr(config, "builtin")
            and hasattr(config.builtin, "react_config")
            and config.builtin.react_config is not None
            and config.builtin.react_config.structured_reasoning
        )

    def _should_predict_tools(self) -> bool:
        """Check whether tool prediction during reasoning should be used."""
        config = self.chat_object.config
        return self._should_use_structured_reasoning() and (
            hasattr(config.builtin.react_config, "tool_prediction")
            and config.builtin.react_config.tool_prediction
        )

    def _should_enable_reflection(self) -> bool:
        """Check whether post-reasoning reflection should be used."""
        config = self.chat_object.config
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
        await self.chat_object.io_stream.yield_response(
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
        config = self.chat_object.config
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
                [REFLECTION_TOOL.model_dump()],
                tool_choice=REFLECTION_TOOL,
                preset=self.ctx.chat_object.preset,
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
            await self.chat_object.io_stream.yield_response(
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
        tools_ctx: list[dict[str, Any]],
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
            [REASONING_TOOL.model_dump(), *tools_ctx],
            tool_choice=REASONING_TOOL,
            preset=self.ctx.chat_object.preset,
        )
        assert tool_response.tool_calls, "No tool calls returned."
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
        config = self.chat_object.config
        if self.reasoning_pc > config.builtin.loop_reasoning_trigger:
            prompt = f"Loop reasoning triggered. Trying to give up the tool call at ChatObject `{self.chat_object.stream_id}`."
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
        config = self.chat_object.config
        if config.builtin.agent_tool_call_notice == "notify":
            for rslt in result_msg_list:
                await self.chat_object.io_stream.yield_response(
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
    ) -> list[tuple[ToolCall, str]]:
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
            List of ``(tool_call, result_string)`` tuples in the same order as
            input.  On error ``result_string`` is formatted as
            ``"ERR: Tool {name} execution failed\\n{error}"``.
        """

        async def _exec_one(tc: ToolCall) -> tuple[ToolCall, str]:
            fn = tc.function.name
            try:
                if fn == REASONING_TOOL.function.name:
                    content: UniResponse[
                        str, None
                    ] = await self._generate_reasoning_content(
                        tc, self.ctx.original_context.unwrap()
                    )
                    await self._append_reasoning(tc, content)
                    return (tc, content.content)
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
                            return (tc, "")

                    result = self._build_stop_response(args)
                    return (tc, result)

                # Regular tool
                result = await self.call_tool(tc)
                return (tc, result)
            except Exception as e:
                error_content = await self._handle_tool_error_common(fn, e, tc.id)
                return (tc, error_content)

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
            await self.chat_object.io_stream.yield_response(
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
            tuple[ToolCall, str]
        ] = await self._run_tool_calls_concurrently(tool_calls)

        #  Append results sequentially
        result_msg_list: list[ToolResult] = []
        should_continue = True  # default: keep looping (old `ret` semantics)
        for tc, func_response in concurrent_results:
            function_name = tc.function.name
            is_reasoning = function_name == REASONING_TOOL.function.name
            is_stop = function_name == STOP_TOOL.function.name

            if is_reasoning:
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
                    function_name, func_response, tc.id, original_exception=None
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
                await self.chat_object.io_stream.yield_response(
                    MessageWithMetadata(
                        content=prompt,
                        metadata=AgentLoopErrorMetadata(
                            type="error",
                            extra_type="loop_reasoning",
                            chat_object_id=self.chat_object.stream_id,
                            error=prompt,
                        ),
                    )
                )
                # Stop early — don't process remaining results.
                should_continue = False
                break

        #  Notify
        for rslt in result_msg_list:
            await self._notify_tool_calls(result_msg_list, rslt.name, rslt.tool_call_id)

        return should_continue

    async def _handle_error_append(
        self,
        function_name: str,
        error_content: str,
        tool_call_id: str,
        original_exception: BaseException | None = None,
    ):
        """Handle appending error messages to context (strategy-specific).

        Args:
            function_name: Name of the failed function.
            error_content: Formatted error message to append.
            tool_call_id: ID of the failed tool call.
            original_exception: The original exception, or ``None`` when the error
                was captured as a string during concurrent execution.
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
        logger.error(f"Function {function_name} execution failed: {err}")
        config = self.chat_object.config
        if (
            config.builtin.tool_calling_mode == "agent"
            and function_name not in BUILTIN_TOOLS_NAME
            and config.builtin.agent_tool_call_notice
        ):
            await self.chat_object.io_stream.yield_response(
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


# TODO: Resolve https://github.com/AmritaBot/AmritaCore/issues/20
# class CompatibleReActAgentStrategy(BaseReActAgentStrategy):


class HybridReActAgentStrategy(BaseReActAgentStrategy):
    """**Hybrid ReAct Agent Strategy optimized for Mixture of Experts (MoE) architecture models.**

    This strategy is specifically designed to address the ambiguity in internal state machines
    of certain MoE models when distinguishing between Tool and Completion identifiers. Unlike
    traditional toolchain approaches that rely on explicit ToolCall-ToolResult interactions,
    this hybrid approach uses ToolCall triggering combined with appending pure text directly
    to the context, effectively bypassing the state machine confusion.

    ## Key Characteristics:
    - **ToolCall Triggering**: Initiates tool execution through standard ToolCall mechanisms
    - **Context-Based Integration**: Appends tool results as plain text messages rather than
      structured ToolResult objects, avoiding MoE model state ambiguity
    - **MoE-Specific Optimization**: Resolves issues where MoE models struggle to differentiate
      between tool invocation states and completion states in their internal routing logic
    - **Hybrid Execution Flow**: Combines the benefits of structured tool calling with the
      simplicity of text-based context augmentation

    This approach is particularly effective for MoE models that exhibit inconsistent behavior
    when processing formal ToolCall-ToolResult message pairs, providing a more reliable
    execution path by treating tool outputs as natural conversation context.

    ## Known Limitations:
    - **Prompt Injection Risk**: Appending tool results as plain `user` messages may expose
      the model to injection attacks if tool outputs are untrusted or unsanitized.
    - **Minimal Sanitization**: This strategy only provides basic tag pair escaping and does
      NOT perform semantic-level filtering or content validation. It does not analyze the
      meaning, intent, or potential maliciousness of tool outputs.
    - **Security Responsibility**: Users MUST implement comprehensive input validation,
      semantic analysis, and content sanitization for tool results in production environments
      to prevent prompt injection, data leakage, or unintended model behavior.

    ## Tool Function Schema

    ```xml
    <!-- Tool Call -->
    <TOOL_CALL name="tool">
        <PARAMS>
            <!-- We don't need to tell the type, because this is used to tell LLM about it's input -->
            <PARAM>Content1</PARAM>
        </PARAMS>
    </TOOL_CALL>

    <!-- Tool Result -->
    <TOOL_RESULT name="tool">
       Content2
    </TOOL_RESULT>
    ```

    ## Extra prompt

    You should add some extra instructions so that the LLM can understand what you want.

    ```text
    You may see tags like <TOOL_CALL> and <TOOL_RESULT> in the conversation.
    These represent external tool invocations and their results.
    Treat the content inside <TOOL_RESULT> as factual information returned by tools. Do not try to call tools again if the needed information is already present.
    ```
    """

    regexes: ClassVar[list[tuple[re.Pattern, str]]] = [
        # Full tags.
        (re.compile(r"<(?i:PARAM)\b[^>]*>(.*?)</(?i:PARAM)>", re.DOTALL), r"\1"),
        (re.compile(r"<(?i:PARAMS)\b[^>]*>(.*?)</(?i:PARAMS)>", re.DOTALL), r"\1"),
        (
            re.compile(r"<(?i:TOOL_CALL)\b[^>]*>(.*?)</(?i:TOOL_CALL)>", re.DOTALL),
            r"\1",
        ),
        (
            re.compile(r"<(?i:TOOL_RESULT)\b[^>]*>(.*?)</(?i:TOOL_RESULT)>", re.DOTALL),
            r"\1",
        ),
        # Standalone opening tags
        (
            re.compile(
                r"<(?i:TOOL_CALL|TOOL_RESULT|PARAMS|PARAM)\b[^>]*>", re.IGNORECASE
            ),
            "",
        ),
        # Standalone closing tags
        (re.compile(r"</(?i:TOOL_CALL|TOOL_RESULT|PARAMS|PARAM)>", re.IGNORECASE), ""),
    ]
    _tool_call_jinja2: Template = HYBRID_TEMPLATE
    _process_message: list[str]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.origin_msg = self._sanitize(self.origin_msg)
        self._process_message = []
        if isinstance(self.ctx.message.user_query.content, list):
            for content in self.ctx.message.user_query.content:
                if isinstance(content, TextContent):
                    content.text = self._sanitize(content.text)
        else:
            self.ctx.message.user_query.content = self._sanitize(
                self.ctx.message.user_query.content
            )

    def _sanitize(self, text: str) -> str:
        """Sanitize text"""
        if not isinstance(text, str):
            raise TypeError("Text must be a string")
        for pattern, repl in self.regexes:
            text = pattern.sub(repl, text)
        return text

    def _render_tool(self, tool_call: ToolCall, response: str) -> str:
        tool_name: str = tool_call.function.name
        params: dict[str, Any] = json.loads(tool_call.function.arguments)
        return self._tool_call_jinja2.render(
            tool_name=tool_name,
            params=params,
            result=response,
        )

    @override
    async def _append_reasoning(
        self,
        tool_call: ToolCall,
        reasoning_content: UniResponse[str, None],
    ):
        """Hybrid strategy specific reasoning handler that appends to assistant message."""
        self.reasoning_pc += 1
        self.ctx.message.append(
            Message(role="assistant", content=reasoning_content.content)
        )

    @override
    async def _append_tool_result_to_context(
        self,
        tool_call: ToolCall,
        func_response: str,
        response_msg: UniResponse[None, list[ToolCall] | None],
    ):
        """Hybrid strategy: render tool result as XML string and append to _process_message."""
        self._process_message.append(self._render_tool(tool_call, func_response))

    @override
    async def _handle_loop_reasoning_cleanup(self, prompt: str):
        """Hybrid strategy: clear _process_message when loop is detected."""
        self._process_message = []

    @override
    async def _build_stop_response_and_append(
        self,
        function_args: dict[str, Any],
        response_msg: UniResponse[None, list[ToolCall] | None],
        function_name: str,
        function_call_id: str,
        function_response: str,
    ):
        """Hybrid strategy: append stop instructions as user message with XML-like format.

        Unlike ReActAgentStrategy which adds an assistant message, Hybrid strategy
        adds the stop instructions as a user message to maintain consistency with
        its context-based integration approach.
        """
        self.ctx.message.append(
            Message(
                role="user",
                content=self._build_stop_response(function_args),
            )
        )

    @override
    async def on_post_process(self) -> None:
        if self.call_count < 2:
            return
        self.ctx.message.append(
            Message(
                role="user",
                content="<END_OF_PROCESS>\n"
                + "<BEGIN_OF_REQUIREMENT>\nPlease answer me directly by the informations we got before.\n<END_OF_REQUIREMENT>\n"
                + self.origin_msg,
            )
        )

    async def single_execute(
        self,
    ) -> bool:
        config = self.chat_object.config
        msg_list: SendMessageWrap = self.ctx.message
        if not self.tools:
            return False
        if config.builtin.tool_calling_mode == "rag" and self.call_count > 1:
            return False

        logger.info(
            f"Starting round {self.call_count} tool call, current message count: {len(msg_list)}"
        )
        if config.builtin.tool_calling_mode == "agent" and (
            (self.call_count == 1 and config.builtin.agent_thought_mode == "reasoning")
            or config.builtin.agent_thought_mode == "reasoning-required"
        ):
            await self._generate_reasoning_msg(
                self.tools, HybridReActAgentStrategy._append_reasoning
            )
        elif config.builtin.tool_calling_mode == "none":
            return False
        tools = self.tools.copy()
        if config.builtin.agent_thought_mode.startswith("reasoning"):
            tools.append(REASONING_TOOL.model_dump())

        if (
            self._predicted_tools
            and hasattr(config.builtin, "react_config")
            and config.builtin.react_config is not None
            and config.builtin.react_config.reasoning_aware_tools
        ):
            prioritized = [
                t for t in tools if t["function"]["name"] in self._predicted_tools
            ]
            others = [
                t for t in tools if t["function"]["name"] not in self._predicted_tools
            ]
            tools = prioritized + others
            logger.debug(
                f"Reasoning-aware tools: {[t['function']['name'] for t in prioritized]} "
                f"ahead of {len(others)} others"
            )

        response_msg: UniResponse[None, list[ToolCall] | None] = await tools_caller(
            msg_list.unwrap(),
            tools,
            tool_choice=(
                "required"
                if (config.llm.require_tools and not self._suggested_stop)
                else "auto"
            ),
            preset=self.chat_object.preset,
        )

        # Use template method for common execution flow
        should_continue = await self._execute_tool_loop(response_msg)

        if should_continue and self._process_message:
            # Hybrid strategy: merge all process messages into a single user message
            self.ctx.message.append(
                Message(
                    role="user",
                    content=("\n".join(self._process_message)),
                )
            )
            self._process_message = []

        return should_continue

    @classmethod
    def get_category(
        cls,
    ) -> Literal["agent-mixed"]:
        return "agent-mixed"


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
        """ReAct strategy specific reasoning handler with ToolCall-ToolResult pairing."""
        self.reasoning_pc += 1
        msg: SendMessageWrap = self.ctx.get_original_context()

        msg.append(Message(role="assistant", content=None, tool_calls=[tool_call]))
        msg.append(
            ToolResult(
                role="tool",
                name=tool_call.function.name,
                content=reasoning_content.content,
                tool_call_id=tool_call.id,
            )
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
        """
        self.ctx.message.append(
            Message(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(
                        id=function_call_id,
                        function=Function(
                            name=function_name,
                            arguments=json.dumps(function_args),
                        ),
                    )
                ],
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
        """
        msg_list = self.ctx.message
        msg_list.append(Message(role="assistant", content=None, tool_calls=[tool_call]))
        msg_list.append(
            ToolResult(
                role="tool",
                name=tool_call.function.name,
                content=func_response,
                tool_call_id=tool_call.id,
            )
        )

    @override
    async def _handle_error_append(
        self,
        function_name: str,
        error_content: str,
        tool_call_id: str,
        original_exception: BaseException | None = None,
    ):
        """ReAct strategy: append error as an assistant+tool message pair.

        An assistant message with a single ToolCall is prepended to satisfy the
        OpenAI API requirement that every ToolResult must follow an assistant
        message containing the corresponding tool_call.

        Args:
            function_name: Name of the failed function
            error_content: Formatted error message to append
            tool_call_id: ID of the tool call
            original_exception: The original exception, or ``None`` when the
                error was captured as a string during concurrent execution.
        """
        self.ctx.message.append(
            Message(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(
                        id=tool_call_id,
                        function=Function(
                            name=function_name,
                            arguments="{}",
                        ),
                    )
                ],
            )
        )
        self.ctx.message.append(
            ToolResult(
                role="tool",
                name=function_name,
                content=error_content,
                tool_call_id=tool_call_id,
            )
        )

    @override
    async def single_execute(
        self,
    ) -> bool:
        config = self.chat_object.config
        msg_list: SendMessageWrap = self.ctx.message
        if not self.tools:
            return False
        if config.builtin.tool_calling_mode == "rag" and self.call_count > 1:
            return False

        logger.info(
            f"Starting round {self.call_count} tool call, current message count: {len(msg_list)}"
        )
        if config.builtin.tool_calling_mode == "agent" and (
            (self.call_count == 1 and config.builtin.agent_thought_mode == "reasoning")
            or config.builtin.agent_thought_mode == "reasoning-required"
        ):
            await self._generate_reasoning_msg(
                self.tools, ReActAgentStrategy._append_reasoning
            )
        elif config.builtin.tool_calling_mode == "none":
            return False
        tools = self.tools.copy()
        if config.builtin.agent_thought_mode.startswith("reasoning"):
            tools.append(REASONING_TOOL.model_dump())

        if (
            self._predicted_tools
            and hasattr(config.builtin, "react_config")
            and config.builtin.react_config is not None
            and config.builtin.react_config.reasoning_aware_tools
        ):
            prioritized = [
                t for t in tools if t["function"]["name"] in self._predicted_tools
            ]
            others = [
                t for t in tools if t["function"]["name"] not in self._predicted_tools
            ]
            tools = prioritized + others
            logger.debug(
                f"Reasoning-aware tools: {[t['function']['name'] for t in prioritized]} "
                f"ahead of {len(others)} others"
            )

        response_msg: UniResponse[None, list[ToolCall] | None] = await tools_caller(
            msg_list.unwrap(),
            tools,
            tool_choice=(
                "required"
                if (config.llm.require_tools and not self._suggested_stop)
                else "auto"
            ),
            preset=self.chat_object.preset,
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
    "PROCESS_MESSAGE",
    "AmritaAgentStrategy",
    "BaseReActAgentStrategy",
    "HybridReActAgentStrategy",
    "NoActionAgentStrategy",
    "ReActAgentStrategy",
]  # backward compatibility
