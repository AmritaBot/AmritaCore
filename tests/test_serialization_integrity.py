import json

from amrita_core.types import (
    Function,
    ImageContent,
    MemoryModel,
    Message,
    ModelConfig,
    ModelPreset,
    TextContent,
    ToolCall,
    ToolResult,
    UniResponse,
)


def test_message_serialization_roundtrip():
    """Test that Message serialization and deserialization preserves data integrity"""

    # Test 1: String content
    original_msg = Message(role="user", content="Hello world")
    dumped = original_msg.model_dump()
    restored = Message.model_validate(dumped)

    assert original_msg.role == restored.role
    assert original_msg.content == restored.content
    assert type(original_msg.content) == type(restored.content)  # noqa: E721

    # Test 2: None content
    original_msg_none = Message(role="user", content=None)
    dumped_none = original_msg_none.model_dump()
    restored_none = Message.model_validate(dumped_none)

    assert original_msg_none.role == restored_none.role
    assert original_msg_none.content == restored_none.content

    # Test 3: Text content list
    text_content = [TextContent(text="Hello world")]
    original_msg_text = Message(role="user", content=text_content)
    dumped_text = original_msg_text.model_dump()
    restored_text = Message.model_validate(dumped_text)

    assert original_msg_text.role == restored_text.role
    assert len(original_msg_text.content) == len(restored_text.content)
    assert isinstance(restored_text.content[0], TextContent)
    assert original_msg_text.content[0].text == restored_text.content[0].text

    # Test 4: Mixed content list
    mixed_content = [
        TextContent(text="Hello"),
        ImageContent(image_url={"url": "https://example.com/image.jpg"}),  # pyright: ignore[reportArgumentType]
    ]
    original_msg_mixed = Message(role="user", content=mixed_content)
    dumped_mixed = original_msg_mixed.model_dump()
    restored_mixed = Message.model_validate(dumped_mixed)

    assert original_msg_mixed.role == restored_mixed.role
    assert len(original_msg_mixed.content) == len(restored_mixed.content)
    assert isinstance(restored_mixed.content[0], TextContent)
    assert isinstance(restored_mixed.content[1], ImageContent)
    assert original_msg_mixed.content[0].text == restored_mixed.content[0].text
    assert (
        original_msg_mixed.content[1].image_url.url
        == restored_mixed.content[1].image_url.url
    )


def test_tool_result_serialization_roundtrip():
    """Test that ToolResult serialization and deserialization preserves data integrity"""
    original_tool = ToolResult(
        role="tool",
        name="test_function",
        content="function result",
        tool_call_id="call_12345",
    )
    dumped = original_tool.model_dump()
    restored = ToolResult.model_validate(dumped)

    assert original_tool.role == restored.role
    assert original_tool.name == restored.name
    assert original_tool.content == restored.content
    assert original_tool.tool_call_id == restored.tool_call_id


def test_tool_call_serialization_roundtrip():
    """Test that ToolCall serialization and deserialization preserves data integrity"""
    original_function = Function(
        arguments='{"param1": "value1", "param2": 42}', name="test_function"
    )
    original_tool_call = ToolCall(
        id="call_12345", function=original_function, type="function"
    )
    dumped = original_tool_call.model_dump()
    restored = ToolCall.model_validate(dumped)

    assert original_tool_call.id == restored.id
    assert original_tool_call.type == restored.type
    assert original_tool_call.function.name == restored.function.name
    assert original_tool_call.function.arguments == restored.function.arguments


def test_uni_response_serialization_roundtrip():
    """Test that UniResponse serialization and deserialization preserves data integrity"""

    # Test with string content and tool calls
    function = Function(arguments='{"x": 5}', name="add")
    tool_call = ToolCall(id="call_1", function=function)

    original_response = UniResponse(
        role="assistant", content="Calculating...", tool_calls=[tool_call]
    )
    dumped = original_response.model_dump()
    restored = UniResponse.model_validate(dumped)

    assert original_response.role == restored.role
    assert original_response.content == restored.content
    assert len(original_response.tool_calls) == len(restored.tool_calls)
    assert original_response.tool_calls[0].id == restored.tool_calls[0].id
    assert (
        original_response.tool_calls[0].function.name
        == restored.tool_calls[0].function.name
    )
    assert (
        original_response.tool_calls[0].function.arguments
        == restored.tool_calls[0].function.arguments
    )


def test_memory_model_serialization_roundtrip():
    """Test that MemoryModel serialization and deserialization preserves data integrity"""
    # Create messages with different content types
    messages = [
        Message(role="user", content="User message"),
        Message(role="assistant", content=[TextContent(text="Assistant response")]),
        ToolResult(
            role="tool",
            name="test_tool",
            content="Tool result",
            tool_call_id="call_123",
        ),
    ]

    original_memory = MemoryModel(
        messages=messages, abstract="Test summary", time=1234567890.0
    )
    dumped = original_memory.model_dump()
    restored = MemoryModel.model_validate(dumped)

    assert original_memory.abstract == restored.abstract
    assert original_memory.time == restored.time
    assert len(original_memory.messages) == len(restored.messages)

    # Verify each message type and content
    for orig_msg, restored_msg in zip(original_memory.messages, restored.messages):
        if isinstance(orig_msg, Message):
            assert isinstance(restored_msg, Message)
            assert orig_msg.role == restored_msg.role
            if isinstance(orig_msg.content, str):
                assert orig_msg.content == restored_msg.content
            elif isinstance(orig_msg.content, list):
                assert len(orig_msg.content) == len(restored_msg.content)
                for orig_content, restored_content in zip(
                    orig_msg.content, restored_msg.content
                ):
                    assert type(orig_content) == type(restored_content)  # noqa: E721
                    if isinstance(orig_content, TextContent):
                        assert orig_content.text == restored_content.text
                    elif isinstance(orig_content, ImageContent):
                        assert (
                            orig_content.image_url.url == restored_content.image_url.url
                        )
        elif isinstance(orig_msg, ToolResult):
            assert isinstance(restored_msg, ToolResult)
            assert orig_msg.name == restored_msg.name
            assert orig_msg.content == restored_msg.content
            assert orig_msg.tool_call_id == restored_msg.tool_call_id


