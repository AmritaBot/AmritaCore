# MultiPresetManager

The MultiPresetManager class manages multiple model presets.

## Description

MultiPresetManager stores presets in a name-keyed dict and supports default-preset selection, single/parallel preset testing, and generation of `PresetReport` results.

## Methods

- `set_default_preset(preset: ModelPreset | str) -> None`: Set the default preset (auto-adds if not registered)
- `get_default_preset() -> ModelPreset`: Get the default preset; falls back to a random preset with a warning if none set
- `get_preset(name: str) -> ModelPreset`: Get a preset by name; raises `ValueError` if not found
- `add_preset(preset: ModelPreset) -> None`: Add a preset; raises `ValueError` if the name already exists
- `get_all_presets() -> list[ModelPreset]`: List all presets
- `async test_single_preset(preset: ModelPreset | str) -> PresetReport`: Test a single preset through its protocol adapter
- `async test_presets() -> AsyncGenerator[PresetReport]`: Test all presets sequentially, yielding one report each

## Example

```python
from amrita_core.preset import MultiPresetManager, ModelPreset

manager = MultiPresetManager()
preset = ModelPreset(name="gpt", base_url="https://api.example.com", api_key="...")
manager.add_preset(preset)
manager.set_default_preset("gpt")

report = await manager.test_single_preset("gpt")
print(report.status, report.time_used)
```
