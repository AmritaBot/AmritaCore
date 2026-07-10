from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from jinja2 import Template
from typing_extensions import deprecated

from amrita_core.agent.context import StrategyContext
from amrita_core.agent.strategy import (
    AgentStrategy,
    StrategyLikedObject,
)
from amrita_core.base.backend import BackendSlots
from amrita_core.config import AmritaConfig
from amrita_core.preset import MultiPresetManager, PresetManager
from amrita_core.tools.manager import MultiToolsManager, ToolsManager
from amrita_core.tools.mcp import ClientManager, MultiClientManager
from amrita_core.types import (
    MemoryModel,
    Message,
    SendMessageWrap,
)
from amrita_core.types.content import USER_INPUT
from amrita_core.types.preset import ModelPreset
from amrita_core.types.response import UniResponse, UniResponseUsage
from amrita_core.utils import get_current_datetime_timestamp


@dataclass
class AbilityContext:
    """Ability Context for ChatObject running, if field not set, will use default **global** managers"""

    tools: MultiToolsManager = field(default_factory=ToolsManager)
    presets: MultiPresetManager = field(default_factory=PresetManager)
    mcp: MultiClientManager = field(default_factory=ClientManager)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
@deprecated(
    "This context includes too much roles. Will be removed in 0.13.x",
    category=DeprecationWarning,
)
class StateContext:
    """State Context for ChatObject running, maybe you can also use it in other places(?)"""

    session_id: str = field(default_factory=lambda: uuid4().hex)
    memory: MemoryModel = field(default_factory=MemoryModel)
    ability: AbilityContext = field(default_factory=AbilityContext)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AbilityState:
    config: AmritaConfig
    slot: BackendSlots
    ability: AbilityContext | None = None  # Be set in runtime
    preset: ModelPreset | None = None


@dataclass
class MemoryContext:
    """Memory Context for running."""

    memory: MemoryModel | None = None  # Be set in runtime


@dataclass
class GeneralInput:
    user_input: USER_INPUT
    template: Template
    jinja2_vars: dict[str, Any]
    train: Message[str]


@dataclass
class WorkingState:
    context_wrap: SendMessageWrap | None = None  # Be set in runtime


@dataclass
class StrategyPayload:
    strategy: type[AgentStrategy] | StrategyLikedObject


@dataclass
class RespState:
    response: UniResponse | None = None
    extra_usage: UniResponseUsage[int] = field(
        default_factory=lambda: UniResponseUsage(
            prompt_tokens=0, completion_tokens=0, total_tokens=0
        )
    )


@dataclass
class SessionMetadata:
    stream_id: str = field(default_factory=lambda: uuid4().hex)
    session_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: str = field(default_factory=get_current_datetime_timestamp)
    time: datetime = field(default_factory=datetime.now)


@dataclass
class AgentLoopState:
    """Transient state for the framework-managed agent loop."""

    strategy: AgentStrategy | StrategyLikedObject | None = None
    stg_ctx: StrategyContext | None = None

    ctx_backup: SendMessageWrap | None = None

    called_count: int = 0


@dataclass
class DatabackendOptions:
    """Transient state for the framework-managed fetch strategy."""

    skip_memory_fetch: bool = False
    skip_tools_fetch: bool = False
    skip_mcp_fetch: bool = False
    skip_presets_fetch: bool = False
    skip_ability_extra_setting: bool = False
    skip_memory_commit: bool = False
