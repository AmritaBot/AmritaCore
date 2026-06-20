from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from amrita_core.preset import MultiPresetManager, PresetManager
from amrita_core.tools.manager import MultiToolsManager, ToolsManager
from amrita_core.tools.mcp import ClientManager, MultiClientManager
from amrita_core.types import MemoryModel


@dataclass
class AbilityContext:
    """Ability Context for ChatObject running, if field not set, will use default **global** managers"""

    tools: MultiToolsManager = field(default_factory=ToolsManager)
    presets: MultiPresetManager = field(default_factory=PresetManager)
    mcp: MultiClientManager = field(default_factory=ClientManager)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class StateContext:
    """State Context for ChatObject running, maybe you can also use it in other places(?)"""

    session_id: str = field(default_factory=lambda: uuid4().hex)
    memory: MemoryModel = field(default_factory=MemoryModel)
    ability: AbilityContext = field(default_factory=AbilityContext)
    extra: dict[str, Any] = field(default_factory=dict)
