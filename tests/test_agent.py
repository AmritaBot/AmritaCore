from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amrita_core.builtins.agent import (
    AGENT_PROCESS_TOOLS,
    BUILTIN_TOOLS_NAME,
    agent_core,
    cookie,
)
from amrita_core.chatmanager import ChatObject
from amrita_core.config import AmritaConfig, FunctionConfig
from amrita_core.hook.event import CompletionEvent, PreCompletionEvent
from amrita_core.protocol import MessageWithMetadata
from amrita_core.tools.models import ToolData
from amrita_core.types import (
    Function,
    Message,
    ToolCall,
    UniResponse,
)


@pytest.fixture
def mock_config():
    config = AmritaConfig()
    config.function_config = FunctionConfig()
    return config


@pytest.fixture
def mock_event():
    event: PreCompletionEvent = MagicMock(spec=PreCompletionEvent)
    event.chat_object = MagicMock(spec=ChatObject)
    event.chat_object.session_id = "test-session"
    event.chat_object.preset = "default-preset"
    event.message = MagicMock()
    event.message.train = Message(role="system", content="System message")
    event.message.user_query = Message(role="user", content="User query")
    event.message.unwrap = MagicMock(
        return_value=[
            Message(role="system", content="System message"),
            Message(role="user", content="User query"),
        ]
    )
    event.original_context = "Original context"
    event.get_context_messages = MagicMock()
    event.get_context_messages.return_value = MagicMock()
    event.get_context_messages.return_value.train = MagicMock()
    event.get_context_messages.return_value.train.content = "Context content"
    event._context_messages = []
    return event


@pytest.mark.asyncio
async def test_builtin_tools_constants():
    assert len(BUILTIN_TOOLS_NAME) > 0
    assert isinstance(BUILTIN_TOOLS_NAME, set)

    assert len(AGENT_PROCESS_TOOLS) > 0
    assert isinstance(AGENT_PROCESS_TOOLS, tuple)


@pytest.mark.asyncio
@patch("amrita_core.builtins.agent.SessionsManager")
@patch("amrita_core.builtins.agent.get_config")
@patch("amrita_core.builtins.agent.tools_caller")
async def test_agent_core_basic(
    mock_tools_caller, mock_get_config, mock_sessions_manager
):
    mock_config: AmritaConfig = MagicMock()
    mock_config.function_config.tool_calling_mode = "agent"
    mock_config.function_config.agent_thought_mode = "reasoning"
    mock_config.function_config.agent_tool_call_limit = 5
    mock_config.function_config.agent_tool_call_notice = "notify"
    mock_config.function_config.use_minimal_context = False
    mock_config.function_config.agent_reasoning_hide = False
    mock_config.function_config.agent_middle_message = True
    mock_get_config.return_value = mock_config

    mock_session = MagicMock()
    mock_session.tools = MagicMock()
    mock_session.tools.tools_meta_dict.return_value = {}
    mock_sessions_manager.return_value.get_session_data.return_value = mock_session

    event = MagicMock(spec=PreCompletionEvent)
    event.chat_object = MagicMock(spec=ChatObject)
    event.chat_object.session_id = "test-session"
    event.chat_object.preset = "default-preset"
    event.chat_object.yield_response = AsyncMock()
    event.chat_object.set_queue_done = AsyncMock()
    event.message = MagicMock()
    event.message.train = Message(role="system", content="System message")
    event.message.user_query = Message(role="user", content="User query")
    event.message.unwrap = MagicMock(
        return_value=[
            Message(role="system", content="System message"),
            Message(role="user", content="User query"),
        ]
    )
    event.original_context = "Original context"
    event.get_context_messages = MagicMock()
    event.get_context_messages.return_value = MagicMock()
    event.get_context_messages.return_value.train = MagicMock()
    event.get_context_messages.return_value.train.content = "Context content"
    event._context_messages = []

    mock_response = MagicMock(spec=UniResponse)
    mock_response.content = None
    mock_response.tool_calls = None
    mock_tools_caller.return_value = mock_response

    await agent_core(event, mock_config)

    mock_sessions_manager.assert_called_once()


