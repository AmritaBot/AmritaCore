import asyncio

import pytest

from amrita_core.types import (
    CONTENT_LIST_TYPE,
    Function,
    MemoryModel,
    Message,
    ModelConfig,
    ModelPreset,
    SendMessageWrap,
    ToolCall,
    UniResponse,
)


class TestModelConfig:
    """Test ModelConfig class functionality"""

    def test_default_values(self):
        """Test default values"""
        config = ModelConfig()
        assert config.top_k
        assert config.top_p
        assert config.temperature
        assert config.stream is False
        assert config.multimodal is False

    def test_custom_values(self):
        """Test custom values"""
        config = ModelConfig(top_k=100, temperature=0.8, stream=True)
        assert config.top_k == 100
        assert config.temperature == 0.8
        assert config.stream is True


class TestModelPreset:
    """Test ModelPreset class functionality"""

    def test_default_values(self):
        """Test default values"""
        preset = ModelPreset()
        assert preset.model == ""
        assert preset.name == "default"
        assert preset.base_url == ""
        assert preset.api_key == ""
        assert preset.protocol == "__main__"

    def test_load_save(self, tmp_path):
        """Test save and load functionality"""
        # Create temporary file path
        temp_file = tmp_path / "preset.json"

        # Create a preset and save it
        preset = ModelPreset(
            model="gpt-3.5-turbo", name="test_preset", api_key="test_key"
        )
        preset.save(temp_file)

        # Verify file exists
        assert temp_file.exists()

        # Load preset from file
        loaded_preset = ModelPreset.load(temp_file)

        # Verify loaded preset values
        assert loaded_preset.model == "gpt-3.5-turbo"
        assert loaded_preset.name == "test_preset"
        assert loaded_preset.api_key == "test_key"

    def test_extra_field(self):
        """Test extra field functionality"""
        preset = ModelPreset(extra={"custom_param": "value"})
        assert preset.extra["custom_param"] == "value"


class TestMessage:
    """Test Message class functionality"""

    def test_text_message(self):
        """Test text message"""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"


class TestSendMessageWrap:
    """Test SendMessageWrap class functionality"""

    def test_initialization(self):
        """Test initialization functionality"""
        train_msg = {"role": "system", "content": "system message"}
        memory: CONTENT_LIST_TYPE = [Message(role="user", content="previous message")]
        user_query = Message(role="user", content="current query")

        wrapper = SendMessageWrap(train_msg, memory, user_query)

        assert wrapper.train.content == "system message"
        assert wrapper.user_query.content == "current query"
        assert len(wrapper.memory) == 1

    def test_validation(self):
        """Test message validation functionality"""
        system_msg = Message(role="system", content="system message")
        user_msg = Message(role="user", content="user message")
        assistant_msg = Message(role="assistant", content="assistant message")

        messages: CONTENT_LIST_TYPE = [system_msg, user_msg, assistant_msg, user_msg]
        wrapper = SendMessageWrap.validate_messages(messages)

        assert wrapper.train.content == "system message"
        assert len(wrapper.memory) == 2
        assert wrapper.user_query.content == "user message"

    def test_iterable_behavior(self):
        """Test iterable behavior"""
        train_msg = {"role": "system", "content": "system message"}
        memory: CONTENT_LIST_TYPE = [
            Message(role="assistant", content="assistant message")
        ]
        user_query = Message(role="user", content="user query")

        wrapper = SendMessageWrap(train_msg, memory, user_query)

        items = list(wrapper)
        assert len(items) == 3  # train + memory + user_query
        assert items[0].content == "system message"
        assert items[1].content == "assistant message"
        assert items[2].content == "user query"


class TestUniResponse:
    """Test UniResponse class functionality"""

    def test_basic_response(self):
        """Test basic response"""
        response = UniResponse(content="Hello world", tool_calls=None, role="assistant")
        assert response.content == "Hello world"
        assert response.tool_calls is None
        assert response.role == "assistant"

    def test_response_with_tool_calls(self):
        """Test response with tool calls"""
        func = Function(arguments='{"x": 5}', name="add")
        tool_call = ToolCall(id="call_1", function=func)

        response = UniResponse(content="Calculating...", tool_calls=[tool_call])
        assert response.content == "Calculating..."
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].id == "call_1"


class TestMemoryModel:
    """Test MemoryModel class functionality"""

    def test_default_values(self):
        """Test default values"""
        memory = MemoryModel()
        assert memory.messages == []
        assert memory.abstract == ""
        assert memory.time > 0  # Should be current timestamp

    def test_with_messages(self):
        """Test with messages"""
        msg = Message(role="user", content="test message")
        memory = MemoryModel(messages=[msg])

        assert len(memory.messages) == 1
        assert memory.messages[0].role == "user"
        assert memory.messages[0].content == "test message"


@pytest.mark.asyncio
async def test_async_example():
    """Async test example"""
    # Simulate an async operation
    await asyncio.sleep(0.01)
    assert True
