from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from amrita_core.types.billing import BillingRecord

if TYPE_CHECKING:
    from amrita_core.contexts import AbilityContext
    from amrita_core.preset import MultiPresetManager
    from amrita_core.tools.manager import MultiToolsManager
    from amrita_core.tools.mcp import MultiClientManager
    from amrita_core.types import MemoryModel


class AbilityBackend(ABC):
    @abstractmethod
    async def load_ability_all(self, session_id: str) -> AbilityContext:
        """Load ability"""
        ...

    @abstractmethod
    async def load_mcp_clients(self, session_id: str) -> MultiClientManager: ...

    @abstractmethod
    async def load_tools(self, session_id: str) -> MultiToolsManager: ...

    @abstractmethod
    async def load_presets(self, session_id: str) -> MultiPresetManager: ...


class MemoryBackend(ABC):
    @abstractmethod
    async def load_memory(self, session_id: str) -> MemoryModel:
        """Load memory"""
        ...

    @abstractmethod
    async def commit_memory(self, session_id: str, memory: MemoryModel) -> None:
        """Commit memory"""
        ...


class BillingBackend(ABC):
    """Optional sink for per-request billing records.

    Records already travel inside ``MemoryModel.billing``, so the default
    persistence path needs no billing backend at all. Implement this only to
    forward the same records to an external cost store (database, metrics
    pipeline, quota enforcer).
    """

    @abstractmethod
    async def commit_billing(
        self, session_id: str, records: list[BillingRecord]
    ) -> None:
        """Append the records produced by one run."""
        ...

    @abstractmethod
    async def load_billing(self, session_id: str) -> list[BillingRecord]:
        """Return the records previously committed for a session."""
        ...


class NullBillingBackend(BillingBackend):
    """No-op billing sink; records stay in memory only."""

    async def commit_billing(
        self, session_id: str, records: list[BillingRecord]
    ) -> None:
        return

    async def load_billing(self, session_id: str) -> list[BillingRecord]:
        return []


def _default_billing_backend() -> BillingBackend:
    """Build the out-of-the-box in-memory billing sink."""
    from amrita_core.builtins.backends import LegacyBackend

    return LegacyBackend()


@dataclass
class BackendSlots:
    ability: AbilityBackend
    memory: MemoryBackend
    billing: BillingBackend = field(default_factory=_default_billing_backend)

    @classmethod
    def default(cls) -> BackendSlots:
        """Build slots backed by a single shared in-memory backend."""
        from amrita_core.builtins.backends import LegacyBackend

        backend = LegacyBackend()
        return cls(ability=backend, memory=backend, billing=backend)
