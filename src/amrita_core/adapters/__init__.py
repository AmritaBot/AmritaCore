"""The base definitions for adapters and related components."""

import importlib
import pkgutil

from amrita_core.base.adapter import (
    ADAPTER_TYPE,
    COMPLETION_RETURNING,
    AdapterManager,
    MessageContent,
    ModelAdapter,
)

__all__ = [
    "ADAPTER_TYPE",
    "COMPLETION_RETURNING",
    "AdapterManager",
    "MessageContent",
    "ModelAdapter",
]

from amrita_core._env import _MODULE_LOADED, TEST_MODE

if (TEST_MODE.value and "adapters" not in _MODULE_LOADED) or not TEST_MODE.value:
    _MODULE_LOADED["adapters"] = True
    for loader, module_name, is_pkg in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{module_name}")
        globals()[module_name] = module
        __all__.append(module_name)  # type: ignore # noqa: PYI056
