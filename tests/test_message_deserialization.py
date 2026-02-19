import pytest
from pydantic import ValidationError

from src.amrita_core.types import Content, ImageContent, Message, TextContent


def test_message_generic_validation():
    """Test if Message deserialization properly validates based on generic type."""

    # Test 1: String content should work with Message[str]
    string_data = {"role": "user", "content": "Hello world"}
    msg_str = Message[str].model_validate(string_data)
    assert msg_str.content == "Hello world"

    # Test 2: Content sequence should work with Message[Sequence[Content]]
    from collections.abc import Sequence

    content_data = {
        "role": "user",
        "content": [
            {"type": "text", "text": "Hello"},
            {
                "type": "image_url",
                "image_url": {"url": "https://example.com/image.jpg"},
            },
        ],
    }
    msg_content = Message[Sequence[Content]].model_validate(content_data)
    assert len(msg_content.content) == 2
    assert isinstance(msg_content.content[0], TextContent)
    assert isinstance(msg_content.content[1], ImageContent)

    # Test 3: Using unparameterized Message should be more permissive
    # This is the current behavior in the codebase
    msg_unparam = Message.model_validate(string_data)
    assert msg_unparam.content == "Hello world"

    # Test 4: Wrong content type with parameterized Message should fail
    with pytest.raises(ValidationError):
        Message[str].model_validate(content_data)  # Trying to parse Content[] as str

    with pytest.raises(ValidationError):
        Message[Sequence[Content]].model_validate(
            {"role": "user", "content": "not a list"}
        )


def test_current_codebase_behavior():
    """Test how the current codebase handles Message deserialization."""

    # This simulates what happens in the current codebase
    # where Message.model_validate() is called without type parameters

    string_data = {"role": "user", "content": "Hello world"}
    content_data = {"role": "user", "content": [{"type": "text", "text": "Hello"}]}

    # Both should work because unparameterized Message treats content as Any
    msg1 = Message.model_validate(string_data)
    msg2 = Message.model_validate(content_data)

    # But we lose type safety - the same Message class instance
    # could have different content types
    assert isinstance(msg1.content, str)
    assert isinstance(msg2.content, list)
