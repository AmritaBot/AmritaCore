import pytest
from pydantic import ValidationError

from amrita_core.types import (
    CONTENT_LIST_TYPE_ITEM,
    ImageContent,
    Message,
    TextContent,
    ToolResult,
)


def test_message_with_empty_content_dict():
    """Test Message validation with empty content dict - this should fail"""
    # This is the problematic case from the error log
    invalid_data = {"role": "user", "content": [{}]}

    with pytest.raises(ValidationError) as exc_info:
        Message.model_validate(invalid_data)

    # Verify the error message contains the expected text
    error_str = str(exc_info.value)
    assert "Content item is missing 'type' field" in error_str


def test_message_with_valid_content_types():
    """Test Message validation with valid content types"""
    # Valid text content
    text_data = {"role": "user", "content": [{"type": "text", "text": "Hello world"}]}
    msg1 = Message.model_validate(text_data)
    assert isinstance(msg1.content[0], TextContent)
    assert msg1.content[0].text == "Hello world"

    # Valid image content
    image_data = {
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
        ],
    }
    msg2 = Message.model_validate(image_data)
    assert isinstance(msg2.content[0], ImageContent)
    assert msg2.content[0].image_url.url == "https://example.com/image.jpg"


def test_message_roundtrip_serialization():
    """Test that model_dump and model_validate work correctly together"""
    # Test with string content
    original_msg_str = Message(role="user", content="Hello world")
    dumped_str = original_msg_str.model_dump()
    restored_msg_str = Message.model_validate(dumped_str)

    assert original_msg_str.content == restored_msg_str.content
    assert original_msg_str.role == restored_msg_str.role

    # Test with text content list
    original_msg_content = Message(
        role="user", content=[TextContent(text="Hello world")]
    )
    dumped_content = original_msg_content.model_dump()
    restored_msg_content = Message.model_validate(dumped_content)

    assert len(original_msg_content.content) == len(restored_msg_content.content)
    assert original_msg_content.content[0].text == restored_msg_content.content[0].text
    assert original_msg_content.role == restored_msg_content.role


def test_message_with_mixed_content():
    """Test Message with mixed content types"""
    mixed_data = {
        "role": "user",
        "content": [
            {"type": "text", "text": "Hello"},
            {
                "type": "image_url",
                "image_url": {"url": "https://example.com/image.jpg"},
            },
        ],
    }
    msg = Message.model_validate(mixed_data)
    assert len(msg.content) == 2
    assert isinstance(msg.content[0], TextContent)
    assert isinstance(msg.content[1], ImageContent)


def test_message_with_none_content():
    """Test Message with None content"""
    none_data = {"role": "user", "content": None}
    msg = Message.model_validate(none_data)
    assert msg.content is None


def test_tool_result_validation():
    """Test ToolResult validation separately"""
    # Valid ToolResult
    tool_result_data = {
        "role": "tool",
        "name": "test_tool",
        "content": "tool result",
        "tool_call_id": "call_123",
    }
    tool_result = ToolResult.model_validate(tool_result_data)
    assert tool_result.role == "tool"
    assert tool_result.name == "test_tool"
    assert tool_result.content == "tool result"
    assert tool_result.tool_call_id == "call_123"

    # Invalid ToolResult (wrong role)
    invalid_tool_result = {
        "role": "user",  # Should be "tool"
        "name": "test_tool",
        "content": "tool result",
        "tool_call_id": "call_123",
    }
    with pytest.raises(ValidationError):
        ToolResult.model_validate(invalid_tool_result)


def test_content_list_type_item_union():
    """Test that CONTENT_LIST_TYPE_ITEM union works correctly"""
    # Test Message can be created
    msg = Message(role="user", content="test")
    assert isinstance(msg, CONTENT_LIST_TYPE_ITEM)

    # Test ToolResult can be created
    tool_result = ToolResult(
        role="tool", name="test_tool", content="result", tool_call_id="123"
    )
    assert isinstance(tool_result, CONTENT_LIST_TYPE_ITEM)


def test_message_validation_error_details():
    """Test that validation errors provide clear information"""
    # Test with completely invalid content structure
    invalid_content = {"role": "user", "content": [{"invalid": "structure"}]}

    with pytest.raises(ValidationError) as exc_info:
        Message.model_validate(invalid_content)

    error_str = str(exc_info.value)
    # Should mention either missing type field or unknown content type
    assert (
        "Content item is missing 'type' field" in error_str
        or "Unknown content type" in error_str
    )


def test_original_error_scenario():
    """Test the exact scenario from the original error log"""
    # This reproduces the exact input that caused the error
    problematic_input = {"role": "user", "content": [{}]}

    # This should raise a ValidationError with the specific error message
    with pytest.raises(ValidationError) as exc_info:
        Message.model_validate(problematic_input)

    # Check that we get the expected validation errors
    errors = exc_info.value.errors()
    assert len(errors) >= 1

    # The first error should be about missing 'type' field
    first_error = errors[0]
    assert first_error["type"] == "value_error"
    assert "Content item is missing 'type' field" in first_error["msg"]
