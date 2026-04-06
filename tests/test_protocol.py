import asyncio
from io import BytesIO

import pytest

from amrita_core.config import AmritaConfig, set_config
from amrita_core.protocol import (
    AdapterManager,
    ImageMessage,
    MessageContent,
    MessageWithMetadata,
    ModelAdapter,
    RawMessageContent,
    StringMessageContent,
    get_image_format,
)
from amrita_core.types import ModelPreset


# Initialize config for tests
@pytest.fixture(autouse=True)
def setup_config():
    """Initialize AmritaConfig for tests"""
    set_config(AmritaConfig())


class TestMessageContent:
    def test_abstract_message_content(self):
        """Test that MessageContent is abstract and cannot be instantiated"""
        with pytest.raises(TypeError):
            MessageContent("test")  # type: ignore

    def test_string_message_content(self):
        """Test StringMessageContent functionality"""
        text = "Hello, world!"
        msg = StringMessageContent(text)

        assert msg.type == "string"
        assert msg.text == text
        assert msg.get_content() == text
        assert str(msg) == text

    def test_raw_message_content(self):
        """Test RawMessageContent functionality"""
        raw_data = {"key": "value", "number": 42}
        msg = RawMessageContent(raw_data)

        assert msg.type == "raw"
        assert msg.raw_data == raw_data
        assert msg.get_content() == raw_data
        assert str(msg) == str(raw_data)

    def test_message_with_metadata(self):
        """Test MessageWithMetadata functionality"""
        content = "Test message"
        metadata = {"type": "info", "extra_type": "notification", "content": "details"}
        msg = MessageWithMetadata(content, metadata)

        assert msg.type == "metadata"
        assert msg.content == content
        assert msg.metadata == metadata
        assert msg.get_content() == content
        assert msg.get_metadata() == metadata
        assert msg.get_full_content() == {"content": content, "metadata": metadata}
        assert str(msg) == content


class TestImageMessage:
    @pytest.fixture
    def sample_image_bytes(self):
        # Create a simple PNG header for testing
        return b"\x89PNG\r\n\x1a\n" + b"\x00" * 20  # Minimal PNG signature + dummy data

    def test_image_message_initialization(self, sample_image_bytes):
        """Test ImageMessage initialization with different input types"""
        # Test with URL string
        url_msg = ImageMessage("https://example.com/image.png")
        assert url_msg.image == "https://example.com/image.png"

        # Test with BytesIO
        bytesio_msg = ImageMessage(BytesIO(sample_image_bytes))
        assert isinstance(bytesio_msg.image, BytesIO)

        # Test with bytes
        bytes_msg = ImageMessage(sample_image_bytes)
        assert bytes_msg.image == sample_image_bytes

    def test_get_image_format_with_valid_png(self, sample_image_bytes):
        """Test get_image_format with valid PNG data"""
        result = get_image_format(sample_image_bytes)
        assert result == "png"

    def test_get_image_format_with_invalid_data(self):
        """Test get_image_format with invalid image data"""
        invalid_data = b"This is not an image"
        result = get_image_format(invalid_data)
        assert result is None

    def test_image_message_get_content_url(self):
        """Test ImageMessage get_content with URL"""
        url = "https://example.com/image.png"
        msg = ImageMessage(url)
        assert msg.get_content() == f"![]({url})"

    def test_image_message_get_content_bytes(self, sample_image_bytes):
        """Test ImageMessage get_content with bytes"""
        msg = ImageMessage(sample_image_bytes)
        content = msg.get_content()
        assert content.startswith("![](data:image/png;base64,")

    def test_image_message_get_content_unsupported_format(self):
        """Test ImageMessage get_content with unsupported format"""
        unsupported_data = b"not an image format"
        msg = ImageMessage(unsupported_data)
        assert msg.get_content() == "[Unsupported image format]"

    # Skip complex curl tests for now as they require more sophisticated mocking
    @pytest.mark.skip(reason="Complex aiohttp mocking requires more setup")
    @pytest.mark.asyncio
    async def test_image_message_curl_image(self):
        pass

    @pytest.mark.skip(reason="Complex aiohttp mocking requires more setup")
    @pytest.mark.asyncio
    async def test_image_message_curl_image_error(self):
        pass

    @pytest.mark.asyncio
    async def test_image_message_save_to(self, tmp_path, sample_image_bytes):
        """Test ImageMessage save_to method"""
        test_file = tmp_path / "test_image.png"

        # Test with bytes
        msg = ImageMessage(sample_image_bytes)
        await msg.save_to(test_file)
        assert test_file.exists()
        assert test_file.read_bytes() == sample_image_bytes

        # Test with BytesIO
        bytesio_msg = ImageMessage(BytesIO(sample_image_bytes))
        test_file2 = tmp_path / "test_image2.png"
        await bytesio_msg.save_to(test_file2)
        assert test_file2.exists()