@pytest.mark.asyncio
@patch("amrita_core.builtins.agent.get_config")
async def test_cookie_handler(mock_get_config):
    mock_config = MagicMock()
    mock_config.cookie.enable_cookie = True
    mock_config.cookie.cookie = "test-cookie"
    mock_get_config.return_value = mock_config

    event = MagicMock(spec=CompletionEvent)
    event.chat_object = MagicMock()
    event.chat_object.yield_response = AsyncMock()
    event.chat_object.set_queue_done = AsyncMock()
    event.get_model_response = MagicMock(
        return_value="Some response with test-cookie inside"
    )

    await cookie(event, mock_config)

    event.chat_object.yield_response.assert_called()
    event.chat_object.set_queue_done.assert_called()


@pytest.mark.asyncio
@patch("amrita_core.builtins.agent.get_config")
async def test_cookie_handler_no_match(mock_get_config):
    mock_config = MagicMock()
    mock_config.cookie.enable_cookie = True
    mock_config.cookie.cookie = "test-cookie"
    mock_get_config.return_value = mock_config

    event = MagicMock(spec=CompletionEvent)
    event.chat_object = MagicMock()
    event.chat_object.yield_response = AsyncMock()
    event.chat_object.set_queue_done = AsyncMock()
    event.get_model_response = MagicMock(return_value="Response without cookie")

    await cookie(event, mock_config)

    event.chat_object.yield_response.assert_not_called()
    event.chat_object.set_queue_done.assert_not_called()


# Additional tests for uncovered code paths


@pytest.mark.asyncio
@patch("amrita_core.builtins.agent.SessionsManager")
@patch("amrita_core.builtins.agent.get_config")
@patch("amrita_core.builtins.agent.tools_caller")
async def test_agent_core_tool_calling_mode_none(
    mock_tools_caller, mock_get_config, mock_sessions_manager
):
    """Test when tool_calling_mode is 'none' - should return early"""
    mock_config = MagicMock()
    mock_config.function_config.tool_calling_mode = "none"
    mock_get_config.return_value = mock_config

    event = MagicMock(spec=PreCompletionEvent)
    event.chat_object = MagicMock(spec=ChatObject)
    event.chat_object.session_id = "test-session"
    event.chat_object.preset = "default-preset"

    await agent_core(event, mock_config)

    # tools_caller should not be called
    mock_tools_caller.assert_not_called()


@pytest.mark.asyncio
@patch("amrita_core.builtins.agent.SessionsManager")
@patch("amrita_core.builtins.agent.get_config")
@patch("amrita_core.builtins.agent.tools_caller")
@patch("amrita_core.builtins.agent.logger")
async def test_agent_core_no_valid_tools(
    mock_logger, mock_tools_caller, mock_get_config, mock_sessions_manager
):
    """Test when no valid tools are defined"""
    mock_config = MagicMock()
    mock_config.function_config.tool_calling_mode = (
        "custom"  # Not "agent", so no built-in tools
    )
    mock_config.function_config.agent_tool_call_limit = 5
    mock_get_config.return_value = mock_config

    mock_session = MagicMock()
    mock_session.tools = MagicMock()
    mock_session.tools.tools_meta_dict.return_value = {}  # No custom tools
    mock_sessions_manager.return_value.get_session_data.return_value = mock_session

    event = MagicMock(spec=PreCompletionEvent)
    event.chat_object = MagicMock(spec=ChatObject)
    event.chat_object.session_id = "test-session"
    event.chat_object.preset = "default-preset"
    event.message = MagicMock()
    event.message.train = Message(role="system", content="System message")
    event.message.user_query = Message(role="user", content="User query")
    event.message.unwrap = MagicMock(
        return_value=[event.message.train, event.message.user_query]
    )

    await agent_core(event, mock_config)

    # Should not call tools_caller and should log warning
    mock_tools_caller.assert_not_called()
    mock_logger.warning.assert_called_with(
        "No valid tools defined! Tools Workflow skipped."
    )


