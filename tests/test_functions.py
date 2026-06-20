"""
Unit tests for AmritaCore Agent Runtime functions.

This module tests the AgentRuntime class and create_agent factory function.
"""

import pytest
from jinja2 import Template

from amrita_core.agent.functions import AgentRuntime, create_agent
from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.backends import LegacyBackend
from amrita_core.chatmanager import ChatObject
from amrita_core.config import AmritaConfig, FunctionConfig, LLMConfig, set_config
from amrita_core.types import Message, ModelConfig, ModelPreset

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


def test_agent_runtime_init_defaults(mock_config, mock_preset):
    """Test AgentRuntime initialization with defaults (no custom session_id/backend)."""
    runtime = AgentRuntime(config=mock_config, train=TEST_TRAIN, preset=mock_preset)

    assert runtime.session_id is not None
    assert len(runtime.session_id) == 32  # uuid4 hex
    assert isinstance(runtime.slot, BackendSlots)
    assert isinstance(runtime.slot.ability, LegacyBackend)
    assert isinstance(runtime.slot.memory, LegacyBackend)
    assert isinstance(runtime.template, Template)
    assert runtime.strategy is not None
    assert runtime.preset == mock_preset
    assert runtime.config == mock_config


def test_agent_runtime_init_with_session_id(mock_config, mock_preset):
    """Test AgentRuntime initialization with explicit session_id."""
    session_id = "my-custom-session-id"
    runtime = AgentRuntime(
        config=mock_config, train=TEST_TRAIN, preset=mock_preset, session_id=session_id
    )

    assert runtime.session_id == session_id


def test_agent_runtime_init_with_backend(mock_config, mock_preset):
    """Test AgentRuntime initialization with custom BackendSlots."""
    mem = LegacyBackend()
    abi = LegacyBackend()
    custom_slot = BackendSlots(ability=abi, memory=mem)

    runtime = AgentRuntime(
        config=mock_config,
        train=TEST_TRAIN,
        preset=mock_preset,
        backend=custom_slot,
    )

    assert runtime.slot is custom_slot
    assert runtime.slot.ability is abi
    assert runtime.slot.memory is mem


def test_agent_runtime_set_strategy(mock_config, mock_preset):
    """Test AgentRuntime set_strategy method."""
    from amrita_core.builtins.agent import ReActAgentStrategy

    runtime = AgentRuntime(config=mock_config, train=TEST_TRAIN, preset=mock_preset)

    MockStrategy = type("MockStrategy", (ReActAgentStrategy,), {})

    runtime.set_strategy(MockStrategy)
    assert runtime.strategy == MockStrategy


def test_agent_runtime_get_chatobject(mock_config, mock_preset):
    """Test AgentRuntime get_chatobject method."""
    runtime = AgentRuntime(
        config=mock_config,
        preset=mock_preset,
        train={"role": "system", "content": "test system message"},
    )

    user_input = "test user input"
    chat_object = runtime.get_chatobject(user_input)

    assert isinstance(chat_object, ChatObject)
    assert chat_object._s_id == runtime.session_id
    assert chat_object.config == runtime.config
    assert chat_object.preset == runtime.preset
    assert chat_object.slot is runtime.slot


def test_agent_runtime_get_chatobject_extra_kwargs(mock_config, mock_preset):
    """Test get_chatobject passes extra kwargs through to ChatObject."""
    runtime = AgentRuntime(config=mock_config, train=TEST_TRAIN, preset=mock_preset)

    chat_object = runtime.get_chatobject(
        "hello",
        jinja2_vars={"extra": "value"},
    )

    assert chat_object.jinja2_vars == {"extra": "value"}


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
    agent = create_agent(
        base_url="https://api.test.com",
        api_key="test-key",
        config=mock_config,
        template="custom template content",
        session_id="custom-session",
    )

    assert "custom template content" in agent.template.render()
    assert agent.session_id == "custom-session"


def test_agent_runtime_train_message_handling(mock_config, mock_preset):
    """Test AgentRuntime handling of train parameter as dict and Message."""
    # Test with dict
    runtime_dict = AgentRuntime(
        config=mock_config,
        preset=mock_preset,
        train={"role": "system", "content": "test content"},
    )
    assert isinstance(runtime_dict.train, Message)
    assert runtime_dict.train.content == "test content"

    # Test with Message object
    train_msg = Message(role="system", content="test message")
    runtime_msg = AgentRuntime(config=mock_config, preset=mock_preset, train=train_msg)
    assert runtime_msg.train == train_msg


def test_agent_runtime_slot_is_independent_per_instance(mock_config, mock_preset):
    """Test that separate AgentRuntime instances get independent BackendSlots."""
    r1 = AgentRuntime(config=mock_config, train=TEST_TRAIN, preset=mock_preset)
    r2 = AgentRuntime(config=mock_config, train=TEST_TRAIN, preset=mock_preset)

    # Different session IDs
    assert r1.session_id != r2.session_id
    # Different BackendSlots instances (each gets its own LegacyBackend)
    assert r1.slot is not r2.slot
    assert r1.slot.ability is not r2.slot.ability
    assert r1.slot.memory is not r2.slot.memory
