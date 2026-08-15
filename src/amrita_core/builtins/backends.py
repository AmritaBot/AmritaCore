from typing import ClassVar

from amrita_core.base.backend import AbilityBackend, MemoryBackend
from amrita_core.contexts import AbilityContext, StateContext
from amrita_core.preset import MultiPresetManager
from amrita_core.tools.manager import MultiToolsManager
from amrita_core.tools.mcp import MultiClientManager
from amrita_core.types.memory import MemoryModel


class LegacyBackend(AbilityBackend, MemoryBackend):
    glb: ClassVar[AbilityContext] = AbilityContext()

    def __init__(self, ctx: StateContext | None = None):
        # Backward-compatible seed: keep accepting a (deprecated) StateContext,
        # but the backend itself no longer stores state through it.
        self._memory: MemoryModel = ctx.memory if ctx else MemoryModel()

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
