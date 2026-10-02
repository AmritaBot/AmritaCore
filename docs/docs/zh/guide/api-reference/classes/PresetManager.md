# PresetManager

PresetManager 类为 AI 模型预设提供基于单例的管理系统。

## 概述

**PresetManager 是管理 AmritaCore 中模型预设的推荐方式。** 不应手动创建和处理 `ModelPreset` 实例，而应使用 PresetManager 集中管理预设，确保一致性并减少配置错误。

当未通过 `set_default_preset()` 设置默认预设时，调用 `get_default_preset()` 会**快速失败**并抛出 `RuntimeError`。这种显式行为能及早暴露配置错误，而不是静默地挑选任意预设。

## 属性

- `_default_preset` (ModelPreset | None)：未指定预设时使用的默认预设
- `_presets` (dict[str, ModelPreset])：所有已注册预设的内部存储

## 方法

### `__new__() -> Self`

创建或返回 PresetManager 的单例实例。

### `__init__() -> None`

初始化 PresetManager（由于单例模式，只执行一次）。

### `set_default_preset(preset: ModelPreset | str) -> None`

设置未选择特定预设时使用的默认预设。

**参数：**

- `preset`：`ModelPreset` 对象或现有预设的名称

**示例：**

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

返回通过 `set_default_preset()` 设置的默认预设。若未设置默认预设，它会**快速失败**并抛出 `RuntimeError`——请先调用 `set_default_preset()`。

**返回：**

- `ModelPreset`：默认预设配置

**示例：**

```python
manager = PresetManager()
default = manager.get_default_preset()
print(f"Default preset: {default.name}")
```

### `get_preset(name: str) -> ModelPreset`

按名称获取特定预设。

**参数：**

- `name`：预设的标识名称

**返回：**

- `ModelPreset`：请求的预设配置

**抛出：**

- `ValueError`：预设名称不存在时

**示例：**

```python
try:
    preset = manager.get_preset("gpt-4-preset")
except ValueError as e:
    print(f"Preset not found: {e}")
```

### `add_preset(preset: ModelPreset) -> None`

向管理器添加新预设。

**参数：**

- `preset`：要注册的 `ModelPreset` 对象

**抛出：**

- `ValueError`：已存在同名预设时

**示例：**

```python
preset1 = ModelPreset(model="gpt-3.5-turbo", name="fast-model", api_key="your-key")
preset2 = ModelPreset(model="gpt-4", name="smart-model", api_key="your-key")

manager.add_preset(preset1)
manager.add_preset(preset2)
```

### `get_all_presets() -> list[ModelPreset]`

返回所有已注册的预设。

**返回：**

- `list[ModelPreset]`：所有预设配置的列表

**示例：**

```python
all_presets = manager.get_all_presets()
for preset in all_presets:
    print(f"- {preset.name}: {preset.model}")
```

### `async test_single_preset(preset: ModelPreset | str) -> PresetReport`

测试单个预设并返回详细报告。

**参数：**

- `preset`：`ModelPreset` 对象或预设名称

**返回：**

- `PresetReport`：包含测试结果的报告，包括：
  - `preset_name`：被测预设的名称
  - `preset_data`：预设配置
  - `test_input`：使用的测试消息
  - `test_output`：模型响应（若成功）
  - `token_prompt`：输入的 token 数
  - `token_completion`：输出的 token 数
  - `status`：测试是否成功
  - `message`：错误消息（若失败）
  - `time_used`：测试耗时

**示例：**

```python
report = await manager.test_single_preset("gpt-4-preset")
if report.status:
    print(f"✓ Test passed in {report.time_used:.2f}s")
else:
    print(f"✗ Test failed: {report.message}")
```

### `async test_presets() -> AsyncGenerator[PresetReport, None]`

依次测试所有已注册的预设并逐个产出报告。

**返回：**

- `AsyncGenerator[PresetReport, None]`：产出测试报告的异步生成器

**示例：**

```python
async for report in manager.test_presets():
    status = "✓" if report.status else "✗"
    print(f"{status} {report.preset_name}: {report.message or 'OK'}")
```

## 推荐用法

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

# Set a default preset (required before get_default_preset())
manager.set_default_preset("fast")

# Use presets in your application
# get_default_preset() raises RuntimeError if no default was set
preset = manager.get_default_preset()  # Returns "fast" preset
```

## 关键优势

1. **集中管理**：所有预设都存储并集中管理在一处
2. **单例模式**：确保应用中预设状态一致
3. **快速失败**：未设置默认预设就调用 `get_default_preset()` 会立即抛出 `RuntimeError`，及早暴露配置错误
4. **校验**：阻止重复的预设名称并校验配置
5. **测试**：内置测试能力以验证预设功能
6. **类型安全**：完整的类型提示，提供更好的 IDE 支持并防止错误

## 另请参阅

- [ModelPreset](ModelPreset.md) - 底层的预设配置类
- [AmritaConfig](AmritaConfig.md) - Amrita 整体配置
- [AgentRuntime](AgentRuntime.md) - 在 agent 运行时中使用预设
