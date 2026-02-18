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
from amrita_core.types import Message, UniResponse


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
