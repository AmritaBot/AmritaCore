"""
Dirty-mark Pydantic model for scenarios such as database ORM,
automatically tracking attribute modification status.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, SupportsIndex, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class DirtyList(list):
    def __init__(self, *args, parent: DirtyAwareModel, attr: str, **kwargs):
        """A list wrapper that automatically notifies the parent model of mutations."""
        super().__init__(*args, **kwargs)
        self._parent = parent
        self._attr = attr

    def _mark_dirty(self):
        """Notify the parent model that this attribute has been modified."""
        self._parent._mark_dirty(self._attr)

    def _wrap_value(self, value: Any) -> Any:
        """Wrap a value as a dirty-aware container if it is a list, dict or set."""
        if isinstance(value, (list, dict, set)) and not hasattr(value, "_parent"):
            return _wrap_container(value, self._parent, self._attr)
        return value

    def append(self, item):
        """Append an item and mark the attribute as dirty."""
        item = self._wrap_value(item)
        super().append(item)
        self._mark_dirty()

    def extend(self, iterable):
        """Extend the list and mark the attribute as dirty."""
        iterable = [self._wrap_value(i) for i in iterable]
        super().extend(iterable)
        self._mark_dirty()

    def insert(self, index, item):
        """Insert an item at the given index and mark the attribute as dirty."""
        item = self._wrap_value(item)
        super().insert(index, item)
        self._mark_dirty()

    def remove(self, item):
        """Remove the first occurrence of an item and mark the attribute as dirty."""
        super().remove(item)
        self._mark_dirty()

    def pop(self, index: SupportsIndex = -1):
        """Pop an item at the given index and mark the attribute as dirty."""
        result = super().pop(index)
        self._mark_dirty()
        return result

    def clear(self):
        """Clear all items and mark the attribute as dirty."""
        super().clear()
        self._mark_dirty()

    def __setitem__(self, index, item):
        """Set an item by index and mark the attribute as dirty."""
        if isinstance(index, slice):
            item = [self._wrap_value(i) for i in item]
        else:
            item = self._wrap_value(item)
        super().__setitem__(index, item)
        self._mark_dirty()

    def __delitem__(self, index):
        """Delete an item by index and mark the attribute as dirty."""
        super().__delitem__(index)
        self._mark_dirty()

    def __iadd__(self, other):
        """In-place addition and mark the attribute as dirty."""
        other = [self._wrap_value(i) for i in other]
        super().__iadd__(other)
        self._mark_dirty()
        return self

    def __imul__(self, other):
        """In-place multiplication and mark the attribute as dirty."""
        super().__imul__(other)
        self._mark_dirty()
        return self

    def __getitem__(self, index):
        """Get an item by index, wrapping nested containers as dirty-aware."""
        value = super().__getitem__(index)
        if isinstance(index, slice):
            return value
        return self._wrap_value(value)


class DirtyDict(dict):
    def __init__(self, *args, parent: DirtyAwareModel, attr: str, **kwargs):
        """A dict wrapper that automatically notifies the parent model of mutations."""
        super().__init__(*args, **kwargs)
        self._parent = parent
        self._attr = attr

    def _mark_dirty(self):
        """Notify the parent model that this attribute has been modified."""
        self._parent._mark_dirty(self._attr)

    def _wrap_value(self, value: Any) -> Any:
        """Wrap a value as a dirty-aware container if it is a list, dict or set."""
        if isinstance(value, (list, dict, set)) and not hasattr(value, "_parent"):
            return _wrap_container(value, self._parent, self._attr)
        return value

    def __setitem__(self, key, value):
        """Set a key-value pair and mark the attribute as dirty."""
        value = self._wrap_value(value)
        super().__setitem__(key, value)
        self._mark_dirty()

    def __delitem__(self, key):
        """Delete a key and mark the attribute as dirty."""
        super().__delitem__(key)
        self._mark_dirty()

    def pop(self, key, default=None):
        """Pop a key and mark the attribute as dirty."""
        result = super().pop(key, default)
        self._mark_dirty()
        return result

    def popitem(self):
        """Pop an arbitrary key-value pair and mark the attribute as dirty."""
        result = super().popitem()
        self._mark_dirty()
        return result

    def clear(self):
        """Clear all items and mark the attribute as dirty."""
        super().clear()
        self._mark_dirty()

    def update(self, *args, **kwargs):
        """Update with another dict and mark the attribute as dirty."""
        other = dict(*args, **kwargs)
        for k, v in other.items():
            other[k] = self._wrap_value(v)
        super().update(other)
        self._mark_dirty()

    def setdefault(self, key, default=None):
        """Set a default value for a key and mark the attribute as dirty if the key is new."""
        default = self._wrap_value(default)
        result = super().setdefault(key, default)
        if key not in self:
            self._mark_dirty()
        return self._wrap_value(result)

    def __getitem__(self, key):
        """Get an item by key, wrapping nested containers as dirty-aware."""
        value = super().__getitem__(key)
        return self._wrap_value(value)


class DirtySet(set):
    def __init__(self, *args, parent: DirtyAwareModel, attr: str, **kwargs):
        """A set wrapper that automatically notifies the parent model of mutations."""
        super().__init__(*args, **kwargs)
        self._parent = parent
        self._attr = attr

    def _mark_dirty(self):
        """Notify the parent model that this attribute has been modified."""
        self._parent._mark_dirty(self._attr)

    def add(self, element):
        """Add an element and mark the attribute as dirty."""
        super().add(element)
        self._mark_dirty()

    def remove(self, element):
        """Remove an element and mark the attribute as dirty."""
        super().remove(element)
        self._mark_dirty()

    def discard(self, element):
        """Discard an element and mark the attribute as dirty."""
        super().discard(element)
        self._mark_dirty()

    def pop(self):
        """Pop an arbitrary element and mark the attribute as dirty."""
        result = super().pop()
        self._mark_dirty()
        return result

    def clear(self):
        """Clear all elements and mark the attribute as dirty."""
        super().clear()
        self._mark_dirty()

    def __ior__(self, other):
        """In-place union (|=) and mark the attribute as dirty."""
        super().__ior__(other)
        self._mark_dirty()
        return self

    def __iand__(self, other):
        """In-place intersection (&=) and mark the attribute as dirty."""
        super().__iand__(other)
        self._mark_dirty()
        return self

    def __isub__(self, other):
        """In-place difference (-=) and mark the attribute as dirty."""
        super().__isub__(other)
        self._mark_dirty()
        return self

    def __ixor__(self, other):
        """In-place symmetric difference (^=) and mark the attribute as dirty."""
        super().__ixor__(other)
        self._mark_dirty()
        return self


def _wrap_container(obj: list | dict | set, parent: DirtyAwareModel, attr: str):
    """Wrap a container (list, dict, set) with the corresponding dirty-aware wrapper."""
    if isinstance(obj, list):
        return DirtyList(obj, parent=parent, attr=attr)
    if isinstance(obj, dict):
        return DirtyDict(obj, parent=parent, attr=attr)
    if isinstance(obj, set):
        return DirtySet(obj, parent=parent, attr=attr)
    return obj


class DirtyAwareModel(BaseModel):
    # Set of attribute names that have been marked as dirty.
    dirtyvars__: set[str] = Field(default_factory=set, init=False, exclude=True)
    dirty_exclude__: tuple[str, ...] = Field(default=(), init=False, exclude=True)

    def model_post_init(self, __context, /):
        """Wrap initial field values as dirty-aware containers after model initialization."""
        del __context
        for name, value in self.__dict__.items():
            if name.startswith("__") or name == "dirtyvars__":
                continue
            wrapped = self._wrap_if_needed(name, value)
            if wrapped is not value:
                object.__setattr__(self, name, wrapped)

    # Methods defined under ``if not TYPE_CHECKING`` to prevent static type
    # checkers from incorrectly determining the existence of actual attributes.
    if not TYPE_CHECKING:

        def __setattr__(self, name, value):
            """Set an attribute, wrap the value if needed, and mark it as dirty."""
            if name in ("dirtyvars__",):
                object.__setattr__(self, name, value)
                return

            wrapped = self._wrap_if_needed(name, value)
            super().__setattr__(name, wrapped)
            self._mark_dirty(name)

        def __getattribute__(self, name: str) -> Any:
            """Get an attribute, automatically wrapping nested containers as dirty-aware."""
            value = super().__getattribute__(name)
            if name.startswith("__") or name == "dirtyvars__" or name.endswith("__"):
                return value

            if hasattr(value, "_parent"):
                return value

            if isinstance(value, (list, dict, set)):
                wrapped = _wrap_container(value, self, name)
                object.__setattr__(self, name, wrapped)
                return wrapped
            # It is unlikely that anyone would nest several layers deep within
            # an ORM model, so a simple handling is sufficient here.
            elif isinstance(value, BaseModel):
                self._mark_dirty(name)

            return value

    def _wrap_if_needed(self, name: str, value: Any) -> Any:
        """Wrap a value as a dirty-aware container if it is a list, dict or set."""
        if isinstance(value, (list, dict, set)) and not hasattr(value, "_parent"):
            return _wrap_container(value, self, name)
        return value

    def _mark_dirty(self, name: str):
        """Mark a specific attribute as dirty."""
        if name.startswith("__") or name.endswith("__"):
            return
        exclude: tuple[str, ...] | None
        if exclude := getattr(self, "dirty_exclude__", None):
            if name in exclude:
                return
        dirty_vars: set[str] | None = getattr(self, "dirtyvars__", None)
        if dirty_vars is None:
            return
        dirty_vars.add(name)

    def is_dirty(self, name: str | None = None) -> bool:
        """Check whether a specific attribute (or any attribute) has been modified."""
        if name:
            return name in self.dirtyvars__
        return len(self.dirtyvars__) > 0

    def get_dirty_vars(self) -> set[str]:
        """Return the set of all dirty attribute names."""
        return set(self.dirtyvars__)

    def clean(self):
        """Reset the dirty state, clearing all tracked changes."""
        self.dirtyvars__.clear()
