"""
Unit tests for AmritaCore Agent Runtime functions.

This module tests the AgentRuntime class and create_agent factory function.
"""

from unittest.mock import patch

import pytest
from jinja2 import Template

from amrita_core.agent.functions import AgentRuntime, create_agent
from amrita_core.chatmanager import ChatObject
from amrita_core.config import AmritaConfig, FunctionConfig, LLMConfig, set_config
from amrita_core.sessions import SessionData, SessionsManager
from amrita_core.types import MemoryModel, Message, ModelConfig, ModelPreset

TEST_TRAIN: dict[str, str] = {
    "role": "system",
    "content": "You are a helpful assistant.",
}


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
def mock_preset():
    """Create a mock ModelPreset for testing."""
    return ModelPreset(
        name="test_preset",
        base_url="https://api.test.com",
        api_key="test_key",
        model="test-model",
        config=ModelConfig(),
    )


def test_agent_runtime_init_no_session(mock_config, mock_preset):
    """Test AgentRuntime initialization with no_session=True."""
    runtime = AgentRuntime(
        config=mock_config, train=TEST_TRAIN, preset=mock_preset, no_session=True
    )

    assert runtime.session is None
    assert runtime.session_id is not None
    assert isinstance(runtime.context, MemoryModel)
    assert isinstance(runtime.template, Template)
    assert runtime.strategy is not None
    assert runtime.preset == mock_preset
    assert runtime.config == mock_config


def test_agent_runtime_init_with_session_string(mock_config, mock_preset):
    """Test AgentRuntime initialization with session as string."""
    session_id = "test-session-id"

    # Mock SessionsManager methods
    with (
        patch.object(SessionsManager, "init_session") as mock_init,
        patch.object(SessionsManager, "get_session_data") as mock_get,
    ):
        mock_session_data = SessionData(session_id=session_id)
        mock_get.return_value = mock_session_data

        runtime = AgentRuntime(
            config=mock_config, train=TEST_TRAIN, preset=mock_preset, session=session_id
        )

        mock_init.assert_called_once_with(session_id)
        mock_get.assert_called_once_with(session_id)
        assert runtime.session == mock_session_data
        assert runtime.session_id == session_id
        assert runtime.context == mock_session_data.memory


def test_agent_runtime_init_new_session(mock_config, mock_preset):
    """Test AgentRuntime initialization creating new session."""
    with (
        patch.object(SessionsManager, "new_session") as mock_new,
        patch.object(SessionsManager, "init_session") as mock_init,
        patch.object(SessionsManager, "get_session_data") as mock_get,
    ):
        mock_new.return_value = "new-session-id"
        mock_session_data = SessionData(session_id="new-session-id")
        mock_get.return_value = mock_session_data

        runtime = AgentRuntime(
            config=mock_config, train=TEST_TRAIN, preset=mock_preset, session=None
        )

        mock_new.assert_called_once()
        mock_init.assert_called_once_with("new-session-id")
        mock_get.assert_called_once_with("new-session-id")
        assert runtime.session == mock_session_data
        assert runtime.session_id == "new-session-id"


def test_agent_runtime_no_session_property(mock_config, mock_preset):
    """Test AgentRuntime no_session property."""
    # Test with session disabled
    runtime_no_session = AgentRuntime(
        config=mock_config, train=TEST_TRAIN, preset=mock_preset, no_session=True
    )
    assert runtime_no_session.no_session is True

    # Test with session enabled
    with (
        patch.object(SessionsManager, "new_session", return_value="test-id"),
        patch.object(SessionsManager, "init_session"),
        patch.object(SessionsManager, "get_session_data") as mock_get,
    ):
        mock_get.return_value = SessionData(session_id="test-id")
        runtime_with_session = AgentRuntime(
            config=mock_config, train=TEST_TRAIN, preset=mock_preset, session=None
        )
        assert runtime_with_session.no_session is False


def test_agent_runtime_set_strategy(mock_config, mock_preset):
    """Test AgentRuntime set_strategy method."""
    from amrita_core.builtins.agent import ReActAgentStrategy

    runtime = AgentRuntime(
        config=mock_config, train=TEST_TRAIN, preset=mock_preset, no_session=True
    )

    MockStrategy = type("MockStrategy", (ReActAgentStrategy,), {})

    runtime.set_strategy(MockStrategy)
    assert runtime.strategy == MockStrategy


def test_agent_runtime_get_chatobject(mock_config, mock_preset):
    """Test AgentRuntime get_chatobject method."""
    runtime = AgentRuntime(
        config=mock_config,
        preset=mock_preset,
        no_session=True,
        train={"role": "system", "content": "test system message"},
    )

    user_input = "test user input"
    chat_object = runtime.get_chatobject(user_input)

    assert isinstance(chat_object, ChatObject)
    assert chat_object.session_id == runtime.session_id
    assert chat_object.config == runtime.config
    assert chat_object.preset == runtime.preset
    assert chat_object.data == runtime.context


def test_create_agent_basic(mock_config):
    """Test create_agent factory function basic usage."""
    url = "https://api.test.com"
    key = "test-api-key"
    model = "test-model"

    agent = create_agent(base_url=url, api_key=key, model=model, config=mock_config)

    assert isinstance(agent, AgentRuntime)
    assert agent.config == mock_config
    assert agent.preset.base_url == url
    assert agent.preset.api_key == key
    assert agent.preset.model == model


def test_create_agent_with_model_config_dict(mock_config):
    """Test create_agent with model_config as dictionary."""
    agent = create_agent(
        base_url="https://api.test.com",
        api_key="test-key",
        model_config={
            "temperature": 0.7,
        },
        config=mock_config,
    )

    assert isinstance(agent.preset.config, ModelConfig)
    assert agent.preset.config.temperature == 0.7


def test_create_agent_with_model_config_object(mock_config):
    """Test create_agent with model_config as ModelConfig object."""
    model_config = ModelConfig(temperature=0.8)
    agent = create_agent(
        base_url="https://api.test.com",
        api_key="test-key",
        model_config=model_config,
        config=mock_config,
    )

    assert agent.preset.config == model_config


def test_create_agent_no_model_config(mock_config):
    """Test create_agent without model_config."""
    agent = create_agent(
        base_url="https://api.test.com", api_key="test-key", config=mock_config
    )

    assert isinstance(agent.preset.config, ModelConfig)


def test_create_agent_with_additional_kwargs(mock_config):
    """Test create_agent with additional kwargs passed to AgentRuntime."""
    with (
        patch.object(SessionsManager, "new_session", return_value="test-id"),
        patch.object(SessionsManager, "init_session"),
        patch.object(SessionsManager, "get_session_data") as mock_get,
    ):
        mock_get.return_value = SessionData(session_id="test-id")

        agent = create_agent(
            base_url="https://api.test.com",
            api_key="test-key",
            config=mock_config,
            template="custom template",
            no_session=False,
        )

        assert "custom template" in agent.template.render()


def test_agent_runtime_train_message_handling(mock_config, mock_preset):
    """Test AgentRuntime handling of train parameter as dict and Message."""
    # Test with dict
    runtime_dict = AgentRuntime(
        config=mock_config,
        preset=mock_preset,
        no_session=True,
        train={"role": "system", "content": "test content"},
    )
    assert isinstance(runtime_dict.train, Message)
    assert runtime_dict.train.content == "test content"

    # Test with Message object
    train_msg = Message(role="system", content="test message")
    runtime_msg = AgentRuntime(
        config=mock_config, preset=mock_preset, no_session=True, train=train_msg
    )
    assert runtime_msg.train == train_msg
