from __future__ import annotations

import json
import typing
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Literal

from amrita_core.agent.context import StrategyContext
from amrita_core.protocol import MessageWithMetadata
from amrita_core.sessions import SessionData, SessionsManager
from amrita_core.tools.manager import ToolsManager
from amrita_core.tools.models import ToolContext
from amrita_core.types import Message, ToolCall

if TYPE_CHECKING:
    from amrita_core.chatmanager import ChatObject
    from amrita_core.tools.manager import MultiToolsManager


class NoExceptionHandler(Exception):
    """Raised by strategies that intentionally do not handle exceptions."""

    pass


class AgentStrategy(ABC):
    """
    Abstract base class for agent strategies that define how an agent should execute its workflow.

    This class provides a unified interface for different types of agent execution strategies,
    allowing the system to support various agent patterns (basic tool calling, RAG, complex workflows).

    This strategy is executed after the PreCompletionEvent hook has completed, as part of the
    AgentWorkflow execution phase.

    The strategy is initialized with a context containing all necessary information for execution,
    including chat object, configuration, and message context.

    Different strategy categories have different execution patterns:
    - 'agent': Uses single_execute() method for step-by-step tool calling, managed by the framework
    - 'rag': Uses run() method with minimal context (only system message and user query)
    - 'workflow': Uses run() method with full manual control over tool calling and context management
    - 'agent-mixed': Uses single_execute() method but can handle both RAG and Agent modes dynamically

    Attributes:
        session: The session data associated with the current chat session, or None if not available
        tools_manager: Manager for handling available tools in the current context
        chat_object: The chat object for yielding responses and managing the conversation flow
        ctx: The strategy context containing execution parameters and configuration
    """

    session: SessionData | None = None
    tools_manager: "MultiToolsManager"
    chat_object: "ChatObject"
    ctx: StrategyContext

    def __init__(self, ctx: StrategyContext) -> None:
        """
        Initialize the agent strategy with the provided context.

        Args:
            ctx: StrategyContext containing chat_object, configuration, and message context
        """
        self.ctx = ctx
        self.chat_object = ctx.chat_object
        session_id = ctx.chat_object.session_id
        self.session = SessionsManager().get_session_data(session_id, None)
        self.tools_manager = self.session.tools if self.session else ToolsManager()

    async def single_execute(
        self,
    ) -> bool:
        """
        Execute a single agent step for 'agent' and 'agent-mixed' category strategies.

        This method is called by the framework to perform one iteration of tool calling.
        The framework handles the loop management, call counting, and termination conditions.

        For 'agent' category strategies, this method should:
        - Process the current message context
        - Make tool calls as needed
        - Return True to continue execution, False to stop

        For 'agent-mixed' category strategies, this method should:
        - Dynamically determine whether to operate in RAG mode or Agent mode based on context
        - Handle both retrieval-augmented generation and iterative tool calling within the same execution flow
        - Return True to continue execution, False to stop

        Returns:
            True if should continue to next execution, False to stop.

        Note:
            This method is used by 'agent' and 'agent-mixed' category strategies.
            'rag' and 'workflow' category strategies should implement run() instead.
        """
        raise NotImplementedError

    async def run(self) -> None:
        """
        Run the complete agent strategy for 'rag' and 'workflow' category strategies.

        This method gives full control to the strategy implementation for managing:
        - Tool calling iterations and limits
        - Context construction and management
        - Error handling and recovery
        - Response generation and streaming

        Category-specific behavior:
        - 'rag': Should use minimal context containing only system message and user query,
                 without historical conversation context. Typically performs retrieval and
                 generates a single response without iterative tool calling.
        - 'workflow': Has complete manual control over everything including tool calling
                     times management, context building, and execution flow. Can implement
                      complex multi-step workflows with custom logic.

        Note:
            This method is used by 'rag' and 'workflow' category strategies.
            'agent' and 'agent-mixed' category strategies should implement single_execute() instead.
        """
        raise NotImplementedError

    async def call_tool(self, tool_call: ToolCall) -> str:
        """Execute a single tool call without modifying the agent's context.

        This is a one-step tool execution that processes the given tool call
        and returns its response. It does not alter the agent's internal state
        or context beyond what the tool itself might do through the provided
        ToolContext.

        Args:
            tool_call (ToolCall): The ToolCall object containing the function name and arguments

        Raises:
            RuntimeError: If the requested tool is not found in the tools manager

        Returns:
            str: The string response from the tool execution, or a default message if the tool returns None
        """
        function_name = tool_call.function.name
        function_args: dict[str, Any] = json.loads(tool_call.function.arguments)
        if (tool_data := self.tools_manager.get_tool(function_name)) is not None:
            if not tool_data.custom_run:
                func_response: str | None = await typing.cast(
                    Callable[[dict[str, Any]], Awaitable[str]],
                    tool_data.func,
                )(function_args)
            elif (
                func_response := await typing.cast(
                    Callable[[ToolContext], Awaitable[str | None]],
                    tool_data.func,
                )(
                    ToolContext(
                        data=function_args,
                        ctx=self.ctx,
                    )
                )
            ) is None:
                func_response = "(this tool returned no content)"
            return func_response
        else:
            raise RuntimeError("Received unexpected tool call")

    async def on_limited(self) -> None:
        """
        Handle the event when the agent reaches its tool calling limit.

        This method is called when the agent strategy has reached the maximum allowed number of tool calls
        as configured by the framework. It provides a callback mechanism to handle special behavior or
        actions required when the tool usage limit is exceeded.

        Common use cases include:
        - Sending a notification message to the user about the limit being reached
        - Providing alternative responses without further tool calls
        - Logging the limit event for monitoring purposes

        Note:
            This method is used by 'agent' and 'agent-mixed' category strategies.
            'rag' and 'workflow' category strategies should implement run() instead.
        """
        await self.chat_object.yield_response(
            MessageWithMetadata(
                content="[AmritaAgent] Too many tool calls! Workflow terminated!",
                metadata={
                    "type": "system",
                    "message": "[AmritaAgent] Too many tool calls! Workflow terminated!",
                    "extra_type": "tool_call_limit",
                },
            )
        )
        self.ctx.original_context.append(
            Message(
                role="user",
                content="Too much tools called occurred,please call later or follow user's instruction."
                + "Now please continue to completion and NOT to call ANY tools.",
            )
        )

    async def on_exception(self, exc: BaseException) -> None:
        raise NoExceptionHandler

    async def on_post_process(self) -> None:
        """Used to process after all steps(Only when successful and in agent/agent-mixed mode)"""
        pass

    @classmethod
    @abstractmethod
    def get_category(cls) -> Literal["agent", "workflow", "rag", "agent-mixed"]:
        """
        Get the category of the agent strategy.

        The category determines how the strategy is executed by the framework:

        - "agent": Framework-managed iterative execution using single_execute().
                   The framework handles the execution loop, call counting, and termination.
                   Strategy focuses on single-step logic. Best for standard tool-calling agents.

        - "rag": Minimal-context execution using run(). Only receives system message and
                 user query without conversation history. Designed for Retrieval-Augmented
                 Generation scenarios where external knowledge retrieval is the primary function.

        - "agent-mixed": Mixed-mode execution using single_execute(). Can handle both RAG and Agent modes.
                         Dynamically switches between retrieval-augmented generation and iterative
                         tool calling based on the current context and requirements. Provides
                         flexibility to adapt execution strategy during runtime.

        - "workflow": Full manual control using run(). Strategy manages everything including
                      tool calling limits, context construction, and execution flow. Suitable
                      for complex multi-step workflows with custom orchestration logic.

        Returns:
            The strategy category as a literal string indicating execution pattern.
        """
        ...
