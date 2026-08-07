from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amrita_core.base.adapter import AdapterManager
from amrita_core.config import AmritaConfig
from amrita_core.libchat import (
    _call_with_reflection,
    _validate_msg_list,
    call_completion,
    get_last_response,
    get_tokens,
    text_generator,
    tools_caller,
)
from amrita_core.tools.models import ToolFunctionSchema
from amrita_core.types import (
    CONTENT_LIST_TYPE,
    Message,
    ToolResult,
    UniResponse,
    UniResponseUsage,
)


class TestTextGenerator:
    """Test text_generator function"""

    def test_text_generator_with_string_content(self):
        """Test text generator with string content"""
        messages: CONTENT_LIST_TYPE = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]

        result = list(text_generator(messages))
        assert result == ["Hello", "Hi there!"]

    def test_text_generator_with_list_content(self):
        """Test text generator with list content"""
        messages = [
            Message(
                role="user",
                content=[
                    {"type": "text", "text": "Hello"},
                    {"type": "image_url", "image_url": {"url": "http://example.com"}},
                ],  # type: ignore
            ),
            Message(role="assistant", content="Response"),
        ]

        result = list(text_generator(messages))
        assert result == ["Hello", "Response"]

    def test_text_generator_with_split_role(self):
        """Test text generator with split_role enabled"""
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
            ToolResult(
                role="tool", content="Tool result", tool_call_id="123", name="test_tool"
            ),
        ]

        result = list(text_generator(messages, split_role=True))
        expected = [
            "<User's query>Hello",
            "<BOT's response>Hi there!",
            "<Tool call>Tool result",
        ]
        assert result == expected

    def test_text_generator_with_none_content(self):
        """Test text generator with None content"""
        messages = [
            Message(role="user", content=None),
            Message(role="assistant", content="Hi there!"),
        ]

        result = list(text_generator(messages))
        assert result == ["Hi there!"]


class TestValidateMsgList:
    """Test _validate_msg_list function"""

    def test_validate_msg_list_with_valid_dicts(self):
        """Test validation with valid message dictionaries"""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        result = _validate_msg_list(messages)
        assert len(result) == 2
        assert isinstance(result[0], Message)
        assert result[0].role == "user"
        assert result[0].content == "Hello"

    def test_validate_msg_list_with_tool_messages(self):
        """Test validation with tool message dictionaries"""
        messages = [
            {"role": "user", "content": "Hello"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "123",
                        "type": "function",
                        "function": {"name": "test_tool", "arguments": "{}"},
                    }
                ],
            },
            {
                "role": "tool",
                "content": "Tool result",
                "tool_call_id": "123",
                "name": "test_tool",
            },
        ]

        result = _validate_msg_list(messages)
        assert len(result) == 3
        assert isinstance(result[0], Message)
        assert isinstance(result[1], Message)
        assert isinstance(result[2], ToolResult)

    def test_validate_msg_list_with_message_objects(self):
        """Test validation with existing Message objects"""
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]

        result = _validate_msg_list(messages)
        assert result == messages  # Should return the same objects

    def test_validate_msg_list_missing_role(self):
        """Test validation with missing role field"""
        messages = [{"content": "Hello"}]

        with pytest.raises(
            ValueError, match="Message dictionary is missing 'role' field"
        ):
            _validate_msg_list(messages)

    def test_validate_msg_list_invalid_format(self):
        """Test validation with invalid message format"""
        messages = [{"role": "user", "invalid_field": "value"}]

        with pytest.raises(ValueError, match="Payload at"):
            _validate_msg_list(messages)


