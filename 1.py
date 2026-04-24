import types
import typing
from typing import get_args, get_origin

from amrita_core.tools.manager import _python_type_to_property_schema

x_type = str | int
origin = get_origin(x_type)
args = get_args(x_type)

print(f"x_type: {x_type}")
print(f"origin: {origin}")
print(f"args: {args}")
print(f"origin is typing.Union: {origin is typing.Union}")
print(f"origin is types.UnionType: {origin is types.UnionType}")

# Try to call the function directly
try:
    result = _python_type_to_property_schema(x_type, globals(), "test")
    print(f"ERROR: Function returned {result} instead of raising exception")
except Exception as e:
    print(f"SUCCESS: Function raised exception: {e}")
