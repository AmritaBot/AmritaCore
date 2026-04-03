"""
Unit tests for AmritaCore Agent Strategy system.

This module tests the new Agent Strategy architecture including:
- AgentStrategy abstract base class
- ReActAgentStrategy implementation
- StrategyContext data class
- Built-in constants and tools
"""

from typing import Literal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amrita_core.agent.context import StrategyContext
from amrita_core.agent.strategy import AgentStrategy, NoExceptionHandler
from amrita_core.builtins.agent import ReActAgentStrategy
from amrita_core.builtins.consts import (
    AGENT_PROCESS_TOOLS,
    BUILTIN_TOOLS_NAME,
)
from amrita_core.builtins.tools import (
    PROCESS_MESSAGE,
    REASONING_TOOL,
    STOP_TOOL,
)
from amrita_core.chatmanager import ChatObject
from amrita_core.config import AmritaConfig, FunctionConfig, LLMConfig, set_config
from amrita_core.protocol import MessageWithMetadata
from amrita_core.tools.manager import ToolsManager
from amrita_core.types import (
    Message,
    SendMessageWrap,
    TextContent,
)


@pytest.fixture(autouse=True)
def setup_global_config():
    """Initialize global configuration before each test."""
    set_config(AmritaConfig())


@pytest.fixture
def mock_config():
    """Create a mock AmritaConfig for testing."""
    config = AmritaConfig()
    config.function_config = FunctionConfig()
    config.llm = LLMConfig()
    return config


@pytest.fixture
def mock_chat_object(mock_config):
    """Create a mock ChatObject for testing."""
    chat_obj = MagicMock(spec=ChatObject)
    chat_obj.session_id = "test-session"
    chat_obj.preset = "default-preset"
    chat_obj.config = mock_config
    chat_obj.yield_response = AsyncMock()
    chat_obj.set_queue_done = AsyncMock()
    return chat_obj


@pytest.fixture
def create_send_message_wrap():
    """Factory fixture to create SendMessageWrap instances."""

    def _create(train_content="System message", user_content="test user input"):
        train_msg = Message(role="system", content=train_content)
        user_msg = Message(role="user", content=user_content)
        memory = [user_msg]
        return SendMessageWrap(
            train=train_msg,
            memory=memory,  # type: ignore
            user_query=user_msg,
        )

    return _create


@pytest.fixture
def mock_strategy_context(mock_chat_object, create_send_message_wrap):
    """Create a mock StrategyContext for testing."""
    original_context = create_send_message_wrap()
    return StrategyContext(
        user_input="test user input",
        original_context=original_context,
        chat_object=mock_chat_object,
    )


def test_builtin_tools_constants():
    """Test that built-in tools constants are properly defined."""
    # Test BUILTIN_TOOLS_NAME set
    assert len(BUILTIN_TOOLS_NAME) == 3
    assert isinstance(BUILTIN_TOOLS_NAME, set)
    expected_names = {
        STOP_TOOL.function.name,
        REASONING_TOOL.function.name,
        PROCESS_MESSAGE.function.name,
    }
    assert BUILTIN_TOOLS_NAME == expected_names

    # Test AGENT_PROCESS_TOOLS tuple
    assert len(AGENT_PROCESS_TOOLS) == 3
    assert isinstance(AGENT_PROCESS_TOOLS, tuple)
    assert AGENT_PROCESS_TOOLS == (REASONING_TOOL, STOP_TOOL, PROCESS_MESSAGE)


def test_strategy_context_properties(mock_strategy_context):
    """Test StrategyContext properties and methods."""
    ctx = mock_strategy_context

    # Test message property
    assert ctx.message == ctx.original_context

    # Test get_original_context method
    assert ctx.get_original_context() == ctx.original_context

    # Test get_user_input method
    assert ctx.get_user_input() == "test user input"

    # Test message setter with validation
    train_msg = Message(role="system", content="New system")
    user_msg = Message(role="user", content="New user")
    new_context = SendMessageWrap(
        train=train_msg, memory=[user_msg], user_query=user_msg
    )
    ctx.message = new_context
    assert ctx.original_context == new_context

    # Test message setter with invalid type
    with pytest.raises(TypeError, match="message must be of type SendMessageWrap"):
        ctx.message = "invalid type"


