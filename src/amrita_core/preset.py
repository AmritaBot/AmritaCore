import random
import time
import typing

from typing_extensions import Self

from .logging import debug_log
from .protocol import AdapterManager
from .tokenizer import hybrid_token_count
from .types import BaseModel, Message, ModelPreset, TextContent, UniResponse

TEST_MSG_PROMPT: Message[list[TextContent]] = Message(
    role="system",
    content=[TextContent(text="You are a helpful assistant.", type="text")],
)
TEST_MSG_USER: Message[list[TextContent]] = Message(
    role="user",
    content=[
        TextContent(text="Hello, please briefly introduce yourself.", type="text")
    ],
)

TEST_MSG_LIST: list[Message[list[TextContent]]] = [
    TEST_MSG_PROMPT,
    TEST_MSG_USER,
]


class PresetReport(BaseModel):
    preset_name: str  # Name of the preset
    preset_data: ModelPreset  # Preset data
    test_input: tuple[Message, Message]  # Test input
    test_output: Message | None  # Test output
    token_prompt: int  # Token count of the prompt
    token_completion: int  # Token count of the completion
    status: bool  # Test result
    message: str  # Test result message
    time_used: float


class MultiPresetManager:
    """
    MultiPresetManager is a class that manages presets.
    """

    _default_preset: ModelPreset | None = None
    _presets: dict[str, ModelPreset]
    _inited = False

    def __init__(self) -> None:
        if not self._inited:
            self._presets = {}
            self._inited = True

    def set_default_preset(self, preset: ModelPreset | str) -> None:
        """
        Set the default preset.
        """
        if isinstance(preset, str):
            preset = self.get_preset(preset)
        if preset.name not in self._presets:
            self.add_preset(preset)
        self._default_preset = preset

    def get_default_preset(self) -> ModelPreset:
        """
        Get the default preset.
        """
        if self._default_preset is None:
            self._default_preset = random.choice(list(self._presets.values()))
        return self._default_preset

    def get_preset(self, name: str) -> ModelPreset:
        """
        Get a preset by name.
        """
        if name not in self._presets:
            raise ValueError(f"Preset {name} not found")
        return self._presets[name]

    def add_preset(self, preset: ModelPreset) -> None:
        """
        Add a preset.
        """
        if preset.name in self._presets:
            raise ValueError(f"Preset {preset.name} already exists")
        self._presets[preset.name] = preset

    def get_all_presets(self) -> list[ModelPreset]:
        """
        Get all presets.
        """
        return list(self._presets.values())

    async def test_single_preset(self, preset: ModelPreset | str) -> PresetReport:
        """Test a single preset for parallel execution"""
        if isinstance(preset, str):
            preset = self.get_preset(preset)
        debug_log(f"Testing preset: {preset.name}...")
        prompt_tokens = hybrid_token_count(
            "".join(
                [typing.cast(TextContent, msg.content[0]).text for msg in TEST_MSG_LIST]
            )
        )

        adapter = AdapterManager().safe_get_adapter(preset.protocol)
        if adapter is None:
            return PresetReport(
                preset_name=preset.name,
                preset_data=preset,
                test_input=(TEST_MSG_PROMPT, TEST_MSG_USER),
                test_output=None,
                token_prompt=prompt_tokens,
                token_completion=0,
                status=False,
                message=f"Undefined protocol adapter: {preset.protocol}",
                time_used=0,
            )

        try:
            time_start = time.time()
            debug_log(f"Calling preset: {preset.name}...")
            data = [  # noqa: RUF015
                i
                async for i in adapter(preset).call_api(TEST_MSG_LIST)
                if isinstance(i, UniResponse)
            ][0]
            time_end = time.time()
            time_delta = time_end - time_start
            debug_log(
                f"Successfully called preset {preset.name}, took {time_delta:.2f} seconds"
            )
            return PresetReport(
                preset_name=preset.name,
                preset_data=preset,
                test_input=(TEST_MSG_PROMPT, TEST_MSG_USER),
                test_output=Message[list[TextContent]](
                    role="assistant",
                    content=[TextContent(type="text", text=data.content)],
                ),
                token_prompt=prompt_tokens,
                token_completion=hybrid_token_count(data.content),
                status=True,
                message="",
                time_used=time_delta,
            )
        except Exception as e:
            debug_log(f"Error occurred while testing preset {preset.name}: {e}")
            return PresetReport(
                preset_name=preset.name,
                preset_data=preset,
                test_input=(TEST_MSG_PROMPT, TEST_MSG_USER),
                test_output=None,
                token_prompt=prompt_tokens,
                token_completion=0,
                status=False,
                message=str(e),
                time_used=0,
            )

    async def test_presets(self) -> typing.AsyncGenerator[PresetReport, None]:
        presets: list[ModelPreset] = self.get_all_presets()
        debug_log(f"Starting to test all presets ({len(presets)} total)...")
        for preset in presets:
            yield await self.test_single_preset(preset)


class PresetManager(MultiPresetManager):
    """
    PresetManager is a singleton class that manages presets.
    """

    _instance = None
    _initialized = False

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not self.__class__._initialized:
            super().__init__()
            self.__class__._initialized = True
