from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from amrita_core.contexts import AbilityContext
    from amrita_core.preset import MultiPresetManager
    from amrita_core.tools.manager import MultiToolsManager
    from amrita_core.tools.mcp import MultiClientManager
    from amrita_core.types import MemoryModel


class AbilityBackend:
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


class MemoryBackend:
    @abstractmethod
    async def load_memory(self, session_id: str) -> MemoryModel:
        """Load memory"""
        ...

    @abstractmethod
    async def commit_memory(self, session_id: str, memory: MemoryModel) -> None:
        """Commit memory"""
        ...


@dataclass
class BackendSlots:
    ability: AbilityBackend
    memory: MemoryBackend