@pytest.mark.asyncio
@patch("amrita_core.builtins.agent.SessionsManager")
@patch("amrita_core.builtins.agent.get_config")
@patch("amrita_core.builtins.agent.tools_caller")
async def test_agent_core_successful_tool_call(
    mock_tools_caller, mock_get_config, mock_sessions_manager
):
    """Test successful custom tool call"""
    mock_config = MagicMock()
    mock_config.function_config.tool_calling_mode = "agent"
    mock_config.function_config.agent_tool_call_limit = 5
    mock_config.function_config.agent_tool_call_notice = "notify"
    mock_config.function_config.use_minimal_context = False
    mock_get_config.return_value = mock_config

    # Mock a custom tool
    mock_session = MagicMock()
    mock_session.tools = MagicMock()
    mock_tool_data = MagicMock(spec=ToolData)
    mock_tool_data.custom_run = False
    mock_tool_data.func = AsyncMock(return_value="Tool result")
    mock_session.tools.get_tool.return_value = mock_tool_data
    mock_session.tools.tools_meta_dict.return_value = {
        "custom_tool": {"function": {"name": "custom_tool", "description": "test"}}
    }
    mock_sessions_manager.return_value.get_session_data.return_value = mock_session

    event = MagicMock(spec=PreCompletionEvent)
    event.chat_object = MagicMock(spec=ChatObject)
    event.chat_object.session_id = "test-session"
    event.chat_object.preset = "default-preset"
    event.chat_object.yield_response = AsyncMock()
    event.message = MagicMock()
    event.message.train = Message(role="system", content="System message")
    event.message.user_query = Message(role="user", content="User query")
    event.message.unwrap = MagicMock(
        return_value=[event.message.train, event.message.user_query]
    )
    event.original_context = "Original context"
    event.get_context_messages = MagicMock()
    event.get_context_messages.return_value.train.content = "Context content"
    event._context_messages = []

    # Create proper ToolCall with real objects
    tool_call = ToolCall(
        id="tool-call-1",
        function=Function(name="custom_tool", arguments='{"param": "value"}'),
    )

    response = UniResponse[None, list[ToolCall]](
        content=None,
        tool_calls=[tool_call],
    )
    mock_tools_caller.return_value = response

    await agent_core(event, mock_config)

    # Verify tool was called and result was processed
    mock_tool_data.func.assert_called()
    assert len(event.message.extend.call_args[0][0]) > 0  # Messages were extended


@pytest.mark.asyncio
@patch("amrita_core.builtins.agent.SessionsManager")
@patch("amrita_core.builtins.agent.get_config")
@patch("amrita_core.builtins.agent.tools_caller")
async def test_agent_core_tool_call_failure(
    mock_tools_caller, mock_get_config, mock_sessions_manager
):
    """Test tool call failure handling"""
    mock_config = MagicMock()
    mock_config.function_config.tool_calling_mode = "agent"
    mock_config.function_config.agent_tool_call_limit = 5
    mock_config.function_config.agent_tool_call_notice = "notify"
    mock_get_config.return_value = mock_config

    mock_session = MagicMock()
    mock_session.tools = MagicMock()
    mock_tool_data = MagicMock(spec=ToolData)
    mock_tool_data.custom_run = False
    mock_tool_data.func = AsyncMock(side_effect=RuntimeError("Tool failed"))
    mock_session.tools.get_tool.return_value = mock_tool_data
    mock_session.tools.tools_meta_dict.return_value = {
        "failing_tool": {"function": {"name": "failing_tool", "description": "test"}}
    }
    mock_sessions_manager.return_value.get_session_data.return_value = mock_session

    event = MagicMock(spec=PreCompletionEvent)
    event.chat_object = MagicMock(spec=ChatObject)
    event.chat_object.session_id = "test-session"
    event.chat_object.preset = "default-preset"
    event.chat_object.yield_response = AsyncMock()
    event.message = MagicMock()
    event.message.train = Message(role="system", content="System message")
    event.message.user_query = Message(role="user", content="User query")
    event.message.unwrap = MagicMock(
        return_value=[event.message.train, event.message.user_query]
    )
    event.original_context = "Original context"
    event.get_context_messages = MagicMock()
    event.get_context_messages.return_value.train.content = "Context content"
    event._context_messages = []

    tool_call = ToolCall(
        id="tool-call-1",
        function=Function(name="failing_tool", arguments='{"param": "value"}'),
    )

    response = UniResponse[None, list[ToolCall]](
        content=None,
        tool_calls=[tool_call],
    )
    mock_tools_caller.return_value = response

    await agent_core(event, mock_config)

    # Should handle the error gracefully and continue
    assert len(event.message.extend.call_args[0][0]) > 0  # Error message was added


