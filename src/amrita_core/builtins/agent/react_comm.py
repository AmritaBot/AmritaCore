from __future__ import annotations

import json
from typing import Any, Literal

from amrita_sense.logging import logger
from typing_extensions import override

from amrita_core.libchat import tools_caller
from amrita_core.tools.models import ToolFunctionSchema
from amrita_core.types import (
    Function,
    Message,
    SendMessageWrap,
    ToolCall,
    ToolResult,
    UniResponse,
)

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
