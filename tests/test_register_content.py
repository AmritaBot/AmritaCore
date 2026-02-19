from typing import Literal

from pydantic import Field

from src.amrita_core.types import (
    CT_MAP,
    Content,
    ImageContent,
    TextContent,
    register_content,
)


def test_register_content_existing_classes():
    """Test that existing Content classes are properly registered."""
    # Clear CT_MAP first to test registration
    original_map = CT_MAP.copy()
    CT_MAP.clear()

    try:
        # Register existing classes
        register_content(TextContent)
        register_content(ImageContent)

        # Verify registration
        assert "text" in CT_MAP
        assert "image_url" in CT_MAP
        assert CT_MAP["text"] == TextContent
        assert CT_MAP["image_url"] == ImageContent

    finally:
        # Restore original map
        CT_MAP.clear()
        CT_MAP.update(original_map)


def test_register_content_with_default():
    """Test registering a Content class with explicit default value."""
    CT_MAP.clear()

    class CustomContent(Content[Literal["custom"]]):
        type: Literal["custom"] = "custom"
        custom_field: str = Field(..., description="Custom field")

    register_content(CustomContent)

    assert "custom" in CT_MAP
    assert CT_MAP["custom"] == CustomContent


def test_register_content_without_default():
    """Test registering a Content class without explicit default (should use Literal type)."""
    CT_MAP.clear()

    class AnotherContent(Content[Literal["another"]]):
        type: Literal["another"]  # No default, should extract from Literal

    register_content(AnotherContent)

    assert "another" in CT_MAP
    assert CT_MAP["another"] == AnotherContent