@pytest.mark.asyncio
@patch("amrita_core.builtins.agent.SessionsManager")
@patch("amrita_core.builtins.agent.get_config")
@patch("amrita_core.builtins.agent.tools_caller")
async def test_agent_core_tool_call_limit_reached(
    mock_tools_caller, mock_get_config, mock_sessions_manager
):
    """Test when tool call limit is reached"""
    mock_config = MagicMock()
    mock_config.function_config.tool_calling_mode = "agent"
    mock_config.function_config.agent_tool_call_limit = 2  # Low limit for testing
    mock_config.function_config.agent_tool_call_notice = "notify"
    mock_get_config.return_value = mock_config

    mock_session = MagicMock()
    mock_session.tools = MagicMock()
    mock_tool_data = MagicMock(spec=ToolData)
    mock_tool_data.custom_run = False
    mock_tool_data.func = AsyncMock(return_value="Tool result")
    mock_session.tools.get_tool.return_value = mock_tool_data
    mock_session.tools.tools_meta_dict.return_value = {
        "loop_tool": {"function": {"name": "loop_tool", "description": "test"}}
    }
    mock_sessions_manager.return_value.get_session_data.return_value = mock_session

    event = MagicMock(spec=PreCompletionEvent)
    event.chat_object = MagicMock(spec=ChatObject)
    event.chat_object.session_id = "test-session"
    event.chat_object.preset = "default-preset"
    event.chat_object.yield_response = AsyncMock()
    event.message = MagicMock()
    event.message.train = Message(role="system", content="System message")
    event.message.user_query = Message(role="user", content="User query")
    event.message.unwrap = MagicMock(
        return_value=[event.message.train, event.message.user_query]
    )
    event.original_context = "Original context"
    event.get_context_messages = MagicMock()
    event.get_context_messages.return_value.train.content = "Context content"
    event._context_messages = []

    tool_call = ToolCall(
        id="tool-call-1",
        function=Function(name="loop_tool", arguments='{"param": "value"}'),
    )

    response = UniResponse[None, list[ToolCall]](
        content=None,
        tool_calls=[tool_call],
    )
    mock_tools_caller.return_value = response

    await agent_core(event, mock_config)

    # Should have called yield_response with limit exceeded message
    call_args = event.chat_object.yield_response.call_args_list
    limit_exceeded_call = None
    for call in call_args:
        if isinstance(call[0][0], MessageWithMetadata):
            msg = call[0][0]
            if "Too many tool calls" in str(msg.content):
                limit_exceeded_call = call
                break

    assert limit_exceeded_call is not None, "Limit exceeded message was not sent"


@pytest.mark.asyncio
@patch("amrita_core.builtins.agent.SessionsManager")
@patch("amrita_core.builtins.agent.get_config")
@patch("amrita_core.builtins.agent.tools_caller")
async def test_agent_core_reasoning_tool(
    mock_tools_caller, mock_get_config, mock_sessions_manager
):
    """Test reasoning tool handling"""
    from amrita_core.builtins.tools import REASONING_TOOL

    mock_config = MagicMock()
    mock_config.function_config.tool_calling_mode = "agent"
    mock_config.function_config.agent_thought_mode = "reasoning"
    mock_config.function_config.agent_tool_call_limit = 5
    mock_config.function_config.agent_reasoning_hide = False
    mock_get_config.return_value = mock_config

    mock_session = MagicMock()
    mock_session.tools = MagicMock()
    mock_session.tools.tools_meta_dict.return_value = {}
    mock_sessions_manager.return_value.get_session_data.return_value = mock_session

    event = MagicMock(spec=PreCompletionEvent)
    event.chat_object = MagicMock(spec=ChatObject)
    event.chat_object.session_id = "test-session"
    event.chat_object.preset = "default-preset"
    event.chat_object.yield_response = AsyncMock()
    event.message = MagicMock()
    event.message.train = Message(role="system", content="System message")
    event.message.user_query = Message(role="user", content="User query")
    event.message.unwrap = MagicMock(
        return_value=[event.message.train, event.message.user_query]
    )
    event.original_context = "Original context"
    event.get_context_messages = MagicMock()
    event.get_context_messages.return_value.train.content = "Context content"
    event._context_messages = []

    # First call: reasoning tool
    reasoning_call = ToolCall(
        id="reasoning-1",
        function=Function(
            name=REASONING_TOOL.function.name,
            arguments='{"content": "This is a reasoning step"}',
        ),
    )

    reasoning_response = UniResponse[None, list[ToolCall]](
        content=None,
        tool_calls=[reasoning_call],
    )

    # Second call: no more tool calls
    final_response = UniResponse[str, None](
        content="Final response",
        tool_calls=None,
    )

    mock_tools_caller.side_effect = [reasoning_response, final_response]

    await agent_core(event, mock_config)

    # Should have called tools_caller twice and handled reasoning
    assert mock_tools_caller.call_count == 2