class ConcreteAgentStrategyForTesting(AgentStrategy):
    """Concrete implementation of AgentStrategy for testing abstract methods."""

    async def single_execute(self) -> bool:
        return False

    async def run(self) -> None:
        pass

    @classmethod
    def get_category(cls) -> Literal["workflow"]:
        return "workflow"


def test_agent_strategy_initialization(mock_strategy_context):
    """Test AgentStrategy initialization and attribute setup."""
    strategy = ConcreteAgentStrategyForTesting(mock_strategy_context)

    # Test attributes are set correctly
    assert strategy.ctx == mock_strategy_context
    assert strategy.chat_object == mock_strategy_context.chat_object
    assert strategy.session is None  # No session in mock
    assert isinstance(strategy.tools_manager, ToolsManager)


def test_amrita_agent_strategy_initialization(mock_strategy_context):
    """Test ReActAgentStrategy initialization."""
    strategy = ReActAgentStrategy(mock_strategy_context)

    # Test attributes specific to ReActAgentStrategy
    assert strategy.agent_last_step is None
    assert strategy.call_count == 1
    assert isinstance(strategy.tools, list)
    assert strategy.origin_msg == "test user input"


def test_amrita_agent_strategy_category():
    """Test that ReActAgentStrategy returns correct category."""
    assert ReActAgentStrategy.get_category() == "agent-mixed"


@pytest.mark.asyncio
async def test_agent_strategy_on_limited(mock_strategy_context):
    """Test AgentStrategy.on_limited method."""
    strategy = ConcreteAgentStrategyForTesting(mock_strategy_context)

    # Call on_limited
    await strategy.on_limited()

    # Verify message was appended to context
    assert len(mock_strategy_context.original_context.end_messages) == 1
    appended_message = mock_strategy_context.original_context.end_messages[0]
    assert isinstance(appended_message, Message)
    assert appended_message.role == "user"
    assert "Too much tools called occurred" in appended_message.content

    # Verify response was yielded
    mock_strategy_context.chat_object.yield_response.assert_called_once()
    yielded_response = mock_strategy_context.chat_object.yield_response.call_args[0][0]
    assert isinstance(yielded_response, MessageWithMetadata)
    assert (
        "[AmritaAgent] Too many tool calls! Workflow terminated!"
        in yielded_response.content
    )


@pytest.mark.asyncio
async def test_agent_strategy_on_exception(mock_strategy_context):
    """Test AgentStrategy.on_exception method."""
    strategy = ConcreteAgentStrategyForTesting(mock_strategy_context)
    with pytest.raises(NoExceptionHandler):
        await strategy.on_exception(Exception())


def test_strategy_context_with_complex_user_input(create_send_message_wrap):
    """Test StrategyContext with complex user input containing TextContent."""
    # Create user message with TextContent
    user_content = [TextContent(type="text", text="Complex user input")]
    user_msg = Message(role="user", content=user_content)
    train_msg = Message(role="system", content="System message")

    original_context = SendMessageWrap(
        train=train_msg, memory=[user_msg], user_query=user_msg
    )

    mock_chat_obj = MagicMock(spec=ChatObject)
    mock_chat_obj.session_id = "test-session"
    mock_chat_obj.preset = "default-preset"
    mock_chat_obj.config = AmritaConfig()

    ctx = StrategyContext(
        user_input=user_content,
        original_context=original_context,
        chat_object=mock_chat_obj,
    )

    # Test that origin_msg is correctly extracted
    strategy = ReActAgentStrategy(ctx)
    assert strategy.origin_msg == "Complex user input"


@pytest.mark.asyncio
async def test_amrita_agent_strategy_single_execute_no_tools(
    mock_strategy_context, mock_config
):
    """Test ReActAgentStrategy single_execute with no tools available."""
    # Configure to have no tools
    mock_config.builtin.tool_calling_mode = "none"
    mock_strategy_context.chat_object.config = mock_config

    strategy = ReActAgentStrategy(mock_strategy_context)
    strategy.tools = []  # No tools available

    result = await strategy.single_execute()
    assert result is False


