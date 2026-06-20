# DirtyAwareBaseModel

A Pydantic base model that extends [BaseModel](BaseModel.md) with automatic dirty-mark tracking for mutation detection.

## Description

`DirtyAwareBaseModel` tracks which fields have been modified since the last `clean()` call. It wraps mutable containers (`list`, `dict`, `set`) with dirty-aware proxies so that even in-place mutations (e.g., `list.append()`) are detected. This is particularly useful for backend persistence scenarios where only changed fields need to be saved.

## Inheritance

`DirtyAwareBaseModel` extends both `BaseModel` and [`DirtyAwareModel`](DirtyAwareModel.md) (from `amrita_core.dirty`), combining Pydantic model features with automatic mutation tracking.

## Dirty Tracking Methods

- `is_dirty(name: str | None = None) -> bool`: Check whether a specific attribute (or any attribute) has been modified
- `get_dirty_vars() -> set[str]`: Return the set of all dirty attribute names
- `clean()`: Reset the dirty state, clearing all tracked changes

## Auto-Wrapped Containers

When a `list`, `dict`, or `set` field is accessed, it is automatically wrapped with a dirty-aware proxy:

- [`DirtyList`](DirtyList.md): Wraps `list` — tracks `append`, `extend`, `insert`, `remove`, `pop`, `clear`, `__setitem__`, `__delitem__`, `__iadd__`, `__imul__`
- [`DirtyDict`](DirtyDict.md): Wraps `dict` — tracks `__setitem__`, `__delitem__`, `pop`, `popitem`, `clear`, `update`, `setdefault`
- [`DirtySet`](DirtySet.md): Wraps `set` — tracks `add`, `remove`, `discard`, `pop`, `clear`, `__ior__`, `__iand__`, `__isub__`, `__ixor__`

## Usage

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
assert m.is_dirty("tags")  # Detected via DirtyList proxy

m.clean()
assert not m.is_dirty()
```

## Notes

- `MemoryModel` uses `DirtyAwareBaseModel` as its base, enabling backends to efficiently detect conversation changes
- The `dirty_exclude__` tuple can be set on subclasses to exclude certain attributes from tracking
