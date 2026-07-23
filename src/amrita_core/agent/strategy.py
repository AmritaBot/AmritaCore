from __future__ import annotations

import json
import typing
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Literal

from typing_extensions import Self

from amrita_core.agent.context import StrategyContext
from amrita_core.contents import MessageMetadataPayloadSystem, MessageWithMetadata
from amrita_core.tools.models import ToolContext
from amrita_core.types import Message, ToolCall

if TYPE_CHECKING:
    from amrita_sense.streaming import SuspendObjectStream

    from amrita_core.chatmanager import ChatObject
    from amrita_core.config import AmritaConfig
    from amrita_core.tools.manager import MultiToolsManager
    from amrita_core.types.preset import ModelPreset
    from amrita_core.types.response import UniResponseUsage


class NoExceptionHandler(Exception):
    """Raised by strategies that intentionally do not handle exceptions."""

    pass


class _StrategyBase(ABC):
    """Shared execution logic for AgentStrategy and StrategyLikedObject, which
    differ only in how the context is injected (``__init__`` vs ``__call__``)."""

    tools_manager: MultiToolsManager
    chat_object: ChatObject  # deprecated — use the convenience properties below
    ctx: StrategyContext

    # Convenience properties — prefer StrategyContext DI fields,
    # fall back to chat_object for backward compatibility.

    @property
    def preset(self) -> ModelPreset:
        """Model preset, resolved from StrategyContext or chat_object."""
        if self.ctx.preset is not None:
            return self.ctx.preset
        return self.chat_object.preset

    @property
    def config(self) -> AmritaConfig:
        """Config, resolved from StrategyContext or chat_object."""
        if self.ctx.config is not None:
            return self.ctx.config
        return self.chat_object.config

    @property
    def io_stream(self) -> SuspendObjectStream:
        """I/O stream, resolved from StrategyContext or chat_object."""
        if self.ctx.io_stream is not None:
            return self.ctx.io_stream
        return self.chat_object.io_stream

    @property
    def train_content(self) -> str:
        """Training/system prompt content, resolved from StrategyContext or chat_object."""
        if self.ctx.train_content is not None:
            return self.ctx.train_content
        return self.chat_object.train.content

    @property
    def stream_id(self) -> str:
        """Stream ID, resolved from StrategyContext or chat_object."""
        if self.ctx.stream_id is not None:
            return self.ctx.stream_id
        return self.chat_object.stream_id

    @property
    def resp_extra_usage(self) -> UniResponseUsage:
        """Extra usage accumulator, resolved from StrategyContext or chat_object.

        Raises:
            RuntimeError: If neither source provides ``resp_extra_usage``.
        """
        if self.ctx.resp_extra_usage is not None:
            return self.ctx.resp_extra_usage
        if self.chat_object is not None:
            return self.chat_object._di_resp.extra_usage
        raise RuntimeError(
            "resp_extra_usage is not available in StrategyContext or chat_object"
        )

    @resp_extra_usage.setter
    def resp_extra_usage(self, value: UniResponseUsage) -> None:
        if self.ctx.resp_extra_usage is not None:
            self.ctx.resp_extra_usage = value
        elif self.chat_object is not None:
            self.chat_object._di_resp.extra_usage = value
        else:
            raise RuntimeError(
                "Cannot set resp_extra_usage: neither StrategyContext nor "
                "chat_object provide a backing storage"
            )

    # _bind — populate runtime references from StrategyContext

    def _bind(self, ctx: StrategyContext) -> None:
        self.ctx = ctx
        # Legacy path — ctx.chat_object may be None in new-style DI workflows
        self.chat_object = ctx.chat_object  # pyright: ignore[reportAttributeAccessIssue]
        # tools_manager: prefer ctx field, fallback to chat_object
        if ctx.tools_manager is not None:
            self.tools_manager = ctx.tools_manager
        elif ctx.chat_object is not None:
            self.tools_manager = ctx.chat_object.state.ability.tools

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
        await self.io_stream.yield_response(
            MessageWithMetadata(
                content="[AmritaAgent] Too many tool calls! Workflow terminated!",
                metadata=MessageMetadataPayloadSystem(
                    type="system",
                    message="[AmritaAgent] Too many tool calls! Workflow terminated!",
                    extra_type="tool_call_limit",
                ),
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
        pass

    async def on_post_process(self) -> None:
        """Used to process after all steps are completed successfully"""
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


class StrategyLikedObject(_StrategyBase, ABC):
    """Abstract base class for agent strategy **instances**.

    Unlike ``AgentStrategy`` which receives a **type** (``type[AgentStrategy]``)
    and is instantiated by the framework for every request, **StrategyLikedObject
    is passed directly as an already-initialised instance** into
    :class:`ChatObject`.  This means the strategy object can carry its own
    internal state machine, pre-configured parameters, and resources without
    relying on class-level attributes or global state.

    The framework invokes the strategy by calling ``strategy(ctx)`` once the
    execution context is ready, which populates :attr:`ctx`, :attr:`chat_object`,
    :attr:`session`, and :attr:`tools_manager`.  From that point onward the same
    instance is used for the lifetime of the conversation, guaranteeing perfect
    isolation between concurrent dialogs.

    Different strategy categories have different execution patterns:

    - ``'agent'``: Uses :meth:`single_execute` for step-by-step tool calling,
      managed by the framework.
    - ``'rag'``: Uses :meth:`run` with minimal context (only system message and
      user query).
    - ``'workflow'``: Uses :meth:`run` with full manual control over tool
      calling and context management.
    - ``'agent-mixed'``: Uses :meth:`single_execute` but can handle both RAG
      and Agent modes dynamically.

    .. note::

       **Relationship with AgentStrategy**

       :class:`AgentStrategy` remains the preferred choice when a strategy is
       stateless and can be described purely by a class.  :class:`ChatObject`
       accepts both a ``StrategyLikedObject`` instance and an
       ``AgentStrategy`` **type**; the latter is simply instantiated on first
       use to preserve backward compatibility.

    Attributes:
        session: The session data associated with the current chat session, or
            ``None`` if not available.
        tools_manager: Manager for handling available tools in the current
            context.
        chat_object: The chat object for yielding responses and managing the
            conversation flow.
        ctx: The strategy context containing execution parameters and
            configuration.
    """

    def __call__(self, ctx: StrategyContext) -> Self:
        """Populate runtime context.

        Called once by the framework when the execution context is ready.
        Subclasses may override this to perform additional initialisation, but
        **must** call ``super().__call__(ctx)`` first.
        """
        self._bind(ctx)
        return self


class AgentStrategy(_StrategyBase, ABC):
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

    def __init__(self, ctx: StrategyContext) -> None:
        """
        Initialize the agent strategy with the provided context.

        Args:
            ctx: StrategyContext containing chat_object, configuration, and message context
        """
        self._bind(ctx)
