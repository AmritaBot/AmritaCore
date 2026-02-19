from src.amrita_core.types import CT_MAP, ImageContent, Message, TextContent


def test_message_content_validation_with_registered_types():
    """Test that Message correctly validates content using registered Content types."""

    # Test data with mixed content types
    test_data = {
        "role": "user",
        "content": [
            {"type": "text", "text": "Hello world"},
            {
                "type": "image_url",
                "image_url": {"url": "https://example.com/image.jpg"},
            },
        ],
    }

    # Deserialize the message
    msg = Message.model_validate(test_data)

    # Verify that content is properly typed
    assert isinstance(msg.content, list)
    assert len(msg.content) == 2

    # First item should be TextContent
    assert isinstance(msg.content[0], TextContent)
    assert msg.content[0].type == "text"
    assert msg.content[0].text == "Hello world"

    # Second item should be ImageContent
    assert isinstance(msg.content[1], ImageContent)
    assert msg.content[1].type == "image_url"
    assert msg.content[1].image_url.url == "https://example.com/image.jpg"


def test_ct_map_registration():
    """Test that CT_MAP contains the correct registered types."""
    assert "text" in CT_MAP
    assert "image_url" in CT_MAP
    assert CT_MAP["text"] == TextContent
    assert CT_MAP["image_url"] == ImageContent


def test_message_string_content_still_works():
    """Test that Message still works with string content."""
    string_data = {"role": "user", "content": "Simple text message"}

    msg = Message.model_validate(string_data)
    assert isinstance(msg.content, str)
    assert msg.content == "Simple text message"


def test_message_none_content_still_works():
    """Test that Message works with None content."""
    none_data = {"role": "assistant", "content": None}

    msg = Message.model_validate(none_data)
    assert msg.content is None
