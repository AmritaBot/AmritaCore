# PresetManager

PresetManager 类为 AI 模型预设提供基于单例的管理系统。

## 概述

**PresetManager 是管理 AmritaCore 中模型预设的推荐方式。** 应使用 PresetManager 来集中管理预设，确保一致性并减少配置错误。

## 属性

- `_default_preset` (ModelPreset | None)：未指定预设时使用的默认预设
- `_presets` (dict[str, ModelPreset])：所有已注册预设的内部存储

## 方法

### `set_default_preset(preset: ModelPreset | str) -> None`

设置未选择特定预设时使用的默认预设。

```python
from amrita_core.preset import PresetManager

manager = PresetManager()
manager.set_default_preset("my-preset-name")
```

### `get_default_preset() -> ModelPreset`

获取默认预设。