@pytest.mark.asyncio
@patch("amrita_core.builtins.agent.SessionsManager")
@patch("amrita_core.builtins.agent.get_config")
@patch("amrita_core.builtins.agent.tools_caller")
async def test_agent_core_stop_tool(
    mock_tools_caller, mock_get_config, mock_sessions_manager
):
    """Test stop tool handling"""
    from amrita_core.builtins.tools import STOP_TOOL

    mock_config = MagicMock()
    mock_config.function_config.tool_calling_mode = "agent"
    mock_config.function_config.agent_tool_call_limit = 5
    mock_get_config.return_value = mock_config

    mock_session = MagicMock()
    mock_session.tools = MagicMock()
    mock_session.tools.tools_meta_dict.return_value = {}
    mock_sessions_manager.return_value.get_session_data.return_value = mock_session

    event = MagicMock(spec=PreCompletionEvent)
    event.chat_object = MagicMock(spec=ChatObject)
    event.chat_object.session_id = "test-session"
    event.chat_object.preset = "default-preset"
    event.chat_object.yield_response = AsyncMock()
    event.message = MagicMock()
    event.message.train = Message(role="system", content="System message")
    event.message.user_query = Message(role="user", content="User query")
    event.message.unwrap = MagicMock(
        return_value=[event.message.train, event.message.user_query]
    )
    event.original_context = "Original context"
    event.get_context_messages = MagicMock()
    event.get_context_messages.return_value.train.content = "Context content"
    event._context_messages = []

    stop_call = ToolCall(
        id="stop-1",
        function=Function(
            name=STOP_TOOL.function.name, arguments='{"result": "Final result summary"}'
        ),
    )

    stop_response = UniResponse[None, list[ToolCall]](
        content=None,
        tool_calls=[stop_call],
    )

    mock_tools_caller.return_value = stop_response

    await agent_core(event, mock_config)

    # Should have processed the stop tool and terminated
    assert len(event.message.extend.call_args[0][0]) > 0


@pytest.mark.asyncio
@patch("amrita_core.builtins.agent.SessionsManager")
@patch("amrita_core.builtins.agent.get_config")
@patch("amrita_core.builtins.agent.tools_caller")
async def test_agent_core_custom_run_tool(
    mock_tools_caller, mock_get_config, mock_sessions_manager
):
    """Test custom run tool handling"""
    mock_config = MagicMock()
    mock_config.function_config.tool_calling_mode = "agent"
    mock_config.function_config.agent_tool_call_limit = 5
    mock_get_config.return_value = mock_config

    async def custom_tool_func(ctx):
        await ctx.event.chat_object.yield_response(
            MessageWithMetadata(
                content="Custom tool output", metadata={"type": "custom"}
            )
        )
        return "Custom tool result"

    mock_session = MagicMock()
    mock_session.tools = MagicMock()
    mock_tool_data = MagicMock(spec=ToolData)
    mock_tool_data.custom_run = True
    mock_tool_data.func = custom_tool_func
    mock_session.tools.get_tool.return_value = mock_tool_data
    mock_session.tools.tools_meta_dict.return_value = {
        "custom_run_tool": {
            "function": {"name": "custom_run_tool", "description": "test"}
        }
    }
    mock_sessions_manager.return_value.get_session_data.return_value = mock_session

    event = MagicMock(spec=PreCompletionEvent)
    event.chat_object = MagicMock(spec=ChatObject)
    event.chat_object.session_id = "test-session"
    event.chat_object.preset = "default-preset"
    event.chat_object.yield_response = AsyncMock()
    event.message = MagicMock()
    event.message.train = Message(role="system", content="System message")
    event.message.user_query = Message(role="user", content="User query")
    event.message.unwrap = MagicMock(
        return_value=[event.message.train, event.message.user_query]
    )
    event.original_context = "Original context"
    event.get_context_messages = MagicMock()
    event.get_context_messages.return_value.train.content = "Context content"
    event._context_messages = []

    tool_call = ToolCall(
        id="tool-call-1",
        function=Function(name="custom_run_tool", arguments='{"param": "value"}'),
    )

    response = UniResponse[None, list[ToolCall]](
        content=None,
        tool_calls=[tool_call],
    )
    mock_tools_caller.return_value = response

    await agent_core(event, mock_config)

    # Custom tool should have been called and yielded response
    assert (
        event.chat_object.yield_response.call_count >= 2
    )  # At least initial + custom tool


