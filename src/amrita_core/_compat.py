"""Centralised adapters for ``amrita_sense`` implementation details.

A few spots in AmritaCore need to reach into ``amrita_sense`` internals that
are deliberately kept outside its public API (and therefore outside its
SemVer compatibility guarantees).  Funnelling every such access through this
module keeps the coupling in one place: if upstream reshuffles these details,
only this file needs to be revisited instead of hunting the call sites down
across the codebase.
"""

from __future__ import annotations

__all__ = ["exc_ignored_disabled"]


def exc_ignored_disabled() -> bool:
    """Return whether amrita_sense's ``DISABLE_EXC_IGNORED`` switch is on.

    The flag lives in ``amrita_sense._unsafe`` and is documented upstream as
    an internal switch that may change without notice.  The import is guarded
    so that a future relocation degrades to the documented default (flag off)
    rather than breaking AmritaCore at import time.
    """
    try:
        from amrita_sense._unsafe import __flags__
    except ImportError:  # pragma: no cover - defensive fallback
        return False
    return bool(__flags__.DISABLE_EXC_IGNORED)