@pytest.mark.asyncio
async def test_amrita_agent_strategy_single_execute_with_tool_calls(
    mock_strategy_context, mock_config
):
    """Test ReActAgentStrategy single_execute with successful tool calls."""
    from amrita_core.types import ToolCall, UniResponse

    # Configure for agent mode
    mock_config.builtin.tool_calling_mode = "agent"
    mock_config.builtin.agent_thought_mode = "none"
    mock_config.llm.require_tools = False
    mock_strategy_context.chat_object.config = mock_config

    # Mock tools_caller to return tool calls
    mock_response = UniResponse(
        content=None,
        tool_calls=[
            ToolCall(
                id="tool1",
                function={"name": "test_tool", "arguments": '{"param": "value"}'},  # pyright: ignore[reportArgumentType]
            )
        ],
        usage=None,
    )

    with patch("amrita_core.builtins.agent.tools_caller", return_value=mock_response):
        strategy = ReActAgentStrategy(mock_strategy_context)
        fun = strategy.tools_manager.get_tool
        try:
            # Add a mock tool
            strategy.tools = [{"name": "test_tool", "description": "Test tool"}]

            # Mock the tools manager to return a tool
            mock_tool_data = MagicMock()
            mock_tool_data.custom_run = False
            mock_tool_data.func = AsyncMock(return_value="Tool result")
            strategy.tools_manager.get_tool = MagicMock(return_value=mock_tool_data)

            result = await strategy.single_execute()
            assert result is True
            assert strategy.call_count == 2  # Should be incremented
        finally:
            strategy.tools_manager.get_tool = fun


@pytest.mark.asyncio
async def test_amrita_agent_strategy_single_execute_stop_tool(
    mock_strategy_context, mock_config
):
    """Test ReActAgentStrategy single_execute with STOP tool."""
    from amrita_core.types import ToolCall, UniResponse

    # Configure for agent mode
    mock_config.builtin.tool_calling_mode = "agent"
    mock_config.builtin.agent_thought_mode = "none"
    mock_strategy_context.chat_object.config = mock_config

    # Mock tools_caller to return STOP tool call
    mock_response = UniResponse(
        content=None,
        tool_calls=[
            ToolCall(
                id="stop1",
                function={"name": "stop", "arguments": '{"result": "Work completed"}'},  # pyright: ignore[reportArgumentType]
            )
        ],
        usage=None,
    )

    with patch("amrita_core.builtins.agent.tools_caller", return_value=mock_response):
        strategy = ReActAgentStrategy(mock_strategy_context)
        strategy.tools = [STOP_TOOL.model_dump()]

        result = await strategy.single_execute()
        assert result is True


@pytest.mark.asyncio
async def test_amrita_agent_strategy_single_execute_tool_error(
    mock_strategy_context, mock_config
):
    """Test ReActAgentStrategy single_execute with tool execution error."""
    from amrita_core.types import ToolCall, UniResponse

    # Configure for agent mode with error notification
    mock_config.builtin.tool_calling_mode = "agent"
    mock_config.builtin.agent_tool_call_notice = True
    mock_strategy_context.chat_object.config = mock_config

    # Mock tools_caller to return tool call
    mock_response = UniResponse(
        content=None,
        tool_calls=[
            ToolCall(
                id="tool1",
                function={"name": "failing_tool", "arguments": '{"param": "value"}'},  # pyright: ignore[reportArgumentType]
            )
        ],
        usage=None,
    )

    # Instead of mocking get_tool globally, we'll create a temporary tool registration
    # that will be cleaned up after the test
    from amrita_core.tools.manager import ToolsManager
    from amrita_core.tools.models import (
        FunctionDefinitionSchema,
        FunctionParametersSchema,
        ToolData,
        ToolFunctionSchema,
    )

    # Register a real failing tool for this test only
    def failing_tool_func(params):
        raise RuntimeError("Tool failed")

    failing_tool_def = FunctionDefinitionSchema(
        name="failing_tool",
        description="A tool that always fails",
        parameters=FunctionParametersSchema(type="object", properties={}),
    )

    failing_tool_data = ToolData(
        func=failing_tool_func,
        data=ToolFunctionSchema(
            function=failing_tool_def, type="function", strict=False
        ),
        custom_run=False,
    )

    manager = ToolsManager()
    manager.register_tool(failing_tool_data)

    try:
        with patch(
            "amrita_core.builtins.agent.tools_caller", return_value=mock_response
        ):
            strategy = ReActAgentStrategy(mock_strategy_context)
            strategy.tools = [{"name": "failing_tool", "description": "Failing tool"}]

            result = await strategy.single_execute()
            assert result is True
            assert strategy.call_count == 2  # Should be incremented even on error
    finally:
        # Clean up the registered tool
        manager.remove_tool("failing_tool")
