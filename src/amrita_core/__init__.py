from amrita_sense.logging import debug_log, logger
from amrita_sense.streaming import SuspendObjectStream

from amrita_core.base.adapter import AdapterManager
from amrita_core.base.tokenizer import TokenizerManager

from . import adapters, tokenizers
from .agent.functions import AgentRuntime, create_agent
from .agent.strategy import AgentStrategy
from .base.backend import AbilityBackend, BackendSlots, MemoryBackend
from .builtins.backends import LegacyBackend
from .chatmanager import ChatManager, ChatObject, ChatObjectMeta, SuspendEnum
from .config import AmritaConfig, get_config, set_config
from .contexts import AbilityContext, StateContext
from .hook.event import CompletionEvent, EventTypeEnum, PreCompletionEvent
from .hook.on import on_completion, on_event, on_precompletion
from .libchat import (
    call_completion,
    get_last_response,
    get_tokens,
    text_generator,
    tools_caller,
)
from .preset import PresetManager, PresetReport
from .tools import mcp
from .tools.manager import ToolsManager, on_tools, simple_tool
from .tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
    ToolContext,
    ToolData,
    ToolFunctionSchema,
)
from .types import (
    BaseModel,
    Function,
    MemoryModel,
    ModelConfig,
    ModelPreset,
    TextContent,
    ToolCall,
    ToolResult,
    UniResponse,
    UniResponseUsage,
)
from .utils import load_and_notice, side_effect_import


async def load_amrita():
    logger.info("Loading AmritaCore built-in components......")
    config = get_config()
    if config.function_config.agent_mcp_client_enable:
        logger.info("Loading MCP clients......")
        clients = list(config.function_config.agent_mcp_server_scripts)
        await mcp.ClientManager().initialize_scripts_all(clients)


async def minimal_init(config: AmritaConfig = AmritaConfig()) -> None:
    set_config(config)
    await load_amrita()


logger.info("Loading tokenizers and adapters......")

load_and_notice(adapters, "Adapters")
logger.debug(f"Loaded adapters: {','.join(AdapterManager().get_adapters().keys())}")
load_and_notice(tokenizers, "Tokenizers")
logger.debug(
    f"Loaded tokenizers: {','.join(TokenizerManager().get_tokenizers().keys())}"
)

__all__ = [
    "AbilityBackend",
    "AbilityContext",
    "AgentRuntime",
    "AgentStrategy",
    "BackendSlots",
    "BaseModel",
    "ChatManager",
    "ChatObject",
    "ChatObjectMeta",
    "CompletionEvent",
    "EventTypeEnum",
    "Function",
    "FunctionDefinitionSchema",
    "FunctionParametersSchema",
    "FunctionPropertySchema",
    "LegacyBackend",
    "MemoryBackend",
    "MemoryModel",
    "ModelConfig",
    "ModelPreset",
    "PreCompletionEvent",
    "PresetManager",
    "PresetReport",
    "StateContext",
    "SuspendEnum",
    "SuspendObjectStream",
    "TextContent",
    "ToolCall",
    "ToolContext",
    "ToolData",
    "ToolFunctionSchema",
    "ToolResult",
    "ToolsManager",
    "UniResponse",
    "UniResponseUsage",
    "adapters",
    "call_completion",
    "create_agent",
    "debug_log",
    "get_config",
    "get_last_response",
    "get_tokens",
    "load_amrita",
    "mcp",
    "minimal_init",
    "on_completion",
    "on_event",
    "on_precompletion",
    "on_tools",
    "set_config",
    "side_effect_import",
    "simple_tool",
    "text_generator",
    "tokenizers",
    "tools_caller",
]
