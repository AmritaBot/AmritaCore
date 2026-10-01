from threading import Lock
from typing import ClassVar

from amrita_core.base.backend import AbilityBackend, BillingBackend, MemoryBackend
from amrita_core.contexts import AbilityContext
from amrita_core.preset import MultiPresetManager
from amrita_core.tools.manager import MultiToolsManager
from amrita_core.tools.mcp import MultiClientManager
from amrita_core.types.billing import BillingRecord
from amrita_core.types.memory import MemoryModel


class LegacyBackend(AbilityBackend, MemoryBackend, BillingBackend):
    """Default in-process backend for ability, memory and billing."""

    glb: ClassVar[AbilityContext] = AbilityContext()

    def __init__(self):
        self._memory: MemoryModel = MemoryModel()
        self._billing: dict[str, list[BillingRecord]] = {}
        self._billing_lock = Lock()

    async def load_ability_all(self, session_id: str) -> AbilityContext:
        """Load ability context from global container"""

        return self.glb

    async def load_mcp_clients(self, session_id: str) -> MultiClientManager:
        return self.glb.mcp

    async def load_tools(self, session_id: str) -> MultiToolsManager:
        return self.glb.tools

    async def load_presets(self, session_id: str) -> MultiPresetManager:

        return self.glb.presets

    async def commit_memory(self, session_id: str, memory: MemoryModel) -> None:
        """Commit memory to global container"""
        self._memory = memory

    async def load_memory(self, session_id: str) -> MemoryModel:
        """Load memory from global container"""
        return self._memory

    async def commit_billing(
        self, session_id: str, records: list[BillingRecord]
    ) -> None:
        """Append billing records to the in-process store"""
        if not records:
            return
        with self._billing_lock:
            self._billing.setdefault(session_id, []).extend(records)

    async def load_billing(self, session_id: str) -> list[BillingRecord]:
        """Return a copy of the session's billing records"""
        with self._billing_lock:
            return list(self._billing.get(session_id, []))
