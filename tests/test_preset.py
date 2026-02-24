from unittest.mock import MagicMock, patch

import pytest

from amrita_core.preset import (
    TEST_MSG_LIST,
    TEST_MSG_PROMPT,
    TEST_MSG_USER,
    MultiPresetManager,
    PresetManager,
    PresetReport,
)
from amrita_core.types import (
    Message,
    ModelConfig,
    ModelPreset,
    TextContent,
    ToolCall,
    UniResponse,
)


class MockModelAdapter:
    """Mock adapter for testing"""

    def __init__(self, preset):
        self.preset = preset

    async def call_api(self, messages):
        """Mock API call that yields a UniResponse"""
        # Create a proper UniResponse with all required fields
        response = UniResponse[str, list[ToolCall] | None](
            content="Hello! I'm a test assistant.",
            tool_calls=None,  # This is required
            usage=None,
        )
        yield response


def create_test_preset(
    name: str = "test_preset", protocol: str = "__main__"
) -> ModelPreset:
    """Helper function to create a test preset"""
    return ModelPreset(
        name=name,
        model="test-model",
        protocol=protocol,
        config=ModelConfig(),
        api_key="test-key",
    )


class TestMultiPresetManager:
    """Test MultiPresetManager class"""

    def test_init(self):
        """Test initialization"""
        manager = MultiPresetManager()
        assert manager._presets == {}
        assert manager._default_preset is None

    def test_add_preset(self):
        """Test adding a preset"""
        manager = MultiPresetManager()
        preset = create_test_preset("test1")

        manager.add_preset(preset)
        assert "test1" in manager._presets
        assert manager._presets["test1"] == preset

    def test_add_preset_duplicate(self):
        """Test adding duplicate preset raises ValueError"""
        manager = MultiPresetManager()
        preset1 = create_test_preset("test1")
        preset2 = create_test_preset("test1")  # Same name

        manager.add_preset(preset1)
        with pytest.raises(ValueError, match="Preset test1 already exists"):
            manager.add_preset(preset2)

    def test_get_preset(self):
        """Test getting a preset by name"""
        manager = MultiPresetManager()
        preset = create_test_preset("test1")
        manager.add_preset(preset)

        retrieved = manager.get_preset("test1")
        assert retrieved == preset

    def test_get_preset_not_found(self):
        """Test getting non-existent preset raises ValueError"""
        manager = MultiPresetManager()
        with pytest.raises(ValueError, match="Preset nonexistent not found"):
            manager.get_preset("nonexistent")

    def test_get_all_presets(self):
        """Test getting all presets"""
        manager = MultiPresetManager()
        preset1 = create_test_preset("test1")
        preset2 = create_test_preset("test2")
        manager.add_preset(preset1)
        manager.add_preset(preset2)

        all_presets = manager.get_all_presets()
        assert len(all_presets) == 2
        assert preset1 in all_presets
        assert preset2 in all_presets

    def test_set_default_preset_by_object(self):
        """Test setting default preset by ModelPreset object"""
        manager = MultiPresetManager()
        preset = create_test_preset("default_test")
        manager.add_preset(preset)

        manager.set_default_preset(preset)
        assert manager._default_preset == preset

    def test_set_default_preset_by_string(self):
        """Test setting default preset by string name"""
        manager = MultiPresetManager()
        preset = create_test_preset("string_test")
        manager.add_preset(preset)

        manager.set_default_preset("string_test")
        assert manager._default_preset == preset

    def test_set_default_preset_auto_add(self):
        """Test setting default preset auto-adds if not present"""
        manager = MultiPresetManager()
        preset = create_test_preset("auto_add_test")

        # Should add the preset automatically
        manager.set_default_preset(preset)
        assert "auto_add_test" in manager._presets
        assert manager._default_preset == preset

    def test_get_default_preset_existing(self):
        """Test getting default preset when it exists"""
        manager = MultiPresetManager()
        preset = create_test_preset("existing_default")
        manager._default_preset = preset

        result = manager.get_default_preset()
        assert result == preset

    def test_get_default_preset_random_choice(self):
        """Test getting default preset chooses randomly when none set"""
        manager = MultiPresetManager()
        preset1 = create_test_preset("random1")
        preset2 = create_test_preset("random2")
        manager.add_preset(preset1)
        manager.add_preset(preset2)

        # Should pick one of the existing presets
        result = manager.get_default_preset()
        assert result in [preset1, preset2]
        assert manager._default_preset == result


class TestPresetManagerSingleton:
    """Test PresetManager singleton behavior"""

    def test_singleton_instance(self):
        """Test that PresetManager returns the same instance"""
        manager1 = PresetManager()
        manager2 = PresetManager()
        assert manager1 is manager2

    def test_singleton_initialization(self):
        """Test that PresetManager initializes only once"""
        # Reset singleton state for testing
        PresetManager._instance = None
        PresetManager._initialized = False

        manager1 = PresetManager()
        # Check that _presets is initialized
        assert hasattr(manager1, "_presets")
        assert manager1._presets == {}

        # Create another instance
        manager2 = PresetManager()
        # Should be the same instance and not re-initialized
        assert manager1 is manager2