@pytest.mark.asyncio
@patch("amrita_core.builtins.agent.SessionsManager")
@patch("amrita_core.builtins.agent.get_config")
@patch("amrita_core.builtins.agent.tools_caller")
async def test_agent_core_exception_handling(
    mock_tools_caller, mock_get_config, mock_sessions_manager
):
    """Test general exception handling in agent core"""
    mock_config = MagicMock()
    mock_config.function_config.tool_calling_mode = "agent"
    mock_config.function_config.agent_tool_call_limit = 5
    mock_get_config.return_value = mock_config

    mock_session = MagicMock()
    mock_session.tools = MagicMock()
    mock_session.tools.tools_meta_dict.return_value = {}
    mock_sessions_manager.return_value.get_session_data.return_value = mock_session

    event = MagicMock(spec=PreCompletionEvent)
    event.chat_object = MagicMock(spec=ChatObject)
    event.chat_object.session_id = "test-session"
    event.chat_object.preset = "default-preset"
    event.chat_object.yield_response = AsyncMock()
    event.message = MagicMock()
    event.message.train = Message(role="system", content="System message")
    event.message.user_query = Message(role="user", content="User query")
    event.message.unwrap = MagicMock(
        return_value=[event.message.train, event.message.user_query]
    )
    event.original_context = "Original context"
    event.get_context_messages = MagicMock()
    event.get_context_messages.return_value.train.content = "Context content"
    event._context_messages = []

    # Make tools_caller raise an exception
    mock_tools_caller.side_effect = RuntimeError("Unexpected error")

    await agent_core(event, mock_config)

    # Should handle the exception and yield error response
    error_call_found = False
    for call in event.chat_object.yield_response.call_args_list:
        if isinstance(call[0][0], MessageWithMetadata):
            msg = call[0][0]
            if "Agent run failed" in str(msg.content):
                error_call_found = True
                break

    assert error_call_found, "Error response was not sent"


@pytest.mark.asyncio
@patch("amrita_core.builtins.agent.SessionsManager")
@patch("amrita_core.builtins.agent.get_config")
@patch("amrita_core.builtins.agent.tools_caller")
async def test_agent_core_minimal_context(
    mock_tools_caller, mock_get_config, mock_sessions_manager
):
    """Test minimal context mode"""
    mock_config = MagicMock()
    mock_config.function_config.tool_calling_mode = "agent"
    mock_config.function_config.agent_tool_call_limit = 5
    mock_config.function_config.use_minimal_context = True
    mock_get_config.return_value = mock_config

    mock_session = MagicMock()
    mock_session.tools = MagicMock()
    mock_session.tools.tools_meta_dict.return_value = {}
    mock_sessions_manager.return_value.get_session_data.return_value = mock_session

    event = MagicMock(spec=PreCompletionEvent)
    event.chat_object = MagicMock(spec=ChatObject)
    event.chat_object.session_id = "test-session"
    event.chat_object.preset = "default-preset"
    event.chat_object.yield_response = AsyncMock()
    event.message = MagicMock()
    event.message.train = Message(role="system", content="System message")
    event.message.user_query = Message(role="user", content="User query")
    event.message.unwrap = MagicMock(
        return_value=[event.message.train, event.message.user_query]
    )
    event.original_context = "Original context"
    event.get_context_messages = MagicMock()
    event.get_context_messages.return_value.train.content = "Context content"
    event._context_messages = []

    mock_response = MagicMock(spec=UniResponse)
    mock_response.content = None
    mock_response.tool_calls = None
    mock_tools_caller.return_value = mock_response

    await agent_core(event, mock_config)

    # Should use minimal context (only train + user_query)
    assert mock_tools_caller.call_args[0][0] == [
        event.message.train,
        event.message.user_query,
    ]


@pytest.mark.asyncio
@patch("amrita_core.builtins.agent.get_config")
async def test_cookie_handler_disabled(mock_get_config):
    """Test cookie handler when disabled"""
    mock_config = MagicMock()
    mock_config.cookie.enable_cookie = False
    mock_config.cookie.cookie = "test-cookie"
    mock_get_config.return_value = mock_config

    event = MagicMock(spec=CompletionEvent)
    event.chat_object = MagicMock()
    event.chat_object.yield_response = AsyncMock()
    event.chat_object.set_queue_done = AsyncMock()
    event.get_model_response = MagicMock(return_value="Response with test-cookie")

    await cookie(event, mock_config)

    # Should not process cookie when disabled
    event.chat_object.yield_response.assert_not_called()
    event.chat_object.set_queue_done.assert_not_called()
