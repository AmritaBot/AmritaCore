from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, Literal

from jinja2 import Template
from typing_extensions import Self, override

from amrita_core.agent.context import StrategyContext
from amrita_core.agent.strategy import AgentStrategy
from amrita_core.builtins.consts import BUILTIN_TOOLS_NAME
from amrita_core.libchat import (
    tools_caller,
)
from amrita_core.logging import debug_log, logger
from amrita_core.protocol import MessageWithMetadata
from amrita_core.types import (
    Message,
    SendMessageWrap,
    TextContent,
    ToolCall,
    ToolResult,
    UniResponse,
)

from .tools import (
    PROCESS_MESSAGE,
    REASONING_TOOL,
    STOP_TOOL,
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
    _reasoning_template = Template(""""
    Please analyze the task requirements based on the user input above,summarize the current step's purpose and reasons, and execute accordingly.
    If no task needs to be performed, no description is needed;
    please analyze according to the character tone set in <ROLE_SETTINGS> (if present).
    {% if last_step %}
    Your previous task was:

    ```text
    {{last_step}}
    ```
    {% endif %}
    {% if original_msg %}
    <INPUT>
    {{original_msg}}
    </INPUT>
    {% endif %}
    <ROLE_SETTINGS>
    {{stg.ctx.get_original_context().train.content}}
    </ROLE_SETTINGS>
    """)

    def __init__(self, ctx: StrategyContext):
        super().__init__(ctx)
        self.tools = []
        self.origin_instruction = self.chat_object.train.content
        config = self.chat_object.config
        if config.builtin.tool_calling_mode == "agent":
            self.tools.append(STOP_TOOL.model_dump())
            if config.builtin.agent_thought_mode.startswith("reasoning"):
                self.tools.append(REASONING_TOOL.model_dump())
        self.tools.extend(self.tools_manager.tools_meta_dict().values())
        self.origin_msg: str = (
            "".join(
                chunk.text
                for chunk in ctx.original_context.user_query.content
                if isinstance(chunk, TextContent)
            )
            if isinstance(ctx.original_context.user_query.content, list)
            else ctx.original_context.user_query.content
        )

    async def _generate_reasoning_msg(
        self,
        tools_ctx: list[dict[str, Any]],
        /,
        then: Callable[
            [Self, UniResponse[None, list[ToolCall] | None]],
            Awaitable[Any],
        ],
    ):
        last_step = self.agent_last_step
        original_msg = self.origin_msg
        reasoning_msg = [
            Message(
                role="system",
                content=self._reasoning_template.render(
                    stg=self,
                    last_step=last_step,
                    original_msg=original_msg,
                ),
            ),
            *self.ctx.message.unwrap(exclude_system=True),
        ]
        response: UniResponse[None, list[ToolCall] | None] = await tools_caller(
            reasoning_msg,
            [REASONING_TOOL.model_dump(), *tools_ctx],
            tool_choice=REASONING_TOOL,
            preset=self.ctx.chat_object.preset,
        )
        await then(self, response)

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
            Tuple of (is_loop_detected, prompt_message)
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
                await self.chat_object.yield_response(
                    MessageWithMetadata(
                        content=f"Called tool {rslt.name}\n",
                        metadata={
                            "type": "function_call",
                            "function_name": function_name,
                            "is_done": True,
                            "tool_id": tool_call_id,
                            "err": None,
                        },
                    )
                )

    async def _build_stop_response_and_append(
        self,
        function_args: dict[str, Any],
        response_msg: UniResponse[None, list[ToolCall] | None],
    ):
        """Build stop response and append to message list (strategy-specific).

        Subclasses can override this to customize how the stop response is handled.
        Default implementation does nothing - subclasses should implement their own logic.

        Args:
            function_args: Arguments passed to the stop tool
            msg_list: The message list to append results to
            response_msg: The original response message
        """
        pass

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

    async def _handle_loop_reasoning_cleanup(self, prompt: str):
        """Clean up strategy-specific state when loop reasoning is detected.

        Subclasses can override this to perform cleanup operations.

        Args:
            prompt: The loop detection prompt message
        """
        pass

    async def _execute_tool_loop(
        self,
        response_msg: UniResponse[None, list[ToolCall] | None],
    ) -> bool:
        """Execute the main tool calling loop with strategy-specific behaviors.

        This is a template method that defines the common execution flow while
        delegating strategy-specific behaviors to abstract methods.

        Args:
            response_msg: The response from tools_caller containing tool calls

        Returns:
            True if execution should continue, False if it should stop
        """
        if not (tool_calls := response_msg.tool_calls):
            return False

        result_msg_list: list[ToolResult] = []
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args: dict[str, Any] = json.loads(tool_call.function.arguments)
            debug_log(f"Function arguments are {tool_call.function.arguments}")
            logger.info(f"Calling function {function_name}")
            await self.chat_object.yield_response(
                MessageWithMetadata(
                    content=f"Calling function {function_name}\n",
                    metadata={
                        "type": "function_call",
                        "function_name": function_name,
                        "is_done": False,
                        "tool_id": tool_call.id,
                    },
                )
            )

            func_response: str = ""
            try:
                match function_name:
                    case REASONING_TOOL.function.name:
                        logger.debug("Generating task summary and reason.")
                        await self._append_reasoning(response=response_msg)
                        return True
                    case STOP_TOOL.function.name:
                        self.agent_last_step = "Stopped"
                        self.reasoning_pc = 0
                        self._suggested_stop = True
                        logger.info("Agent work has been terminated.")
                        func_response = self._build_stop_response(function_args)
                        await self._build_stop_response_and_append(
                            function_args, response_msg
                        )
                    case _:
                        self.reasoning_pc = 0
                        func_response = await self.call_tool(tool_call)
                        await self._append_tool_result_to_context(
                            tool_call, func_response, response_msg
                        )
            except Exception as err:
                error_content = await self._handle_tool_error_common(
                    function_name, err, tool_call.id
                )
                # Strategy-specific error handling with original exception
                await self._handle_error_append(
                    function_name,
                    error_content,
                    tool_call.id,
                    original_exception=err,
                )
            else:
                logger.debug(f"Function {function_name} returned: {func_response}")
                msg: ToolResult = ToolResult(
                    role="tool",
                    content=func_response,
                    name=function_name,
                    tool_call_id=tool_call.id,
                )
                result_msg_list.append(msg)

            finally:
                self.call_count += 1
                prompt = self._check_and_handle_loop_reasoning()
                if prompt is not None:
                    await self._handle_loop_reasoning_cleanup(prompt)
                    await self.chat_object.yield_response(
                        MessageWithMetadata(
                            content=prompt,
                            metadata={
                                "type": "error",
                                "extra_type": "loop_reasoning",
                                "chat_object_id": self.chat_object.stream_id,
                                "content": prompt,
                            },
                        )
                    )
                    return False

            # Send tool call info to user
            await self._notify_tool_calls(result_msg_list, function_name, tool_call.id)

        return True

    async def _handle_error_append(
        self,
        function_name: str,
        error_content: str,
        tool_call_id: str,
        original_exception: BaseException,
    ):
        """Handle appending error messages to context (strategy-specific)."""
        ...

    @abstractmethod
    async def _append_reasoning(
        self, response: UniResponse[None, list[ToolCall] | None]
    ):
        """Append reasoning content to context (strategy-specific).

        Subclasses must implement this to define how reasoning results are added to context.

        Args:
            response: The response from tools_caller containing reasoning tool calls
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
            await self.chat_object.yield_response(
                MessageWithMetadata(
                    content=f"Error: {function_name} failed.",
                    metadata={
                        "type": "function_call",
                        "function_name": function_name,
                        "is_done": True,
                        "tool_id": tool_call_id,
                        "err": err,
                    },
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
    _tool_call_jinja2: Template = Template("""<TOOL_CALL name="{{tool_name}}">
        <PARAMS>
            {% for key,value in params.items() %}
            <PARAM name="{{key}}">{{value}}</PARAM>
            {% endfor %}
        </PARAMS>
    </TOOL_CALL>
    <TOOL_RESULT name="{{tool_name}}">
    {{result}}
    </TOOL_RESULT>""")
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

    async def _append_reasoning(
        self, response: UniResponse[None, list[ToolCall] | None]
    ):
        """Hybrid strategy specific reasoning handler that appends to assistant message."""
        self.reasoning_pc += 1
        tool_calls: list[ToolCall] | None = response.tool_calls
        if tool_calls:
            for tool in tool_calls:
                if tool.function.name == REASONING_TOOL.function.name:
                    break
            else:
                raise ValueError(f"No reasoning tool found in response \n\n{response}")

            args = json.loads(tool.function.arguments)
            if reasoning := args.get("content"):
                self.agent_last_step = reasoning
                content: str = reasoning
                self.ctx.message.append(Message(role="assistant", content=content))
                logger.debug(f"[AmritaAgent] {reasoning}")
                if not self.chat_object.config.builtin.agent_reasoning_hide:
                    await self.chat_object.yield_response(
                        response=MessageWithMetadata(
                            content=content,
                            metadata={"type": "reasoning", "content": reasoning},
                        )
                    )
            else:
                raise ValueError("Reasoning tool has no content!")

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

        response_msg: UniResponse[None, list[ToolCall] | None] = await tools_caller(
            msg_list.unwrap(),
            self.tools,
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

    async def _append_reasoning(
        self, response: UniResponse[None, list[ToolCall] | None]
    ):
        """ReAct strategy specific reasoning handler with ToolCall-ToolResult pairing."""
        self.reasoning_pc += 1
        msg: SendMessageWrap = self.ctx.get_original_context()

        tool_calls: list[ToolCall] | None = response.tool_calls
        if tool_calls:
            for tool in tool_calls:
                if tool.function.name == REASONING_TOOL.function.name:
                    break
            else:
                raise ValueError(f"No reasoning tool found in response \n\n{response}")
            if reasoning := json.loads(tool.function.arguments).get("content"):
                msg.append(Message.model_validate(response, from_attributes=True))
                msg.append(
                    ToolResult(
                        role="tool",
                        name=tool.function.name,
                        content=reasoning,
                        tool_call_id=tool.id,
                    )
                )
                self.agent_last_step = reasoning
                logger.debug(f"[AmritaAgent] {reasoning}")
                if not self.chat_object.config.builtin.agent_reasoning_hide:
                    await self.chat_object.yield_response(
                        response=MessageWithMetadata(
                            content=f"<think>\n{reasoning}\n</think>",
                            metadata={"type": "reasoning", "content": reasoning},
                        )
                    )
            else:
                raise ValueError("Reasoning tool has no content!")

    @override
    async def _build_stop_response_and_append(
        self,
        function_args: dict[str, Any],
        response_msg: UniResponse[None, list[ToolCall] | None],
    ):
        """ReAct strategy: append assistant message before stop."""
        self.ctx.message.append(
            Message.model_validate(response_msg, from_attributes=True)
        )

    @override
    async def _append_tool_result_to_context(
        self,
        tool_call: ToolCall,
        func_response: str,
        response_msg: UniResponse[None, list[ToolCall] | None],
    ):
        """ReAct strategy: append both assistant message and tool result as a pair.

        This follows OpenAI's ToolCall-ToolResult pairing requirement where every
        assistant message with tool_calls must be followed by corresponding tool messages.
        """
        # First, append the assistant message containing the tool_calls
        msg_list = self.ctx.message
        msg_list.append(Message.model_validate(response_msg, from_attributes=True))
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
        original_exception: BaseException,
    ):
        """ReAct strategy: append error as ToolResult with optional exception context.

        The original_exception parameter allows for advanced error handling strategies,
        such as different recovery behaviors based on exception type (e.g., retry on
        timeout, abort on authentication errors).

        Args:
            function_name: Name of the failed function
            error_content: Formatted error message to append
            tool_call_id: ID of the tool call
            original_exception: The original exception object for type-based handling
        """
        self.ctx.message.append(
            ToolResult(
                role="tool",
                name=function_name,
                content=error_content,
                tool_call_id=tool_call_id,
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
                self.tools, ReActAgentStrategy._append_reasoning
            )
        elif config.builtin.tool_calling_mode == "none":
            return False
        response_msg: UniResponse[None, list[ToolCall] | None] = await tools_caller(
            msg_list.unwrap(),
            self.tools,
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

__all__ = ["PROCESS_MESSAGE"]  # backward compatibility
