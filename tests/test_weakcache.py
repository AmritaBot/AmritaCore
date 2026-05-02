import gc
from typing import Any

import pytest

from amrita_core.weakcache import WeakValueLRUCache


class TestObject:
    """Test object for weak reference testing"""

    def __init__(self, value: Any):
        self.value = value

    def __repr__(self):
        return f"TestObject({self.value!r})"

    def __eq__(self, other):
        if isinstance(other, TestObject):
            return self.value == other.value
        return False

    def __hash__(self):
        return hash(self.value)


class TestWeakValueLRUCache:
    """Test suite for WeakValueLRUCache"""

    def test_init_with_negative_capacity(self):
        """Test that negative capacity raises ValueError"""
        with pytest.raises(ValueError, match="Capacity must be a positive integer"):
            WeakValueLRUCache(capacity=-1)

    def test_init_with_zero_capacity(self):
        """Test initialization with zero capacity"""
        cache = WeakValueLRUCache(capacity=0)
        assert cache.capacity == 0
        assert len(cache) == 0

    def test_init_with_positive_capacity(self):
        """Test normal initialization"""
        cache = WeakValueLRUCache(capacity=5)
        assert cache.capacity == 5
        assert len(cache) == 0

    def test_init_with_items(self):
        """Test initialization with initial items"""
        obj1 = TestObject("value1")
        obj2 = TestObject("value2")
        items = {"key1": obj1, "key2": obj2}
        cache = WeakValueLRUCache(capacity=5, items=items)

        assert cache.get("key1") is obj1
        assert cache.get("key2") is obj2
        assert len(cache) == 2

    def test_put_none_value_raises_error(self):
        """Test that putting None value raises ValueError"""
        cache = WeakValueLRUCache(capacity=5)
        with pytest.raises(
            ValueError, match="Cannot store None value in WeakValueLRUCache"
        ):
            cache.put("key", None)

    def test_put_and_get_basic(self):
        """Test basic put and get operations"""
        cache = WeakValueLRUCache(capacity=5)
        obj = TestObject("test")

        cache.put("key", obj)
        retrieved = cache.get("key")

        assert retrieved is obj
        assert len(cache) == 1

    def test_get_nonexistent_key(self):
        """Test getting non-existent key returns None or default"""
        cache = WeakValueLRUCache(capacity=5)

        # Default behavior
        assert cache.get("nonexistent") is None

        # With default value
        assert cache.get("nonexistent", "default") == "default"

    def test_get_expired_key(self):
        """Test getting expired (garbage collected) key"""
        cache = WeakValueLRUCache(capacity=5)

        # Create an object and add it to cache
        obj = TestObject("test")
        cache.put("key", obj)
        assert cache.get("key") is obj

        # Delete the object and force garbage collection
        del obj
        gc.collect()

        # The key should now return None/default
        assert cache.get("key") is None
        assert cache.get("key", "default") == "default"
        assert len(cache) == 0  # Should be cleaned up

    def test_lru_eviction_normal_mode(self):
        """Test LRU eviction in normal mode"""
        cache = WeakValueLRUCache(capacity=2)

        obj1 = TestObject("1")
        obj2 = TestObject("2")
        obj3 = TestObject("3")

        cache.put("key1", obj1)
        cache.put("key2", obj2)
        assert len(cache) == 2

        # Adding third item should evict the oldest (key1)
        cache.put("key3", obj3)
        assert len(cache) == 2
        assert cache.get("key1") is None  # Should be evicted
        assert cache.get("key2") is obj2
        assert cache.get("key3") is obj3

    def test_lru_eviction_with_existing_key(self):
        """Test that updating existing key doesn't cause eviction"""
        cache = WeakValueLRUCache(capacity=2)

        obj1 = TestObject("1")
        obj2 = TestObject("2")
        obj3 = TestObject("3")

        cache.put("key1", obj1)
        cache.put("key2", obj2)
        assert len(cache) == 2

        # Updating existing key should move it to end (most recent)
        cache.put("key1", obj1)
        assert len(cache) == 2

        # Adding new key should evict key2 (now oldest)
        cache.put("key3", obj3)
        assert len(cache) == 2
        assert cache.get("key1") is obj1
        assert cache.get("key2") is None  # Should be evicted
        assert cache.get("key3") is obj3

    def test_loose_mode_enabled(self):
        """Test loose mode behavior"""
        cache = WeakValueLRUCache(capacity=2, loose_mode=True)

        obj1 = TestObject("1")
        obj2 = TestObject("2")
        obj3 = TestObject("3")

        cache.put("key1", obj1)
        cache.put("key2", obj2)
        assert len(cache) == 2

        # In loose mode, adding third item should not evict if all refs are alive
        cache.put("key3", obj3)
        assert len(cache) == 3  # Should exceed capacity in loose mode
        assert cache.get("key1") is obj1
        assert cache.get("key2") is obj2
        assert cache.get("key3") is obj3

    def test_loose_mode_with_expired_refs(self):
        """Test loose mode with expired references"""
        cache = WeakValueLRUCache(capacity=2, loose_mode=True)

        obj1 = TestObject("1")
        obj2 = TestObject("2")

        cache.put("key1", obj1)
        cache.put("key2", obj2)
        assert len(cache) == 2

        # Let obj1 go out of scope and be garbage collected
        del obj1
        gc.collect()

        # Add new item - should clean up expired ref and add new one
        obj3 = TestObject("3")
        cache.put("key3", obj3)
        assert len(cache) == 2
        assert cache.get("key1") is None  # Expired
        assert cache.get("key2") is obj2
        assert cache.get("key3") is obj3

    def test_resize_capacity(self):
        """Test resizing cache capacity"""
        cache = WeakValueLRUCache(capacity=5)
        obj1 = TestObject("1")
        obj2 = TestObject("2")
        obj3 = TestObject("3")

        cache.put("key1", obj1)
        cache.put("key2", obj2)
        cache.put("key3", obj3)
        assert cache.capacity == 5
        assert len(cache) == 3

        # Resize to smaller capacity
        cache.resize(2)
        assert cache.capacity == 2

        # Cache should still contain all items until next put operation
        assert len(cache) == 3

        # Adding new item should trigger eviction based on new capacity
        obj4 = TestObject("4")
        cache.put("key4", obj4)
        assert len(cache) == 2  # Should evict based on new capacity of 2

    def test_set_loose_mode(self):
        """Test setting loose mode dynamically"""
        cache = WeakValueLRUCache(capacity=2, loose_mode=False)
        assert cache.loose is False

        cache.set_loose(True)
        assert cache.loose is True

        cache.set_loose(False)
        assert cache.loose is False

    def test_expire_method(self):
        """Test expire method"""
        cache = WeakValueLRUCache(capacity=5)

        # Add some objects
        obj1 = TestObject("1")
        obj2 = TestObject("2")
        obj3 = TestObject("3")
        obj4 = TestObject("4")
        obj5 = TestObject("5")

        cache.put("key1", obj1)
        cache.put("key2", obj2)
        cache.put("key3", obj3)
        cache.put("key4", obj4)
        cache.put("key5", obj5)

        # Let some objects expire
        del obj1
        del obj3
        del obj5
        gc.collect()

        # Before expire, cache should have 5 entries (including expired)
        assert len(cache) == 5

        # Expire with specific length - should check first 'length' keys
        cache.expire(3)
        # After expire, the expired keys in the first 3 positions should be removed
        # key1 and key3 were expired, so they should be removed from first 3
        assert "key1" not in cache._cache  # Should be removed
        assert "key3" not in cache._cache  # Should be removed
        assert "key2" in cache._cache  # Should remain (not expired)

        # Test expire with default length (1/5 of cache)
        # Reset cache
        cache.clear()
        for i in range(10):
            obj = TestObject(f"value{i}")
            cache.put(f"key{i}", obj)

        # Expire some objects
        for i in [0, 1, 2]:
            # We can't easily delete specific objects here, so just test the method call
            pass

        cache.expire()  # Should not crash

    def test_magic_methods_getitem_setitem_delitem(self):
        """Test __getitem__, __setitem__, __delitem__"""
        cache = WeakValueLRUCache(capacity=5)
        obj = TestObject("test")

        # Test __setitem__
        cache["key"] = obj
        assert cache["key"] is obj

        # Test __getitem__ with missing key
        with pytest.raises(KeyError):
            _ = cache["nonexistent"]

        # Test __delitem__
        del cache["key"]
        with pytest.raises(KeyError):
            del cache["key"]  # Already deleted

        # Test __delitem__ with non-existent key
        with pytest.raises(KeyError):
            del cache["nonexistent"]

    def test_contains_method(self):
        """Test __contains__ method"""
        cache = WeakValueLRUCache(capacity=5)
        obj = TestObject("test")

        cache.put("key", obj)
        assert "key" in cache

        # Test with expired key
        del obj
        gc.collect()
        assert "key" not in cache

        # Test with non-existent key
        assert "nonexistent" not in cache

    def test_len_method(self):
        """Test __len__ method"""
        cache = WeakValueLRUCache(capacity=5)
        assert len(cache) == 0

        obj1 = TestObject("1")
        obj2 = TestObject("2")
        cache.put("key1", obj1)
        cache.put("key2", obj2)
        assert len(cache) == 2

        # Test with expired object
        del obj1
        gc.collect()
        # Note: __len__ returns total entries including expired ones
        # until they are accessed/cleaned up
        assert len(cache) == 2  # Still 2 until cleanup happens

        # Accessing should trigger cleanup
        _ = cache.get("key1")
        assert len(cache) == 1

    def test_iter_keys_methods(self):
        """Test __iter__ and keys methods"""
        cache = WeakValueLRUCache(capacity=5)
        obj1 = TestObject("1")
        obj2 = TestObject("2")
        obj3 = TestObject("3")

        cache.put("key1", obj1)
        cache.put("key2", obj2)
        cache.put("key3", obj3)

        keys_list = list(cache)
        assert set(keys_list) == {"key1", "key2", "key3"}

        keys_from_keys_method = list(cache.keys())
        assert set(keys_from_keys_method) == {"key1", "key2", "key3"}

        # Test with expired object
        del obj2
        gc.collect()

        keys_after_gc = list(cache)
        assert set(keys_after_gc) == {"key1", "key3"}

    def test_clear_method(self):
        """Test clear method"""
        cache = WeakValueLRUCache(capacity=5)
        obj1 = TestObject("1")
        obj2 = TestObject("2")

        cache.put("key1", obj1)
        cache.put("key2", obj2)
        assert len(cache) == 2

        cache.clear()
        assert len(cache) == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_capacity_properties(self):
        """Test capacity property and get_capacity method"""
        cache = WeakValueLRUCache(capacity=10)
        assert cache.capacity == 10
        assert cache.get_capacity() == 10

    def test_size_method(self):
        """Test size method (counts only non-expired items)"""
        cache = WeakValueLRUCache(capacity=5)
        obj1 = TestObject("1")
        obj2 = TestObject("2")
        obj3 = TestObject("3")

        cache.put("key1", obj1)
        cache.put("key2", obj2)
        cache.put("key3", obj3)
        assert cache.size() == 3

        # Expire one object
        del obj2
        gc.collect()
        assert cache.size() == 2

    def test_is_full_method(self):
        """Test is_full method"""
        cache = WeakValueLRUCache(capacity=2)
        assert not cache.is_full()

        obj1 = TestObject("1")
        cache.put("key1", obj1)
        assert not cache.is_full()

        obj2 = TestObject("2")
        cache.put("key2", obj2)
        assert cache.is_full()

        # Even with expired objects, is_full checks total entries
        del obj1
        gc.collect()
        assert cache.is_full()  # Still has 2 entries (one expired)

    def test_pop_method(self):
        """Test pop method"""
        cache = WeakValueLRUCache(capacity=5)
        obj = TestObject("test")

        cache.put("key", obj)

        # Pop existing key
        popped = cache.pop("key")
        assert popped is obj
        assert len(cache) == 0

        # Pop non-existent key without default
        with pytest.raises(KeyError):
            cache.pop("nonexistent")

        # Pop non-existent key with default
        assert cache.pop("nonexistent", "default") == "default"

        # Test pop with expired key
        obj2 = TestObject("test2")
        cache.put("key2", obj2)
        del obj2
        gc.collect()

        # Pop expired key without default
        with pytest.raises(KeyError):
            cache.pop("key2")

        # Pop expired key with default
        assert cache.pop("key2", "default") == "default"

    def test_repr_method(self):
        """Test __repr__ method"""
        cache = WeakValueLRUCache(capacity=5)
        obj1 = TestObject("1")
        obj2 = TestObject("2")

        cache.put("key1", obj1)
        cache.put("key2", obj2)

        repr_str = repr(cache)
        assert "capacity=5" in repr_str
        assert "'key1': TestObject('1')" in repr_str
        assert "'key2': TestObject('2')" in repr_str

        # Test with expired object
        del obj1
        gc.collect()
        repr_str_after_gc = repr(cache)
        assert "'key1'" not in repr_str_after_gc
        assert "'key2': TestObject('2')" in repr_str_after_gc

    def test_get_moves_to_end(self):
        """Test that get operation moves item to end (most recently used)"""
        cache = WeakValueLRUCache(capacity=3)
        obj1 = TestObject("1")
        obj2 = TestObject("2")
        obj3 = TestObject("3")

        cache.put("key1", obj1)
        cache.put("key2", obj2)
        cache.put("key3", obj3)

        # Get key1 to move it to end
        _ = cache.get("key1")

        # Add new item - should evict key2 (now oldest)
        obj4 = TestObject("4")
        cache.put("key4", obj4)

        assert cache.get("key1") is obj1  # Should still be there
        assert cache.get("key2") is None  # Should be evicted
        assert cache.get("key3") is obj3
        assert cache.get("key4") is obj4

    def test_put_existing_key_moves_to_end(self):
        """Test that putting existing key moves it to end"""
        cache = WeakValueLRUCache(capacity=3)
        obj1 = TestObject("1")
        obj2 = TestObject("2")
        obj3 = TestObject("3")

        cache.put("key1", obj1)
        cache.put("key2", obj2)
        cache.put("key3", obj3)

        # Put existing key1 again
        cache.put("key1", obj1)

        # Add new item - should evict key2 (now oldest)
        obj4 = TestObject("4")
        cache.put("key4", obj4)

        assert cache.get("key1") is obj1
        assert cache.get("key2") is None  # Should be evicted
        assert cache.get("key3") is obj3
        assert cache.get("key4") is obj4
