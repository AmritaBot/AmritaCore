from __future__ import annotations

import weakref
from collections import OrderedDict
from collections.abc import Generator, Hashable, Iterator
from typing import Any, Generic, TypeVar, overload

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")
T = TypeVar("T")


class WeakValueLRUCache(Generic[K, V]):
    """Weak reference LRU cache implementation.

    Always used for locks pool.
    """

    __marker = object()
    _capacity: int
    _cache: OrderedDict[K, weakref.ReferenceType[V]]
    _loose_mode: bool

    def __init__(
        self,
        *,
        capacity: int,
        loose_mode: bool = False,
        items: dict[K, V] | None = None,
    ):
        """Constructor of WeakValueLRUCache

        Args:
            capacity (int): Size of cache.
            loose_mode (bool, optional): When the length of items is out of capacity, still allowed to add item to cache. Defaults to False.
            items (dict[K, V] | None, optional): Initial items. Defaults to None.

        Raises:
            ValueError: Raised when capacity is not positive.
        """
        if capacity < 0:
            raise ValueError("Capacity must be a positive integer")
        self._capacity = capacity
        self._loose_mode = loose_mode
        self._cache: OrderedDict[K, weakref.ref[V]] = OrderedDict()
        if items:
            for key, value in items.items():
                self.put(key, value)

    def _cleanup_key_if_expired(self, key: K) -> bool:
        """Clean a key if it's expired.

        Args:
            key (K): Key in this cache.

        Returns:
            bool: True if this key hasn't expired. Otherwise, return False.
        """
        if key not in self._cache:
            return False

        weak_ref = self._cache[key]
        if weak_ref() is None:
            self._cache.pop(key, None)
            return False
        return True

    def resize(self, new_size: int):
        """Resize the cache.

        Args:
            new_size (int): New cache size.
        """
        self._capacity = new_size

    def set_loose(self, loose: bool):
        """Set loose mode.

        Args:
            loose (bool): Loose mode.
        """
        self._loose_mode = loose

    @property
    def loose(self) -> bool:
        """Get loose mode.

        Returns:
            bool: Loose mode.
        """
        return self._loose_mode

    @overload
    def get(self, key: K) -> V | None: ...
    @overload
    def get(self, key: K, default: T) -> V | T: ...
    def get(self, key: K, default: T = None) -> V | T:
        """Get a value from cache.

        Args:
            key (K): Key in this cache.

        Returns:
            V | None: Value in this cache.
        """

        if key not in self._cache:
            return default

        weak_ref = self._cache[key]
        value: V | None = weak_ref()

        if value is None:
            self._cache.pop(key, None)
            return default

        self._cache.pop(key)
        self._cache[key] = weak_ref
        return value

    def put(self, key: K, value: V) -> None:
        """Put a value into cache.

        Args:
            key (K): Key in this cache.
            value (V): Value in this cache.
        """
        if value is None:
            raise ValueError("Cannot store None value in WeakValueLRUCache")

        weak_ref: weakref.ReferenceType[V] = weakref.ref(value)

        if key in self._cache:
            self._cache.pop(key)
        else:
            should_expire_count = max(0, (len(self._cache) + 1) - self._capacity)
            collected = 0
            for _ in range(len(self._cache)):
                if collected >= should_expire_count:
                    break
                oldest_key: K = next(iter(self._cache))
                oldest_ref = self._cache[oldest_key]
                if oldest_ref() is None or not self._loose_mode:
                    collected += 1
                    self._cache.pop(oldest_key)
                elif self._loose_mode:
                    self._cache.move_to_end(oldest_key)

        self._cache[key] = weak_ref

    def expire(self, length: int | None = None) -> None:
        """Expire cache of given length

        Args:
            length (int | None, optional): Length. Defaults to None.
        """
        if length is None:
            length = int(len(self._cache) * (1 / 5))
        keys_to_check = list(self._cache.keys())[: min(length, len(self._cache))]
        expired_keys = [key for key in keys_to_check if self._cache[key]() is None]

        for key in expired_keys:
            self._cache.pop(key, None)

    def __getitem__(self, key: K) -> V:
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: K, value: V) -> None:
        self.put(key, value)

    def __delitem__(self, key: K) -> None:

        if key not in self._cache:
            raise KeyError(key)
        del self._cache[key]

    def __contains__(self, key: K) -> bool:
        if key not in self._cache:
            return False
        return self._cache[key]() is not None

    def __len__(self) -> int:
        """!!!This will return the number of non-expired items in the cache.!!!"""
        return len(self._cache)

    def __iter__(self) -> Iterator[K]:
        for key in list(self._cache.keys()):
            if self._cleanup_key_if_expired(key):
                yield key

    def keys(self) -> Iterator[K]:
        """Return a iterator that yield keys.

        Yields:
            Iterator[Hashable]: Iterator
        """
        return self.__iter__()

    def values(self) -> Generator[V, Any, None]:
        for _, value in self.items():  # noqa: PERF102
            yield value

    def items(self) -> Generator[tuple[K, V], Any, None]:

        for key, weak_ref in list(self._cache.items()):
            if self._cleanup_key_if_expired(key):
                value = weak_ref()
                assert value is not None
                yield key, value

    def clear(self) -> None:
        """Remove all items from cache."""
        self._cache.clear()

    @property
    def capacity(self) -> int:
        """Get cache capacity."""
        return self._capacity

    def get_capacity(self) -> int:
        """Get cache capacity."""
        return self._capacity

    def size(self) -> int:
        """Return the valid size of cache."""
        t = 0
        for i in self._cache.values():
            if i() is not None:
                t += 1
        return t

    def is_full(self) -> bool:
        """Check if cache is full."""
        return len(self._cache) >= self._capacity

    @overload
    def pop(self, key: K) -> V: ...
    @overload
    def pop(self, key: K, default: T) -> V | T: ...

    def pop(self, key: K, default: T = __marker) -> V | T:
        """Remove and return item associated with key if key is in cache, else default.

        Args:
            key (K): Key in this cache.
            default (T, optional): Default value. Defaults to __marker.

        Returns:
            V | T: Value in this cache.
        """
        if key not in self._cache:
            if default is self.__marker:
                raise KeyError(key)
            return default

        weak_ref = self._cache.pop(key)
        value = weak_ref()
        if value is None:
            if default is self.__marker:
                raise KeyError(key)
            return default
        return value

    def __repr__(self) -> str:

        items = []
        for k, weak_ref in self._cache.items():
            v = weak_ref()
            if v is not None:
                items.append(f"{k!r}: {v!r}")
        return f"{self.__class__.__name__}(capacity={self._capacity}, items={{{', '.join(items)}}})"
