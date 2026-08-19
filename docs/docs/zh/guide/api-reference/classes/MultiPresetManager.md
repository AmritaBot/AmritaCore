# MultiPresetManager

MultiPresetManager 类管理多个模型预设。

## 描述

MultiPresetManager 将预设存储在按名称索引的字典中，支持默认预设选择、单个/并行预设测试以及生成 `PresetReport` 结果。

## 方法

- `set_default_preset(preset: ModelPreset | str) -> None`：设置默认预设（未注册则自动添加）
- `get_default_preset() -> ModelPreset`：获取默认预设；未设置则引发 `RuntimeError`（快速失败）
- `get_preset(name: str) -> ModelPreset`：按名称获取预设；未找到则引发 `ValueError`
- `add_preset(preset: ModelPreset) -> None`：添加预设；名称已存在则引发 `ValueError`
- `get_all_presets() -> list[ModelPreset]`：列出所有预设
- `async test_single_preset(preset: ModelPreset | str) -> PresetReport`：通过协议适配器测试单个预设
- `async test_presets() -> AsyncGenerator[PresetReport]`：顺序测试所有预设

## 示例

```python
from amrita_core.preset import MultiPresetManager, ModelPreset

manager = MultiPresetManager()
preset = ModelPreset(name="gpt", base_url="https://api.example.com", api_key="...")
manager.add_preset(preset)
manager.set_default_preset("gpt")

report = await manager.test_single_preset("gpt")
print(report.status, report.time_used)
```
