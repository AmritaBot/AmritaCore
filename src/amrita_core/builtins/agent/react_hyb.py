from __future__ import annotations

import json
import re
from typing import Any, ClassVar, Literal

from amrita_sense.logging import logger
from jinja2 import Template
from typing_extensions import override

from amrita_core.libchat import tools_caller
from amrita_core.tools.models import ToolFunctionSchema
from amrita_core.types import (
    Function,
    Message,
    SendMessageWrap,
    TextContent,
    ToolCall,
    ToolResult,
    UniResponse,
)

from ..consts import HYBRID_TEMPLATE
from ..tools import REASONING_TOOL
from .react_base import BaseReActAgentStrategy


def _resolve_tool_name(tool: ToolFunctionSchema | dict) -> str:
    """Resolve the function name from a tool schema (object or dict form)."""
    if isinstance(tool, dict):
        return tool.get("function", {}).get("name", "")
    return tool.function.name


class HybridReActAgentStrategy(BaseReActAgentStrategy):
    """**DEPRECATED** — Hybrid ReAct Agent Strategy.

    .. deprecated::
        This strategy cannot faithfully model ``reasoning_content`` (it appends
        reasoning as plain assistant text, which bypasses thinking filters and
        leaks reasoning into the model context). Prefer :class:`ReActAgentStrategy`,
        which stores reasoning in ``Message.reasoning_content``. Kept only for
        backward compatibility; it may be removed in a future release.

    **Hybrid ReAct Agent Strategy optimized for Mixture of Experts (MoE) architecture models.**

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.origin_msg = self._sanitize(self.origin_msg)
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
        """Hybrid strategy reasoning handler with ToolCall-ToolResult pairing.

        Reasoning is stored in ``Message.reasoning_content`` (never in
        ``content``) so that thinking-mode providers receive it back verbatim
        and the thinking filter can strip it when configured to.
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
    async def _append_tool_result_to_context(
        self,
        tool_call: ToolCall,
        func_response: str,
        response_msg: UniResponse[None, list[ToolCall] | None],
    ):
        """Hybrid strategy: render tool result as XML, paired with the call.

        The XML-rendered text lives in the ``ToolResult.content`` — keeping the
        MoE-friendly text style while satisfying the OpenAI-compatible
        ToolCall-ToolResult pairing requirement.
        """
        reasoning = response_msg.reasoning_content if response_msg else None
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
                content=self._render_tool(tool_call, func_response),
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
        """Hybrid strategy: append stop instructions as a paired tool message.

        Unlike the old plain-text injection, the stop response is appended as
        a ToolCall-ToolResult pair (XML style kept in the result content) to
        satisfy the OpenAI-compatible pairing requirement.
        """
        reasoning = response_msg.reasoning_content if response_msg else None
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
                reasoning_content=reasoning,
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
                self.tools, HybridReActAgentStrategy._append_reasoning
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

        # Use template method for common execution flow.
        # Tool results were already appended as paired assistant + tool
        # messages inside _execute_tool_loop.
        return await self._execute_tool_loop(response_msg)

    @classmethod
    def get_category(
        cls,
    ) -> Literal["agent-mixed"]:
        return "agent-mixed"


__all__ = [
    "HybridReActAgentStrategy",
]
