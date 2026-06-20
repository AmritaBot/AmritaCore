from typing import ClassVar

from amrita_core.base.backend import AbilityBackend, MemoryBackend
from amrita_core.contexts import AbilityContext, StateContext
from amrita_core.preset import MultiPresetManager
from amrita_core.tools.manager import MultiToolsManager
from amrita_core.tools.mcp import MultiClientManager
from amrita_core.types.memory import MemoryModel


class LegacyBackend(AbilityBackend, MemoryBackend):
    ctx: StateContext
    glb: ClassVar[AbilityContext] = AbilityContext()

    def __init__(self, ctx: StateContext | None = None):
        if ctx:
            self.ctx = ctx

    def _init_ctx(self, session_id: str):
        if not hasattr(self, "ctx"):
            self.ctx = StateContext(session_id, ability=self.glb)

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
        self._init_ctx(session_id)
        self.ctx.memory = memory

    async def load_memory(self, session_id: str) -> MemoryModel:
        """Load memory from global container"""
        self._init_ctx(session_id)
        return self.ctx.memory
