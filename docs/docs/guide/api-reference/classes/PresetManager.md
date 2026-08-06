# PresetManager

The PresetManager class provides a singleton-based management system for AI model presets.

## Overview

**PresetManager is the recommended way to manage model presets in AmritaCore.** Instead of manually creating and handling `ModelPreset` instances, you should use PresetManager to centralize preset management, ensuring consistency and reducing configuration errors.

When no preset is explicitly selected, the system will **automatically fallback to a default preset**. This fallback mechanism ensures your application continues to work even if preset selection fails or is not specified.

## Properties

- `_default_preset` (ModelPreset | None): The default preset to use when none is specified
- `_presets` (dict[str, ModelPreset]): Internal storage for all registered presets

## Methods

### `__new__() -> Self`

Creates or returns the singleton instance of PresetManager.

### `__init__() -> None`

Initializes the PresetManager (only runs once due to singleton pattern).

### `set_default_preset(preset: ModelPreset | str) -> None`

Sets the default preset to use when no specific preset is selected.

**Parameters:**

- `preset`: Either a `ModelPreset` object or the name of an existing preset

**Example:**

```python
from amrita_core.preset import PresetManager
from amrita_core.types import ModelPreset

manager = PresetManager()

# Set using ModelPreset object
preset = ModelPreset(model="gpt-3.5-turbo", api_key="your-key")
manager.set_default_preset(preset)

# Or set using preset name
manager.set_default_preset("my-preset-name")
```

### `get_default_preset() -> ModelPreset`

Returns the default preset. If no default has been set, it will automatically select a random preset from available presets.

**Returns:**

- `ModelPreset`: The default preset configuration

**Example:**

```python
manager = PresetManager()
default = manager.get_default_preset()
print(f"Default preset: {default.name}")
```

### `get_preset(name: str) -> ModelPreset`

Retrieves a specific preset by name.

**Parameters:**

- `name`: The identifier name of the preset

**Returns:**

- `ModelPreset`: The requested preset configuration

**Raises:**

- `ValueError`: If the preset name doesn't exist

**Example:**

```python
try:
    preset = manager.get_preset("gpt-4-preset")
except ValueError as e:
    print(f"Preset not found: {e}")
```

### `add_preset(preset: ModelPreset) -> None`

Adds a new preset to the manager.

**Parameters:**

- `preset`: The `ModelPreset` object to register

**Raises:**

- `ValueError`: If a preset with the same name already exists

**Example:**

```python
preset1 = ModelPreset(model="gpt-3.5-turbo", name="fast-model", api_key="your-key")
preset2 = ModelPreset(model="gpt-4", name="smart-model", api_key="your-key")

manager.add_preset(preset1)
manager.add_preset(preset2)
```

### `get_all_presets() -> list[ModelPreset]`

Returns all registered presets.

**Returns:**

- `list[ModelPreset]`: A list of all preset configurations

**Example:**

```python
all_presets = manager.get_all_presets()
for preset in all_presets:
    print(f"- {preset.name}: {preset.model}")
```

### `async test_single_preset(preset: ModelPreset | str) -> PresetReport`

Tests a single preset and returns a detailed report.

**Parameters:**

- `preset`: Either a `ModelPreset` object or the preset name

**Returns:**

- `PresetReport`: A report containing test results including:
  - `preset_name`: Name of the tested preset
  - `preset_data`: The preset configuration
  - `test_input`: Test messages used
  - `test_output`: Model response (if successful)
  - `token_prompt`: Token count of input
  - `token_completion`: Token count of output
  - `status`: Whether the test succeeded
  - `message`: Error message (if failed)
  - `time_used`: Time taken for the test

**Example:**

```python
report = await manager.test_single_preset("gpt-4-preset")
if report.status:
    print(f"✓ Test passed in {report.time_used:.2f}s")
else:
    print(f"✗ Test failed: {report.message}")
```

### `async test_presets() -> AsyncGenerator[PresetReport, None]`

Tests all registered presets sequentially and yields reports.

**Returns:**

- `AsyncGenerator[PresetReport, None]`: An async generator yielding test reports

**Example:**

```python
async for report in manager.test_presets():
    status = "✓" if report.status else "✗"
    print(f"{status} {report.preset_name}: {report.message or 'OK'}")
```

## Recommended Usage Pattern

```python
from amrita_core.preset import PresetManager
from amrita_core.types import ModelPreset, ModelConfig

# Initialize the manager (singleton, only needs to be called once)
manager = PresetManager()

# Add multiple presets
manager.add_preset(
    ModelPreset(
        model="gpt-3.5-turbo",
        name="fast",
        api_key="sk-xxx",
        config=ModelConfig(stream=True),
    )
)

manager.add_preset(
    ModelPreset(
        model="gpt-4", name="smart", api_key="sk-xxx", config=ModelConfig(stream=False)
    )
)

# Set a default preset (optional, but recommended)
manager.set_default_preset("fast")

# Use presets in your application
# If you don't specify a preset, get_default_preset() will auto-fallback
preset = manager.get_default_preset()  # Returns "fast" preset
```

## Key Benefits

1. **Centralized Management**: All presets are stored and managed in one place
2. **Singleton Pattern**: Ensures consistent preset state across your application
3. **Automatic Fallback**: If no preset is selected, a default is automatically chosen
4. **Validation**: Prevents duplicate preset names and validates configurations
5. **Testing**: Built-in testing capability to verify preset functionality
6. **Type Safety**: Full type hints for better IDE support and error prevention

## See Also

- [ModelPreset](ModelPreset.md) - The underlying preset configuration class
- [AmritaConfig](AmritaConfig.md) - Overall Amrita configuration
- [AgentRuntime](AgentRuntime.md) - Using presets with the agent runtime
