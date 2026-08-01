# BaseModel

BaseModel 类是 AmritaCore 中所有数据模型的基类，继承自 Pydantic 的 BaseModel。

## 描述

BaseModel 类扩展了 Pydantic BaseModel，添加了字典式访问能力：

- `__str__` 和 `__repr__`：将模型转换为 JSON 字符串
- `__getitem__` 和 `__setitem__`：允许字典式访问和设置模型字段
- 保留 Pydantic 的所有验证和序列化功能

## 相关类

- `DirtyAwareBaseModel`：扩展 BaseModel，添加自动脏标记跟踪用于变更检测

## 使用

BaseModel 是所有数据模型的基类，不应直接实例化。它被其他模型类（如 Message、ModelConfig 等）继承使用。
