import importlib
import pkgutil

from amrita_core._env import _MODULE_LOADED, TEST_MODE
from amrita_core.base.tokenizer import BaseTokenizer, TokenizerManager

__all__ = ["BaseTokenizer", "TokenizerManager"]

if (TEST_MODE.value and "tokenizers" not in _MODULE_LOADED) or not TEST_MODE.value:
    _MODULE_LOADED["tokenizers"] = True

    for loader, module_name, is_pkg in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{module_name}")
        globals()[module_name] = module
        __all__.append(module_name)  # type: ignore # noqa: PYI056