class TestAdapterManager:
    def test_singleton_pattern(self):
        """Test AdapterManager singleton pattern"""
        manager1 = AdapterManager()
        manager2 = AdapterManager()
        assert manager1 is manager2

    def test_adapter_registration_and_retrieval(self):
        """Test adapter registration and retrieval"""
        manager = AdapterManager()

        # Clear existing adapters for clean test
        manager._adapter_class.clear()

        class TestAdapter(ModelAdapter):
            __abstract__ = True  # Mark as abstract to avoid auto-registration

            @staticmethod
            def get_adapter_protocol():
                return "test-protocol"

        # Register adapter manually
        manager.register_adapter(TestAdapter)

        # Retrieve adapter
        retrieved = manager.get_adapter("test-protocol")
        assert retrieved == TestAdapter

        # Test safe_get_adapter
        safe_retrieved = manager.safe_get_adapter("test-protocol")
        assert safe_retrieved == TestAdapter

        # Test safe_get_adapter with non-existent protocol
        none_retrieved = manager.safe_get_adapter("non-existent")
        assert none_retrieved is None

        # Test get_adapter with non-existent protocol (should raise)
        with pytest.raises(ValueError, match="No adapter found for protocol"):
            manager.get_adapter("non-existent")

    def test_adapter_override_functionality(self):
        """Test adapter override functionality"""
        manager = AdapterManager()
        manager._adapter_class.clear()

        class OriginalAdapter(ModelAdapter):
            __abstract__ = True

            @staticmethod
            def get_adapter_protocol():
                return "override-test"

        class OverrideAdapter(ModelAdapter):
            __abstract__ = True
            __override__ = True

            @staticmethod
            def get_adapter_protocol():
                return "override-test"

        # Register original adapter
        manager.register_adapter(OriginalAdapter)

        # Register override adapter (should work due to __override__ = True)
        manager.register_adapter(OverrideAdapter)

        # Verify override worked
        retrieved = manager.get_adapter("override-test")
        assert retrieved == OverrideAdapter

    def test_multiple_protocol_registration(self):
        """Test registration with multiple protocols"""
        manager = AdapterManager()
        manager._adapter_class.clear()

        class MultiProtocolAdapter(ModelAdapter):
            __abstract__ = True

            @staticmethod
            def get_adapter_protocol():
                return ("protocol1", "protocol2", "protocol3")

        manager.register_adapter(MultiProtocolAdapter)

        for protocol in ["protocol1", "protocol2", "protocol3"]:
            retrieved = manager.get_adapter(protocol)
            assert retrieved == MultiProtocolAdapter

    def test_protocol_type_validation(self):
        """Test protocol type validation"""
        manager = AdapterManager()
        manager._adapter_class.clear()

        class InvalidProtocolAdapter(ModelAdapter):
            __abstract__ = True

            @staticmethod
            def get_adapter_protocol():  # type: ignore
                return ("valid", 123)  # Contains non-string

        with pytest.raises(
            TypeError,
            match="Model protocol adapter must be a string or tuple of strings",
        ):
            manager.register_adapter(InvalidProtocolAdapter)


class TestModelAdapterAbstractMethods:
    def test_model_adapter_abstract_methods(self):
        """Test that ModelAdapter abstract methods raise NotImplementedError"""

        class ConcreteAdapter(ModelAdapter):
            __abstract__ = True

            @staticmethod
            def get_adapter_protocol():
                return "concrete-test"

        adapter = ConcreteAdapter(ModelPreset(name="test", base_url="test"))

        # Test call_tools raises NotImplementedError
        with pytest.raises(NotImplementedError):
            asyncio.run(adapter.call_tools([], []))

        # Test get_adapter_protocol works
        assert adapter.get_adapter_protocol() == "concrete-test"
        assert adapter.protocol == "concrete-test"