class TestPresetTesting:
    """Test preset testing functionality"""

    @pytest.mark.asyncio
    async def test_test_single_preset_success(self):
        """Test successful preset testing"""
        manager = MultiPresetManager()
        preset = create_test_preset("test_success", "__main__")

        # Mock the adapter manager to return our mock adapter
        with patch("amrita_core.preset.AdapterManager") as mock_adapter_manager_class:
            mock_instance = MagicMock()
            mock_adapter_manager_class.return_value = mock_instance
            mock_instance.safe_get_adapter.return_value = MockModelAdapter

            # Mock hybrid_token_count
            with patch("amrita_core.preset.hybrid_token_count", return_value=10):
                report = await manager.test_single_preset(preset)

                assert isinstance(report, PresetReport)
                assert report.preset_name == "test_success"
                assert report.status is True
                assert report.message == ""
                assert report.test_output is not None
                assert report.token_prompt == 10
                assert report.token_completion > 0

    @pytest.mark.asyncio
    async def test_test_single_preset_by_string(self):
        """Test testing preset by string name"""
        manager = MultiPresetManager()
        preset = create_test_preset("test_by_string", "__main__")
        manager.add_preset(preset)

        with patch("amrita_core.preset.AdapterManager") as mock_adapter_manager_class:
            mock_instance = MagicMock()
            mock_adapter_manager_class.return_value = mock_instance
            mock_instance.safe_get_adapter.return_value = MockModelAdapter

            with patch("amrita_core.preset.hybrid_token_count", return_value=10):
                report = await manager.test_single_preset("test_by_string")

                assert report.preset_name == "test_by_string"
                assert report.status is True

    @pytest.mark.asyncio
    async def test_test_single_preset_undefined_protocol(self):
        """Test preset testing with undefined protocol adapter"""
        manager = MultiPresetManager()
        preset = create_test_preset("test_undefined", "undefined_protocol")

        with patch("amrita_core.preset.AdapterManager") as mock_adapter_manager_class:
            mock_instance = MagicMock()
            mock_adapter_manager_class.return_value = mock_instance
            mock_instance.safe_get_adapter.return_value = None

            with patch("amrita_core.preset.hybrid_token_count", return_value=10):
                report = await manager.test_single_preset(preset)

                assert report.status is False
                assert (
                    "Undefined protocol adapter: undefined_protocol" in report.message
                )
                assert report.test_output is None

    @pytest.mark.asyncio
    async def test_test_single_preset_exception(self):
        """Test preset testing with exception during API call"""

        class FailingMockAdapter:
            def __init__(self, preset):
                self.preset = preset

            async def call_api(self, messages):
                # This should be an async generator that raises an exception
                raise RuntimeError("API call failed")
                yield  # This line will never be reached

        manager = MultiPresetManager()
        preset = create_test_preset("test_exception", "__main__")

        with patch("amrita_core.preset.AdapterManager") as mock_adapter_manager_class:
            mock_instance = MagicMock()
            mock_adapter_manager_class.return_value = mock_instance
            mock_instance.safe_get_adapter.return_value = FailingMockAdapter

            with patch("amrita_core.preset.hybrid_token_count", return_value=10):
                report = await manager.test_single_preset(preset)

                assert report.status is False
                assert "API call failed" in report.message
                assert report.test_output is None

    @pytest.mark.asyncio
    async def test_test_presets_generator(self):
        """Test test_presets async generator"""
        manager = MultiPresetManager()
        preset1 = create_test_preset("gen1", "__main__")
        preset2 = create_test_preset("gen2", "__main__")
        manager.add_preset(preset1)
        manager.add_preset(preset2)

        with patch("amrita_core.preset.AdapterManager") as mock_adapter_manager_class:
            mock_instance = MagicMock()
            mock_adapter_manager_class.return_value = mock_instance
            mock_instance.safe_get_adapter.return_value = MockModelAdapter

            with patch("amrita_core.preset.hybrid_token_count", return_value=10):
                reports = []
                async for report in manager.test_presets():
                    reports.append(report)

                assert len(reports) == 2
                assert all(isinstance(r, PresetReport) for r in reports)
                assert {r.preset_name for r in reports} == {"gen1", "gen2"}
                assert all(r.status is True for r in reports)


class TestPresetReport:
    """Test PresetReport model"""

    def test_preset_report_creation(self):
        """Test creating a PresetReport"""
        preset = create_test_preset("report_test")
        test_input = (TEST_MSG_PROMPT, TEST_MSG_USER)
        test_output = Message(
            role="assistant", content=[TextContent(type="text", text="test response")]
        )

        report = PresetReport(
            preset_name="report_test",
            preset_data=preset,
            test_input=test_input,
            test_output=test_output,
            token_prompt=5,
            token_completion=3,
            status=True,
            message="",
            time_used=0.1,
        )

        assert report.preset_name == "report_test"
        assert report.preset_data == preset
        assert report.test_input == test_input
        assert report.test_output == test_output
        assert report.token_prompt == 5
        assert report.token_completion == 3
        assert report.status is True
        assert report.message == ""
        assert report.time_used == 0.1


# Test constants
def test_test_constants():
    """Test that test constants are properly defined"""
    assert TEST_MSG_PROMPT.role == "system"
    assert TEST_MSG_USER.role == "user"
    assert len(TEST_MSG_LIST) == 2
    assert TEST_MSG_LIST[0] == TEST_MSG_PROMPT
    assert TEST_MSG_LIST[1] == TEST_MSG_USER