class TestThinkingFilter:
    """Test _apply_thinking_filter: must not mutate original Message objects.

    Providers like DeepSeek require assistant ``reasoning_content`` to be
    passed back verbatim on subsequent requests — stripping it from the
    live objects would cause HTTP 400.
    """

    def _thinking_config(self, content_mode: str):
        from amrita_core.types import ThinkingConfig

        return ThinkingConfig(thinking_type="enabled", content_mode=content_mode)  # type: ignore[arg-type]

    def test_never_mode_does_not_mutate_original(self):
        from amrita_core.libchat import _apply_thinking_filter

        msgs = [
            Message(
                role="assistant",
                content="answer",
                reasoning_content="thinking text",
            ),
            Message(role="user", content="next question"),
        ]
        validated = list(msgs)
        _apply_thinking_filter(validated, self._thinking_config("never"))  # type: ignore

        # The validated list has a stripped *copy*...
        assert validated[0].reasoning_content is None
        # ...but the original object keeps its reasoning_content.
        assert msgs[0].reasoning_content == "thinking text"

    def test_by_tool_keeps_reasoning_for_tool_calls(self):
        from amrita_core.libchat import _apply_thinking_filter
        from amrita_core.types import ToolCall

        msgs = [
            Message(
                role="assistant",
                content=None,
                reasoning_content="thinking with tools",
                tool_calls=[
                    ToolCall(
                        id="t1",
                        function={"name": "search", "arguments": "{}"},  # pyright: ignore[reportArgumentType]
                    )
                ],
            )
        ]
        validated = list(msgs)
        _apply_thinking_filter(validated, self._thinking_config("by-tool"))  # type: ignore
        # Same object identity when nothing is stripped (no copy needed).
        assert validated[0] is msgs[0]
        assert validated[0].reasoning_content == "thinking with tools"

    def test_by_tool_strips_plain_assistant(self):
        from amrita_core.libchat import _apply_thinking_filter

        msgs = [
            Message(
                role="assistant",
                content="answer",
                reasoning_content="thinking text",
            )
        ]
        validated = list(msgs)
        _apply_thinking_filter(validated, self._thinking_config("by-tool"))  # type: ignore
        assert validated[0].reasoning_content is None
        assert msgs[0].reasoning_content == "thinking text"  # original intact

    def test_optional_passthrough_no_copy(self):
        from amrita_core.libchat import _apply_thinking_filter

        msgs = [
            Message(
                role="assistant",
                content="answer",
                reasoning_content="thinking text",
            )
        ]
        validated = list(msgs)
        _apply_thinking_filter(validated, self._thinking_config("optional"))  # type: ignore
        assert validated[0] is msgs[0]
        assert validated[0].reasoning_content == "thinking text"

    def test_disabled_thinking_no_op(self):
        from amrita_core.libchat import _apply_thinking_filter
        from amrita_core.types import ThinkingConfig

        msgs = [
            Message(
                role="assistant",
                content="answer",
                reasoning_content="thinking text",
            )
        ]
        validated = list(msgs)
        _apply_thinking_filter(
            validated,  # type: ignore
            ThinkingConfig(thinking_type="disabled", content_mode="never"),  # type: ignore
        )  # type: ignore
        assert validated[0] is msgs[0]
        assert validated[0].reasoning_content == "thinking text"


class TestCallWithReflection:
    """Test _call_with_reflection function"""

    @pytest.fixture
    def mock_adapter_class(self):
        """Create a mock adapter class"""
        mock_adapter = MagicMock()
        mock_adapter.__name__ = "MockAdapter"  # Add __name__ attribute
        mock_adapter_instance = AsyncMock()
        mock_adapter.return_value = mock_adapter_instance
        mock_adapter_instance.some_method = AsyncMock(return_value="test_result")
        mock_adapter.get_type.return_value = "text-gen"
        return mock_adapter

    @pytest.mark.asyncio
    async def test_call_with_reflection_undefined_protocol(self):
        """Test call with undefined protocol"""
        from amrita_core.config import AmritaConfig
        from amrita_core.types import ModelPreset

        with patch.object(AdapterManager, "safe_get_adapter", return_value=None):
            preset = ModelPreset(
                model="test-model",
                name="test-preset",
                api_key="test-key",
                protocol="undefined-protocol",
            )
            config = AmritaConfig()

            async def test_call_func(adapter, *args, **kwargs):
                return "should not be called"

            with pytest.raises(
                ValueError, match="Undefined protocol adapter: undefined-protocol"
            ):
                await _call_with_reflection(preset, test_call_func, config)


class TestToolsCaller:
    """Test tools_caller function"""

    @pytest.mark.asyncio
    async def test_tools_caller_basic(self):
        """Test basic tools caller functionality"""
        from amrita_core.config import AmritaConfig
        from amrita_core.types import ModelPreset

        messages: CONTENT_LIST_TYPE = [
            Message(role="user", content="What's the weather?")
        ]
        tools = [
            ToolFunctionSchema.model_validate(
                {
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather info",
                        "parameters": {"type": "object", "properties": {}},
                    }
                }
            )
        ]

        preset = ModelPreset(
            model="test-model",
            name="test-preset",
            api_key="test-key",
            protocol="test-protocol",
        )
        config = AmritaConfig()

        # Mock the _call_with_reflection to avoid actual adapter calls
        with patch("amrita_core.libchat._call_with_reflection") as mock_call:
            mock_call.return_value = UniResponse(
                content=None, tool_calls=[], usage=None
            )

            result = await tools_caller(messages, tools, preset, None, config)

            assert result.tool_calls == []
            assert result.content is None
            mock_call.assert_called_once()


class TestCallCompletion:
    """Test call_completion function"""

    @pytest.mark.asyncio
    async def test_call_completion_basic(self):
        """Test basic call completion functionality"""
        from amrita_core.config import AmritaConfig
        from amrita_core.types import ModelPreset

        messages: CONTENT_LIST_TYPE = [Message(role="user", content="Hello")]

        preset = ModelPreset(
            model="test-model",
            name="test-preset",
            api_key="test-key",
            protocol="test-protocol",
        )
        config = AmritaConfig()

        # Mock the _call_with_reflection and adapter responses
        async def mock_call_completion_return():
            yield "Hello"
            yield " world"
            yield UniResponse(content="Hello world", tool_calls=[], usage=None)

        with patch("amrita_core.libchat._call_with_reflection") as mock_call:
            mock_call.return_value = lambda: mock_call_completion_return()

            chunks = []
            async for chunk in call_completion(messages, preset, config):
                chunks.append(chunk)

            assert len(chunks) == 3
            assert chunks[0] == "Hello"
            assert chunks[1] == " world"
            assert isinstance(chunks[2], UniResponse)
            assert chunks[2].content == "Hello world"


