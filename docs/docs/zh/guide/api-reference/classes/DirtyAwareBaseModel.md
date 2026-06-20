# DirtyAwareBaseModel

扩展 [BaseModel](BaseModel.md) 的 Pydantic 基础模型，增加了用于变更检测的自动脏标记追踪。

## 描述

`DirtyAwareBaseModel` 追踪自上次 `clean()` 调用以来哪些字段被修改过。它用脏感知代理包装可变容器（`list`、`dict`、`set`），以便即使就地修改（例如 `list.append()`）也能被检测到。这对于仅需要保存已更改字段的后端持久化场景特别有用。

## 继承

`DirtyAwareBaseModel` 同时扩展了 `BaseModel` 和 [`DirtyAwareModel`](DirtyAwareModel.md)（来自 `amrita_core.dirty`），将 Pydantic 模型特性与自动变更追踪相结合。

## 脏追踪方法

- `is_dirty(name: str | None = None) -> bool`: 检查特定属性（或任意属性）是否已被修改
- `get_dirty_vars() -> set[str]`: 返回所有脏属性名称的集合
- `clean()`: 重置脏状态，清除所有追踪的变更

## 自动包装的容器

当访问 `list`、`dict` 或 `set` 字段时，它会自动被脏感知代理包装：

- [`DirtyList`](DirtyList.md): 包装 `list` — 追踪 `append`、`extend`、`insert`、`remove`、`pop`、`clear`、`__setitem__`、`__delitem__`、`__iadd__`、`__imul__`
- [`DirtyDict`](DirtyDict.md): 包装 `dict` — 追踪 `__setitem__`、`__delitem__`、`pop`、`popitem`、`clear`、`update`、`setdefault`
- [`DirtySet`](DirtySet.md): 包装 `set` — 追踪 `add`、`remove`、`discard`、`pop`、`clear`、`__ior__`、`__iand__`、`__isub__`、`__ixor__`

## 用法

```python
from amrita_core.types import DirtyAwareBaseModel
from pydantic import Field

class MyModel(DirtyAwareBaseModel):
    name: str = ""
    tags: list[str] = Field(default_factory=list)

m = MyModel(name="test")
assert not m.is_dirty()

m.name = "updated"
assert m.is_dirty("name")
assert m.get_dirty_vars() == {"name"}

m.tags.append("new-tag")
assert m.is_dirty("tags")  # 通过 DirtyList 代理检测

m.clean()
assert not m.is_dirty()
```

## 注意

- `MemoryModel` 使用 `DirtyAwareBaseModel` 作为基类，使后端能够高效地检测对话变更
- 可以在子类上设置 `dirty_exclude__` 元组，以排除某些属性不受追踪