def test_model_config_serialization_roundtrip():
    """Test that ModelConfig serialization and deserialization preserves data integrity"""
    original_config = ModelConfig(
        top_k=100, top_p=0.9, temperature=0.7, stream=True, multimodal=True
    )
    dumped = original_config.model_dump()
    restored = ModelConfig.model_validate(dumped)

    assert original_config.top_k == restored.top_k
    assert original_config.top_p == restored.top_p
    assert original_config.temperature == restored.temperature
    assert original_config.stream == restored.stream
    assert original_config.multimodal == restored.multimodal


def test_model_preset_serialization_roundtrip():
    """Test that ModelPreset serialization and deserialization preserves data integrity"""
    original_preset = ModelPreset(
        model="gpt-4",
        name="production_preset",
        base_url="https://api.custom-provider.com",
        api_key="secret_key_123",
        protocol="custom_adapter",
        config=ModelConfig(top_k=50, temperature=0.8),
        extra={"custom_param": "custom_value", "timeout": 30},
    )
    dumped = original_preset.model_dump()
    restored = ModelPreset.model_validate(dumped)

    assert original_preset.model == restored.model
    assert original_preset.name == restored.name
    assert original_preset.base_url == restored.base_url
    assert original_preset.api_key == restored.api_key
    assert original_preset.protocol == restored.protocol
    assert original_preset.config.top_k == restored.config.top_k
    assert original_preset.config.temperature == restored.config.temperature
    assert original_preset.extra == restored.extra


def test_json_compatibility():
    """Test that model_dump produces JSON-compatible output"""
    msg = Message(role="user", content="Test message")
    dumped = msg.model_dump()

    # Should be serializable to JSON without errors
    json_str = json.dumps(dumped)
    parsed_back = json.loads(json_str)

    # Should be able to validate from the parsed JSON
    restored = Message.model_validate(parsed_back)
    assert restored.role == "user"
    assert restored.content == "Test message"


def test_nested_serialization_consistency():
    """Test that nested objects maintain consistency through serialization cycles"""
    # Create a complex nested structure
    original_messages = [
        Message(
            role="user",
            content=[
                TextContent(text="Hello"),
                ImageContent(image_url={"url": "https://example.com/image1.jpg"}),  # pyright: ignore[reportArgumentType]
            ],
        ),
        Message(
            role="assistant",
            content="Response with tool call",
            tool_calls=[
                ToolCall(
                    id="call_1",
                    function=Function(
                        name="search_web", arguments='{"query": "test search"}'
                    ),
                )
            ],
        ),
        ToolResult(
            role="tool",
            name="search_web",
            content='{"results": ["result1", "result2"]}',
            tool_call_id="call_1",
        ),
    ]

    # Multiple serialization-deserialization cycles
    current_data = original_messages
    for cycle in range(3):
        # Serialize all messages
        dumped_messages = [msg.model_dump() for msg in current_data]
        # Deserialize back
        restored_messages = []
        for dumped_msg in dumped_messages:
            if "name" in dumped_msg and "tool_call_id" in dumped_msg:
                # This is a ToolResult
                restored_messages.append(ToolResult.model_validate(dumped_msg))
            else:
                # This is a Message
                restored_messages.append(Message.model_validate(dumped_msg))
        current_data = restored_messages

    # Final comparison with original
    assert len(original_messages) == len(current_data)

    # Check first message (user with content list)
    orig_user_msg = original_messages[0]
    final_user_msg = current_data[0]
    assert orig_user_msg.role == final_user_msg.role
    assert len(orig_user_msg.content) == len(final_user_msg.content)
    assert orig_user_msg.content[0].text == final_user_msg.content[0].text
    assert (
        orig_user_msg.content[1].image_url.url
        == final_user_msg.content[1].image_url.url
    )

    # Check second message (assistant with tool calls)
    orig_assistant_msg = original_messages[1]
    final_assistant_msg = current_data[1]
    assert orig_assistant_msg.role == final_assistant_msg.role
    assert orig_assistant_msg.content == final_assistant_msg.content
    assert len(orig_assistant_msg.tool_calls) == len(final_assistant_msg.tool_calls)
    assert (
        orig_assistant_msg.tool_calls[0].function.name
        == final_assistant_msg.tool_calls[0].function.name
    )
    assert (
        orig_assistant_msg.tool_calls[0].function.arguments
        == final_assistant_msg.tool_calls[0].function.arguments
    )

    # Check third message (tool result)
    orig_tool_result = original_messages[2]
    final_tool_result = current_data[2]
    assert orig_tool_result.role == final_tool_result.role
    assert orig_tool_result.name == final_tool_result.name
    assert orig_tool_result.content == final_tool_result.content
    assert orig_tool_result.tool_call_id == final_tool_result.tool_call_id