class TestGetLastResponse:
    """Test get_last_response function"""

    @pytest.mark.asyncio
    async def test_get_last_response_success(self):
        """Test successful extraction of last response"""

        async def mock_generator():
            yield "chunk1"
            yield "chunk2"
            yield UniResponse(content="response1", tool_calls=None, usage=None)
            yield "chunk3"
            yield UniResponse(content="response2", tool_calls=None, usage=None)

        result = await get_last_response(mock_generator())
        assert isinstance(result, UniResponse)
        assert result.content == "response2"

    @pytest.mark.asyncio
    async def test_get_last_response_no_response(self):
        """Test error when no response is found"""

        async def mock_generator():
            yield "chunk1"
            yield "chunk2"

        with pytest.raises(RuntimeError, match=r"No response found in generator."):
            await get_last_response(mock_generator())


# get_tokens


class TestGetTokens:
    """Unit tests for the get_tokens function — the token-counting fallback
    used when the API does not return usage data."""

    @staticmethod
    def _make_response(
        content: str = "response",
        prompt: int | None = 10,
        completion: int | None = 5,
        total: int | None = 15,
    ) -> UniResponse[str, None]:
        return UniResponse(
            content=content,
            tool_calls=[],
            usage=UniResponseUsage(
                prompt_tokens=prompt,  # type: ignore[arg-type]
                completion_tokens=completion,  # type: ignore[arg-type]
                total_tokens=total,  # type: ignore[arg-type]
            ),
        )

    def test_api_has_full_usage_returns_directly(self):
        """When the API provides complete usage data it is returned as-is."""
        memory: CONTENT_LIST_TYPE = [Message(role="user", content="Hello")]
        response = self._make_response(prompt=12, completion=3, total=15)
        result = get_tokens(memory, response)
        assert result is response.usage
        assert result is not None
        assert result.prompt_tokens == 12
        assert result.completion_tokens == 3
        assert result.total_tokens == 15

    def test_api_usage_missing_total_does_not_return_directly(self):
        """When total_tokens is None, the guard rejects it even if prompt and
        completion are present, falling back to local estimation."""
        memory: CONTENT_LIST_TYPE = [Message(role="user", content="Hello")]
        response = UniResponse(
            content="ok",
            tool_calls=[],
            usage=UniResponseUsage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=None,  # type: ignore[arg-type]
            ),
        )
        result = get_tokens(memory, response, config=AmritaConfig())  # pyright: ignore[reportArgumentType]
        # Falls back to hybrid_token_count, so result is a new object
        assert result is not response.usage
        assert isinstance(result, UniResponseUsage)
        assert result.prompt_tokens >= 0
        assert result.completion_tokens >= 0
        assert result.total_tokens == result.prompt_tokens + result.completion_tokens

    def test_no_tokenizer_config_returns_none(self):
        """When no_tokenizer is True and the API returns no usage, result is None."""
        config = AmritaConfig()
        config.function_config.no_tokenizer = True
        memory: CONTENT_LIST_TYPE = [Message(role="user", content="Hello")]
        response = UniResponse(content="ok", tool_calls=[], usage=None)
        result = get_tokens(memory, response, config=config)  # pyright: ignore[reportArgumentType]
        assert result is None

    def test_fallback_local_estimation(self):
        """When the API returns no usage, hybrid_token_count is used as a
        rough estimate."""
        config = AmritaConfig()
        config.function_config.no_tokenizer = False
        memory: CONTENT_LIST_TYPE = [
            Message(role="user", content="Hello world"),
            Message(role="assistant", content="Hi there!"),
        ]
        response = UniResponse(content="Sure, I can help.", tool_calls=[], usage=None)
        result = get_tokens(memory, response, config=config)  # pyright: ignore[reportArgumentType]
        assert result is not None
        assert isinstance(result, UniResponseUsage)
        assert result.prompt_tokens > 0
        assert result.completion_tokens > 0
        assert result.total_tokens == result.prompt_tokens + result.completion_tokens

    def test_response_usage_is_none_triggers_fallback(self):
        """response.usage = None always triggers the fallback path."""
        config = AmritaConfig()
        memory: CONTENT_LIST_TYPE = []
        response: UniResponse[str, None] = UniResponse(
            content="x", tool_calls=[], usage=None
        )  # pyright: ignore[reportAssignmentType]
        result = get_tokens(memory, response, config=config)
        assert result is not None
        assert isinstance(result, UniResponseUsage)
