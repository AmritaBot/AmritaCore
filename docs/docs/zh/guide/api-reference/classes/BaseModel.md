# BaseModel

BaseModel 类是 AmritaCore 中所有数据模型的基类，继承自 Pydantic 的 BaseModel。

## 描述

BaseModel 类扩展了 Pydantic BaseModel，增加了字典风格的访问能力（鸭子类型）：

- `__str__` 和 `__repr__`: 将模型转换为 JSON 字符串
- `__getitem__` 和 `__setitem__`: 允许以字典风格访问和设置模型字段
- 保留 Pydantic 的所有验证和序列化功能

## 特性

- 支持模型验证和数据序列化
- 支持字典风格的访问方法
- 支持 JSON 序列化和反序列化
- 集成了 Pydantic 的 Field 定义功能

## 相关类

- [`DirtyAwareBaseModel`](DirtyAwareBaseModel.md): 扩展 BaseModel，增加自动脏标记追踪以检测变更——适用于需要知道哪些字段发生了更改的后端

## 用法

BaseModel 是所有数据模型的基类，不应直接实例化。它被其他模型类（如 Message、ModelConfig 等）继承使用。
