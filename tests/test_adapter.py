# type: ignore
from unittest.mock import AsyncMock, patch

import pytest
from openai import AsyncStream
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)
from openai.types.chat.chat_completion_message_tool_call import (
    Function as ToolCallFunction,
)

from amrita_core.builtins.adapter import OpenAIAdapter
from amrita_core.config import AmritaConfig
from amrita_core.tools.models import ToolFunctionSchema
from amrita_core.types import ModelPreset, ToolCall, UniResponse


class MockAsyncStream(AsyncStream):
    """Mock AsyncStream for testing"""

    def __init__(self, chunks):
        self.chunks = chunks

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.chunks:
            raise StopAsyncIteration
        return self.chunks.pop(0)


class TestOpenAIAdapter:
    """Test OpenAIAdapter functionality"""

    @pytest.fixture
    def adapter(self):
        """Create OpenAIAdapter instance with mock config and preset"""
        config = AmritaConfig()
        preset = ModelPreset(
            model="gpt-3.5-turbo",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
        )
        return OpenAIAdapter(config=config, preset=preset)

    @pytest.fixture
    def mock_messages(self):
        """Create mock messages for testing"""
        return [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]

    @pytest.mark.asyncio
    async def test_get_adapter_protocol(self):
        """Test get_adapter_protocol method"""
        protocol = OpenAIAdapter.get_adapter_protocol()
        assert protocol == ("openai", "__main__")

    @pytest.mark.asyncio
    async def test_call_api_non_streaming(self, adapter, mock_messages):
        """Test call_api with non-streaming response"""
        # Mock the OpenAI client response
        mock_completion = ChatCompletion(
            id="chatcmpl-123",
            choices=[
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello there!"},
                    "finish_reason": "stop",
                }
            ],
            created=1234567890,
            model="gpt-3.5-turbo",
            object="chat.completion",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )

        with patch("amrita_core.builtins.adapter.openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai.return_value = mock_client

            # Call the method
            results = []
            async for result in adapter.call_api(mock_messages):
                results.append(result)

            # Verify results
            assert len(results) == 2  # content + UniResponse
            assert results[0] == "Hello there!"
            assert isinstance(results[1], UniResponse)
            assert results[1].content == "Hello there!"
            assert results[1].usage is not None
            assert results[1].usage.prompt_tokens == 10

    @pytest.mark.asyncio
    async def test_call_api_streaming(self, adapter, mock_messages):
        """Test call_api with streaming response"""
        # Set stream to True
        adapter.preset.config.stream = True

        # Create mock chunks
        chunk1 = ChatCompletionChunk(
            id="chatcmpl-123",
            choices=[
                {"index": 0, "delta": {"content": "Hello"}, "finish_reason": None}
            ],
            created=1234567890,
            model="gpt-3.5-turbo",
            object="chat.completion.chunk",
        )
        chunk2 = ChatCompletionChunk(
            id="chatcmpl-123",
            choices=[
                {"index": 0, "delta": {"content": " there!"}, "finish_reason": "stop"}
            ],
            created=1234567890,
            model="gpt-3.5-turbo",
            object="chat.completion.chunk",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )

        with patch("amrita_core.builtins.adapter.openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_stream = MockAsyncStream([chunk1, chunk2])
            mock_client.chat.completions.create.return_value = mock_stream
            mock_openai.return_value = mock_client

            # Call the method
            results = []
            async for result in adapter.call_api(mock_messages):
                results.append(result)

            # Verify results
            assert len(results) == 3  # "Hello" + " there!" + UniResponse
            assert results[0] == "Hello"
            assert results[1] == " there!"
            assert isinstance(results[2], UniResponse)
            assert results[2].content == "Hello there!"
            assert results[2].usage is not None

    @pytest.mark.asyncio
    async def test_call_api_streaming_with_empty_content(self, adapter, mock_messages):
        """Test call_api with streaming response that has empty content chunks"""
        adapter.preset.config.stream = True

        # Create mock chunks with some empty content
        chunk1 = ChatCompletionChunk(
            id="chatcmpl-123",
            choices=[{"index": 0, "delta": {"content": ""}, "finish_reason": None}],
            created=1234567890,
            model="gpt-3.5-turbo",
            object="chat.completion.chunk",
        )
        chunk2 = ChatCompletionChunk(
            id="chatcmpl-123",
            choices=[
                {"index": 0, "delta": {"content": "Hello"}, "finish_reason": "stop"}
            ],
            created=1234567890,
            model="gpt-3.5-turbo",
            object="chat.completion.chunk",
        )

        with patch("amrita_core.builtins.adapter.openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_stream = MockAsyncStream([chunk1, chunk2])
            mock_client.chat.completions.create.return_value = mock_stream
            mock_openai.return_value = mock_client

            results = []
            async for result in adapter.call_api(mock_messages):
                results.append(result)

            # Empty string is also yielded since it's not None
            assert len(results) == 3
            assert results[0] == ""
            assert results[1] == "Hello"
            assert isinstance(results[2], UniResponse)
            assert results[2].content == "Hello"

    @pytest.mark.asyncio
    async def test_call_api_non_streaming_empty_content(self, adapter, mock_messages):
        """Test call_api with non-streaming response that has empty content"""
        mock_completion = ChatCompletion(
            id="chatcmpl-123",
            choices=[
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": None},
                    "finish_reason": "stop",
                }
            ],
            created=1234567890,
            model="gpt-3.5-turbo",
            object="chat.completion",
        )

        with patch("amrita_core.builtins.adapter.openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai.return_value = mock_client

            results = []
            async for result in adapter.call_api(mock_messages):
                results.append(result)

            assert len(results) == 2
            assert results[0] == ""
            assert isinstance(results[1], UniResponse)
            assert results[1].content == ""

    @pytest.mark.asyncio
    async def test_call_tools_auto_choice(self, adapter, mock_messages):
        """Test call_tools with auto tool choice"""
        # Mock tool call response
        mock_tool_call = ChatCompletionMessageToolCall(
            id="call_123",
            function=ToolCallFunction(
                name="test_function", arguments='{"param": "value"}'
            ),
            type="function",
        )
        mock_completion = ChatCompletion(
            id="chatcmpl-123",
            choices=[
                {
                    "index": 0,
                    "message": ChatCompletionMessage(
                        role="assistant", content=None, tool_calls=[mock_tool_call]
                    ),
                    "finish_reason": "tool_calls",
                }
            ],
            created=1234567890,
            model="gpt-3.5-turbo",
            object="chat.completion",
        )

        with patch("amrita_core.builtins.adapter.openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai.return_value = mock_client

            # Call the method
            result = await adapter.call_tools(mock_messages, tools=[])

            # Verify result
            assert isinstance(result, UniResponse)
            assert result.content is None
            assert result.tool_calls is not None
            assert len(result.tool_calls) == 1
            assert isinstance(result.tool_calls[0], ToolCall)
            assert result.tool_calls[0].id == "call_123"
            assert result.tool_calls[0].function.name == "test_function"

    @pytest.mark.asyncio
    async def test_call_tools_specific_function_choice(self, adapter, mock_messages):
        """Test call_tools with specific function tool choice"""
        tool_schema = ToolFunctionSchema(
            function={
                "name": "specific_function",
                "description": "A test function",
                "parameters": {"type": "object", "properties": {}},
            }
        )
        mock_tool_call = ChatCompletionMessageToolCall(
            id="call_456",
            function=ToolCallFunction(
                name="specific_function", arguments='{"param": "test"}'
            ),
            type="function",
        )
        mock_completion = ChatCompletion(
            id="chatcmpl-123",
            choices=[
                {
                    "index": 0,
                    "message": ChatCompletionMessage(
                        role="assistant", content=None, tool_calls=[mock_tool_call]
                    ),
                    "finish_reason": "tool_calls",
                }
            ],
            created=1234567890,
            model="gpt-3.5-turbo",
            object="chat.completion",
        )

        with patch("amrita_core.builtins.adapter.openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai.return_value = mock_client

            result = await adapter.call_tools(
                mock_messages, tools=[], tool_choice=tool_schema
            )

            assert isinstance(result, UniResponse)
            assert result.tool_calls is not None
            assert len(result.tool_calls) == 1
            assert result.tool_calls[0].function.name == "specific_function"

    @pytest.mark.asyncio
    async def test_call_tools_no_tool_calls(self, adapter, mock_messages):
        """Test call_tools when no tool calls are returned"""
        mock_completion = ChatCompletion(
            id="chatcmpl-123",
            choices=[
                {
                    "index": 0,
                    "message": ChatCompletionMessage(
                        role="assistant", content="No tools needed", tool_calls=None
                    ),
                    "finish_reason": "stop",
                }
            ],
            created=1234567890,
            model="gpt-3.5-turbo",
            object="chat.completion",
        )

        with patch("amrita_core.builtins.adapter.openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai.return_value = mock_client

            result = await adapter.call_tools(mock_messages, tools=[])

            assert isinstance(result, UniResponse)
            assert result.content is None
            assert result.tool_calls is None

    @pytest.mark.asyncio
    async def test_call_api_unexpected_response_type(self, adapter, mock_messages):
        """Test call_api with unexpected response type"""
        adapter.preset.config.stream = False

        with patch("amrita_core.builtins.adapter.openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = "unexpected_string"
            mock_openai.return_value = mock_client

            with pytest.raises(RuntimeError, match="Received unexpected response type"):
                async for _ in adapter.call_api(mock_messages):
                    pass

    @pytest.mark.asyncio
    async def test_call_api_streaming_index_error(self, adapter, mock_messages):
        """Test call_api streaming with IndexError exception"""
        adapter.preset.config.stream = True

        # Create mock chunk that will cause IndexError (empty choices)
        chunk1 = ChatCompletionChunk(
            id="chatcmpl-123",
            choices=[],  # Empty choices list will cause IndexError
            created=1234567890,
            model="gpt-3.5-turbo",
            object="chat.completion.chunk",
        )

        with patch("amrita_core.builtins.adapter.openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_stream = MockAsyncStream([chunk1])
            mock_client.chat.completions.create.return_value = mock_stream
            mock_openai.return_value = mock_client

            results = []
            async for result in adapter.call_api(mock_messages):
                results.append(result)

            # Should handle IndexError gracefully and return empty response
            assert len(results) == 1  # Only UniResponse
            assert isinstance(results[0], UniResponse)
            assert results[0].content == ""

    @pytest.mark.asyncio
    async def test_call_tools_with_string_tool_choice(self, adapter, mock_messages):
        """Test call_tools with string tool choice to cover client creation path"""
        mock_completion = ChatCompletion(
            id="chatcmpl-123",
            choices=[
                {
                    "index": 0,
                    "message": ChatCompletionMessage(
                        role="assistant", content="No tools needed", tool_calls=None
                    ),
                    "finish_reason": "stop",
                }
            ],
            created=1234567890,
            model="gpt-3.5-turbo",
            object="chat.completion",
        )

        with patch("amrita_core.builtins.adapter.openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai.return_value = mock_client

            # Pass a string as tool_choice to test the else branch
            result = await adapter.call_tools(
                mock_messages, tools=[], tool_choice="required"
            )

            assert isinstance(result, UniResponse)
            assert result.content is None
            assert result.tool_calls is None
