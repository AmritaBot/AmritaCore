# ModelAdapter

`ModelAdapter` 是一个数据类，作为 AmritaCore 中模型协议适配器的基类。

## 概述

`ModelAdapter` 类提供了统一的接口，用于将不同的 AI 模型提供商（如 OpenAI、Anthropic 等）集成到 AmritaCore 框架中。

## 类定义

```python
from dataclasses import dataclass, field
from amrita_core.base.adapter import ModelAdapter

@dataclass
class ModelAdapter:
    preset: ModelPreset
    config: AmritaConfig = field(default_factory=get_config)
    __override__: bool = False
```

## 属性

### `preset`

- **类型**：[`ModelPreset`](ModelPreset.md)
- **描述**：包含模型名称、API 密钥、基础 URL 和其他设置的模型预设配置

### `config`

- **类型**：[`AmritaConfig`](AmritaConfig.md)
- **描述**：适配器的全局配置

### `__override__`

- **类型**：`bool`
- **描述**：是否允许覆盖具有相同协议的现有适配器。默认 `False`

## 抽象方法

### `get_adapter_protocol()`

子类必须实现此方法以返回此适配器支持的协议标识符。
