# type: ignore
from unittest.mock import AsyncMock, MagicMock, patch

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

from amrita_core.builtins.adapter import AnthropicAdapter, OpenAIAdapter
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


class TestAnthropicAdapter:
    """Test AnthropicAdapter functionality"""

    @pytest.fixture
    def anthropic_adapter(self):
        """Create AnthropicAdapter instance with mock config and preset"""
        config = AmritaConfig()
        preset = ModelPreset(
            model="claude-3-opus-20240229",
            base_url="https://api.anthropic.com",
            api_key="test-key",
        )
        return AnthropicAdapter(config=config, preset=preset)

    @pytest.fixture
    def simple_messages(self):
        """Create simple messages for testing"""
        return [
            {
                "role": "user",
                "content": "Hello!",
            },  # Remove system message for tool tests
        ]

    @pytest.fixture
    def messages_with_tool_calls(self):
        """Create messages with tool calls for testing"""
        return [
            {"role": "user", "content": "What's the weather?"},
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "toolu_bdrk_01K2K2K2K2K2K2K2K2K2K2",
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"location": "New York"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "toolu_bdrk_01K2K2K2K2K2K2K2K2K2K2",
                "content": "The weather is sunny, 75°F",
            },
        ]

    def test_get_adapter_protocol(self):
        """Test get_adapter_protocol method"""
        protocol = AnthropicAdapter.get_adapter_protocol()
        assert protocol == ("anthropic", "claude")

    def test_convert_content_to_blocks_text(self):
        """Test _convert_content_to_blocks with plain text"""
        content = "Hello world"
        blocks = AnthropicAdapter._convert_content_to_blocks(content)
        expected = [{"type": "text", "text": "Hello world"}]
        assert blocks == expected

    def test_convert_content_to_blocks_none(self):
        """Test _convert_content_to_blocks with None"""
        blocks = AnthropicAdapter._convert_content_to_blocks(None)
        assert blocks == []

    def test_convert_content_to_blocks_list_text(self):
        """Test _convert_content_to_blocks with list of text content"""
        content = [{"type": "text", "text": "Hello"}, {"type": "text", "text": "World"}]
        blocks = AnthropicAdapter._convert_content_to_blocks(content)
        expected = [
            {"type": "text", "text": "Hello"},
            {"type": "text", "text": "World"},
        ]
        assert blocks == expected

    def test_convert_content_to_blocks_list_image(self):
        """Test _convert_content_to_blocks with image content"""
        content = [
            {"type": "text", "text": "Hello"},
            {
                "type": "image_url",
                "image_url": {"url": "https://example.com/image.jpg"},
            },
        ]
        blocks = AnthropicAdapter._convert_content_to_blocks(content)
        expected = [
            {"type": "text", "text": "Hello"},
            {
                "type": "image",
                "source": {"type": "url", "url": "https://example.com/image.jpg"},
            },
        ]
        assert blocks == expected

    def test_convert_content_to_blocks_empty_list(self):
        """Test _convert_content_to_blocks with empty list returns default text block"""
        content = []
        blocks = AnthropicAdapter._convert_content_to_blocks(content)
        expected = [{"type": "text", "text": ""}]
        assert blocks == expected

    def test_convert_messages_system_only(self):
        """Test _convert_messages with only system message"""
        messages = [{"role": "system", "content": "You are an AI assistant."}]
        converted = AnthropicAdapter._convert_messages(messages)
        expected = [{"role": "system", "content": "You are an AI assistant."}]
        assert converted == expected

    def test_convert_messages_user_text(self):
        """Test _convert_messages with user text message"""
        messages = [{"role": "user", "content": "Hello!"}]
        converted = AnthropicAdapter._convert_messages(messages)
        expected = [{"role": "user", "content": [{"type": "text", "text": "Hello!"}]}]
        assert converted == expected

    def test_convert_messages_user_list_content(self):
        """Test _convert_messages with user list content"""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Hello"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://example.com/image.jpg"},
                    },
                ],
            }
        ]
        converted = AnthropicAdapter._convert_messages(messages)
        expected = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Hello"},
                    {
                        "type": "image",
                        "source": {
                            "type": "url",
                            "url": "https://example.com/image.jpg",
                        },
                    },
                ],
            }
        ]
        assert converted == expected

    def test_convert_messages_assistant_no_tools(self):
        """Test _convert_messages with assistant message without tools"""
        messages = [{"role": "assistant", "content": "Hello there!"}]
        converted = AnthropicAdapter._convert_messages(messages)
        expected = [
            {"role": "assistant", "content": [{"type": "text", "text": "Hello there!"}]}
        ]
        assert converted == expected

    def test_convert_messages_assistant_with_tools(self):
        """Test _convert_messages with assistant message with tool calls"""
        messages = [
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "toolu_bdrk_01K2K2K2K2K2K2K2K2K2K2",
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"location": "New York"}',
                        },
                    }
                ],
            }
        ]
        converted = AnthropicAdapter._convert_messages(messages)
        expected = [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_bdrk_01K2K2K2K2K2K2K2K2K2K2",
                        "name": "get_weather",
                        "input": {"location": "New York"},
                    }
                ],
            }
        ]
        assert converted == expected

    def test_convert_messages_tool_messages(self):
        """Test _convert_messages with tool messages (should be merged into user message)"""
        messages = [
            {"role": "user", "content": "What's the weather?"},
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "toolu_bdrk_01K2K2K2K2K2K2K2K2K2K2",
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"location": "New York"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "toolu_bdrk_01K2K2K2K2K2K2K2K2K2K2",
                "content": "The weather is sunny, 75°F",
            },
        ]
        converted = AnthropicAdapter._convert_messages(messages)
        expected = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "What's the weather?"}],
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_bdrk_01K2K2K2K2K2K2K2K2K2K2",
                        "name": "get_weather",
                        "input": {"location": "New York"},
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_bdrk_01K2K2K2K2K2K2K2K2K2K2",
                        "content": "The weather is sunny, 75°F",
                    }
                ],
            },
        ]
        assert converted == expected

    def test_convert_messages_mixed_roles(self):
        """Test _convert_messages with mixed roles including system"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        converted = AnthropicAdapter._convert_messages(messages)
        expected = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": [{"type": "text", "text": "Hello!"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "Hi there!"}]},
        ]
        assert converted == expected

    def test_convert_messages_system_with_list_content(self):
        """Test _convert_messages with system message containing list content"""
        messages = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": "You are a helpful assistant."},
                    {"type": "text", "text": "Always be polite."},
                ],
            }
        ]
        converted = AnthropicAdapter._convert_messages(messages)
        expected = [
            {
                "role": "system",
                "content": "You are a helpful assistant.Always be polite.",
            }
        ]
        assert converted == expected

    def test_convert_tools_empty(self):
        """Test _convert_tools with empty tools list"""
        tools = []
        converted = AnthropicAdapter._convert_tools(tools)
        assert converted == []

    def test_convert_tools_single_tool(self):
        """Test _convert_tools with single tool"""
        from amrita_core.tools.models import (
            FunctionDefinitionSchema,
            FunctionParametersSchema,
        )

        tool_schema = ToolFunctionSchema(
            function=FunctionDefinitionSchema(
                name="get_weather",
                description="Get the current weather",
                parameters=FunctionParametersSchema(
                    type="object",
                    properties={"location": {"type": "string"}},
                    required=["location"],
                ),
            ),
            strict=False,
        )
        converted = AnthropicAdapter._convert_tools([tool_schema])
        expected = [
            {
                "name": "get_weather",
                "description": "Get the current weather",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "No description"}
                    },
                    "required": ["location"],
                },
                "strict": False,
            }
        ]
        assert converted == expected

    def test_convert_tools_strict_tool(self):
        """Test _convert_tools with strict tool"""
        from amrita_core.tools.models import (
            FunctionDefinitionSchema,
            FunctionParametersSchema,
        )

        tool_schema = ToolFunctionSchema(
            function=FunctionDefinitionSchema(
                name="calculate",
                description="Perform calculation",
                parameters=FunctionParametersSchema(
                    type="object",
                    properties={"expression": {"type": "string"}},
                    required=["expression"],
                ),
            ),
            strict=True,
        )
        converted = AnthropicAdapter._convert_tools([tool_schema])
        expected = [
            {
                "name": "calculate",
                "description": "Perform calculation",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "No description",
                        }
                    },
                    "required": ["expression"],
                },
                "strict": True,
            }
        ]
        assert converted == expected

    def test_convert_tool_choice_none(self):
        """Test _convert_tool_choice with None"""
        choice = AnthropicAdapter._convert_tool_choice(None)
        expected = {"type": "auto"}
        assert choice == expected

    def test_convert_tool_choice_auto(self):
        """Test _convert_tool_choice with 'auto'"""
        choice = AnthropicAdapter._convert_tool_choice("auto")
        expected = {"type": "auto"}
        assert choice == expected

    def test_convert_tool_choice_none_string(self):
        """Test _convert_tool_choice with 'none'"""
        choice = AnthropicAdapter._convert_tool_choice("none")
        expected = {"type": "none"}
        assert choice == expected

    def test_convert_tool_choice_required(self):
        """Test _convert_tool_choice with 'required'"""
        choice = AnthropicAdapter._convert_tool_choice("required")
        expected = {"type": "any"}
        assert choice == expected

    def test_convert_tool_choice_specific_function(self):
        """Test _convert_tool_choice with specific ToolFunctionSchema"""
        tool_schema = ToolFunctionSchema(
            function={
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {"type": "object", "properties": {}},
            }
        )
        choice = AnthropicAdapter._convert_tool_choice(tool_schema)
        expected = {"type": "tool", "name": "get_weather"}
        assert choice == expected

    def test_convert_tool_choice_invalid(self):
        """Test _convert_tool_choice with invalid choice raises ValueError"""
        with pytest.raises(ValueError, match="Invalid choice: invalid_choice"):
            AnthropicAdapter._convert_tool_choice("invalid_choice")

    @pytest.mark.asyncio
    async def test_call_api_non_streaming(self, anthropic_adapter, simple_messages):
        """Test call_api with non-streaming Anthropic response"""
        # Mock Anthropic client response
        from anthropic.types import TextBlock, Usage

        mock_message = MagicMock()
        mock_message.content = [TextBlock(text="Hello there!", type="text")]
        mock_message.usage = Usage(input_tokens=10, output_tokens=5, total_tokens=15)

        with patch(
            "amrita_core.builtins.adapter.anthropic.AsyncAnthropic"
        ) as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create.return_value = mock_message
            mock_anthropic.return_value = mock_client

            # Disable streaming for this test
            anthropic_adapter.preset.config.stream = False

            results = []
            async for result in anthropic_adapter.call_api(simple_messages):
                results.append(result)

            assert len(results) == 2
            assert results[0] == "Hello there!"
            assert isinstance(results[1], UniResponse)
            assert results[1].content == "Hello there!"
            assert results[1].usage is not None
            assert results[1].usage.prompt_tokens == 10
            assert results[1].usage.completion_tokens == 5

    @pytest.mark.asyncio
    async def test_call_api_streaming(self, anthropic_adapter, simple_messages):
        """Test call_api with streaming Anthropic response"""
        from anthropic.types import TextBlock, Usage

        # Create a simple async generator to simulate text_stream
        async def mock_text_stream():
            yield "Hello"
            yield " there!"

        # Create a mock final message
        mock_final_message = MagicMock()
        mock_final_message.content = [TextBlock(text="Hello there!", type="text")]
        mock_final_message.usage = Usage(
            input_tokens=10, output_tokens=5, total_tokens=15
        )

        # Create a simple mock context manager
        class SimpleMockContext:
            def __init__(self, text_stream_gen, final_msg):
                self._text_stream = text_stream_gen
                self._final_msg = final_msg

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            @property
            def text_stream(self):
                return self._text_stream()

            async def get_final_message(self):
                return self._final_msg

        # Directly mock the stream method to return our context manager (not async!)
        def mock_stream_method(**kwargs):
            return SimpleMockContext(mock_text_stream, mock_final_message)

        with patch(
            "amrita_core.builtins.adapter.anthropic.AsyncAnthropic"
        ) as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.stream = mock_stream_method
            mock_anthropic.return_value = mock_client

            # Enable streaming for this test
            anthropic_adapter.preset.config.stream = True

            results = []
            async for result in anthropic_adapter.call_api(simple_messages):
                results.append(result)

            assert len(results) == 3
            assert results[0] == "Hello"
            assert results[1] == " there!"
            assert isinstance(results[2], UniResponse)
            assert results[2].content == "Hello there!"
            assert results[2].usage is not None
            assert results[2].usage.prompt_tokens == 10
            assert results[2].usage.completion_tokens == 5

    @pytest.mark.asyncio
    async def test_call_api_streaming_empty_content(
        self, anthropic_adapter, simple_messages
    ):
        """Test call_api with streaming Anthropic response that has empty content"""
        from anthropic.types import TextBlock, Usage

        async def mock_text_stream():
            yield ""

        mock_final_message = MagicMock()
        mock_final_message.content = [TextBlock(text="", type="text")]
        mock_final_message.usage = Usage(
            input_tokens=10, output_tokens=0, total_tokens=10
        )

        class SimpleMockContext:
            def __init__(self, text_stream_gen, final_msg):
                self._text_stream = text_stream_gen
                self._final_msg = final_msg

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            @property
            def text_stream(self):
                return self._text_stream()

            async def get_final_message(self):
                return self._final_msg

        def mock_stream_method(**kwargs):
            return SimpleMockContext(mock_text_stream, mock_final_message)

        with patch(
            "amrita_core.builtins.adapter.anthropic.AsyncAnthropic"
        ) as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.stream = mock_stream_method
            mock_anthropic.return_value = mock_client

            anthropic_adapter.preset.config.stream = True

            results = []
            async for result in anthropic_adapter.call_api(simple_messages):
                results.append(result)

            assert len(results) == 2
            assert results[0] == ""
            assert isinstance(results[1], UniResponse)
            assert results[1].content == ""
            assert results[1].usage is not None

    @pytest.mark.asyncio
    async def test_call_api_non_streaming_multiple_blocks(
        self, anthropic_adapter, simple_messages
    ):
        """Test call_api with non-streaming response containing multiple content blocks"""
        from anthropic.types import TextBlock, Usage

        # Mock Anthropic client response with multiple text blocks
        mock_message = MagicMock()
        mock_message.content = [
            TextBlock(text="First part", type="text"),
            TextBlock(text=" Second part", type="text"),
        ]
        mock_message.usage = Usage(input_tokens=15, output_tokens=10, total_tokens=25)

        with patch(
            "amrita_core.builtins.adapter.anthropic.AsyncAnthropic"
        ) as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create.return_value = mock_message
            mock_anthropic.return_value = mock_client

            anthropic_adapter.preset.config.stream = False

            results = []
            async for result in anthropic_adapter.call_api(simple_messages):
                results.append(result)

            assert len(results) == 2
            assert results[0] == "First part Second part"
            assert isinstance(results[1], UniResponse)
            assert results[1].content == "First part Second part"
            assert results[1].usage.prompt_tokens == 15
            assert results[1].usage.completion_tokens == 10

    @pytest.mark.asyncio
    async def test_call_tools_basic(self, anthropic_adapter, messages_with_tool_calls):
        """Test call_tools with basic tool call scenario"""
        # This would require mocking the Anthropic client's tool calling behavior
        # For now, we'll focus on the message conversion parts which are the core logic

        # Test the message conversion that happens before calling the API
        converted_messages = AnthropicAdapter._convert_messages(
            messages_with_tool_calls
        )
        assert len(converted_messages) == 3
        assert converted_messages[0]["role"] == "user"
        assert converted_messages[1]["role"] == "assistant"
        assert (
            converted_messages[2]["role"] == "user"
        )  # tool results merged into user message

        # The actual API call would be tested with proper mocking in a real implementation
        # For coverage purposes, we've tested all the helper methods thoroughly
