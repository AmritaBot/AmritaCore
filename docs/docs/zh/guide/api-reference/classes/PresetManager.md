# PresetManager

PresetManager 类提供了一个基于单例模式的 AI 模型预设管理系统。

## 概述

**PresetManager 是 AmritaCore 中管理模型预设的推荐方式。** 与其手动创建和处理 `ModelPreset` 实例，不如使用 PresetManager 来集中管理预设，这样可以确保一致性并减少配置错误。

当未明确选择预设时，系统将**自动 fallback 到默认预设**。这种 fallback 机制确保即使预设选择失败或未指定，您的应用程序仍能继续工作。

## 属性

- `_default_preset` (ModelPreset | None): 未指定预设时使用的默认预设
- `_presets` (dict[str, ModelPreset]): 所有已注册预设的内部存储

## 方法

### `__new__() -> Self`

创建或返回 PresetManager 的单例实例。

### `__init__() -> None`

初始化 PresetManager（由于单例模式，仅运行一次）。

### `set_default_preset(preset: ModelPreset | str) -> None`

设置未选择特定预设时使用的默认预设。

**参数：**

- `preset`: `ModelPreset` 对象或现有预设的名称

**示例：**

```python
from amrita_core.preset import PresetManager
from amrita_core.types import ModelPreset

manager = PresetManager()

# 使用 ModelPreset 对象设置
preset = ModelPreset(model="gpt-3.5-turbo", api_key="your-key")
manager.set_default_preset(preset)

# 或使用预设名称设置
manager.set_default_preset("my-preset-name")
```

### `get_default_preset() -> ModelPreset`

返回默认预设。如果尚未设置默认值，它将从可用预设中自动随机选择一个预设。

**返回值：**

- `ModelPreset`: 默认预设配置

**示例：**

```python
manager = PresetManager()
default = manager.get_default_preset()
print(f"默认预设：{default.name}")
```

### `get_preset(name: str) -> ModelPreset`

按名称检索特定预设。

**参数：**

- `name`: 预设的标识符名称

**返回值：**

- `ModelPreset`: 请求的预设配置

**异常：**

- `ValueError`: 如果预设名称不存在

**示例：**

```python
try:
    preset = manager.get_preset("gpt-4-preset")
except ValueError as e:
    print(f"预设不存在：{e}")
```

### `add_preset(preset: ModelPreset) -> None`

向管理器添加新预设。

**参数：**

- `preset`: 要注册的 `ModelPreset` 对象

**异常：**

- `ValueError`: 如果相同名称的预设已存在

**示例：**

```python
preset1 = ModelPreset(
    model="gpt-3.5-turbo",
    name="fast-model",
    api_key="your-key"
)
preset2 = ModelPreset(
    model="gpt-4",
    name="smart-model",
    api_key="your-key"
)

manager.add_preset(preset1)
manager.add_preset(preset2)
```

### `get_all_presets() -> list[ModelPreset]`

返回所有已注册的预设。

**返回值：**

- `list[ModelPreset]`: 所有预设配置的列表

**示例：**

```python
all_presets = manager.get_all_presets()
for preset in all_presets:
    print(f"- {preset.name}: {preset.model}")
```

### `async test_single_preset(preset: ModelPreset | str) -> PresetReport`

测试单个预设并返回详细报告。

**参数：**

- `preset`: `ModelPreset` 对象或预设名称

**返回值：**

- `PresetReport`: 包含测试结果的报告，包括：
  - `preset_name`: 测试的预设名称
  - `preset_data`: 预设配置
  - `test_input`: 使用的测试消息
  - `test_output`: 模型响应（如果成功）
  - `token_prompt`: 输入的 token 计数
  - `token_completion`: 输出的 token 计数
  - `status`: 测试是否成功
  - `message`: 错误消息（如果失败）
  - `time_used`: 测试耗时

**示例：**

```python
report = await manager.test_single_preset("gpt-4-preset")
if report.status:
    print(f"✓ 测试通过，耗时 {report.time_used:.2f}秒")
else:
    print(f"✗ 测试失败：{report.message}")
```

### `async test_presets() -> AsyncGenerator[PresetReport, None]`

顺序测试所有已注册的预设并生成报告。

**返回值：**

- `AsyncGenerator[PresetReport, None]`: 异步生成器，生成测试报告

**示例：**

```python
async for report in manager.test_presets():
    status = "✓" if report.status else "✗"
    print(f"{status} {report.preset_name}: {report.message or 'OK'}")
```

## 推荐使用模式

```python
from amrita_core.preset import PresetManager
from amrita_core.types import ModelPreset, ModelConfig

# 初始化管理器（单例，只需调用一次）
manager = PresetManager()

# 添加多个预设
manager.add_preset(ModelPreset(
    model="gpt-3.5-turbo",
    name="fast",
    api_key="sk-xxx",
    config=ModelConfig(stream=True)
))

manager.add_preset(ModelPreset(
    model="gpt-4",
    name="smart",
    api_key="sk-xxx",
    config=ModelConfig(stream=False)
))

# 设置默认预设（可选，但推荐）
manager.set_default_preset("fast")

# 在应用程序中使用预设
# 如果不指定预设，get_default_preset() 将自动 fallback
preset = manager.get_default_preset()  # 返回 "fast" 预设
```

## 主要优势

1. **集中管理**: 所有预设都存储和管理在一个地方
2. **单例模式**: 确保整个应用程序中的预设状态一致
3. **自动 Fallback**: 如果未选择预设，将自动选择默认值
4. **验证**: 防止重复的预设名称并验证配置
5. **测试**: 内置测试功能以验证预设功能
6. **类型安全**: 完整的类型提示，提供更好的 IDE 支持和错误预防

## 另请参见

- [ModelPreset](ModelPreset.md) - 基础预设配置类
- [AmritaConfig](AmritaConfig.md) - 整体 Amrita 配置
- [AgentRuntime](AgentRuntime.md) - 在 Agent 运行时中使用预设
