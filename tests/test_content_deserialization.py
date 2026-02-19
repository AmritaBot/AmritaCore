import contextlib

import pytest

from src.amrita_core.types import ImageContent, Message, TextContent


def test_message_content_discriminated_union():
    """Test that Message correctly deserializes Content subclasses based on type field."""

    # Test mixed content types
    mixed_data = {
        "role": "user",
        "content": [
            {"type": "text", "text": "Hello world"},
            {
                "type": "image_url",
                "image_url": {"url": "https://example.com/image.jpg"},
            },
        ],
    }

    msg = Message.model_validate(mixed_data)

    # Verify correct types
    assert isinstance(msg.content, list)
    assert len(msg.content) == 2
    assert isinstance(msg.content[0], TextContent)
    assert isinstance(msg.content[1], ImageContent)

    # Verify content values
    assert msg.content[0].text == "Hello world"
    assert msg.content[1].image_url.url == "https://example.com/image.jpg"
    assert msg.content[0].type == "text"
    assert msg.content[1].type == "image_url"


def test_message_string_content():
    """Test that Message still works with string content."""

    string_data = {"role": "user", "content": "Simple text message"}

    msg = Message.model_validate(string_data)
    assert isinstance(msg.content, str)
    assert msg.content == "Simple text message"


def test_message_none_content():
    """Test that Message works with None content."""

    none_data = {"role": "assistant", "content": None}

    msg = Message.model_validate(none_data)
    assert msg.content is None


def test_unknown_content_type():
    """Test behavior with unknown content type."""

    unknown_data = {
        "role": "user",
        "content": [{"type": "unknown_type", "some_field": "some_value"}],
    }

    # Should raise an error.
    with contextlib.suppress(ValueError):
        Message.model_validate(unknown_data)
        pytest.fail("Expected an error, but no error was raised.")
