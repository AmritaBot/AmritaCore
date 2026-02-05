from .chatmanager import ChatManager, ChatObject, ChatObjectMeta
from .config import get_config, set_config
from .hook.event import CompletionEvent, PreCompletionEvent
from .hook.matcher import MatcherManager
from .hook.on import on_completion, on_event, on_precompletion
from .libchat import (
    call_completion,
    get_last_response,
    get_tokens,
    text_generator,
    tools_caller,
)
from .logging import debug_log, logger
from .preset import PresetManager, PresetReport
from .tools import mcp
from .tools.manager import ToolsManager, on_tools
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

__all__ = [
    "BaseModel",
    "ChatManager",
    "ChatObject",
    "ChatObjectMeta",
    "CompletionEvent",
    "Function",
    "FunctionDefinitionSchema",
    "FunctionParametersSchema",
    "FunctionPropertySchema",
    "MatcherManager",
    "MemoryModel",
    "ModelConfig",
    "ModelPreset",
    "PreCompletionEvent",
    "PresetManager",
    "PresetReport",
    "TextContent",
    "ToolCall",
    "ToolContext",
    "ToolData",
    "ToolFunctionSchema",
    "ToolResult",
    "ToolsManager",
    "UniResponse",
    "UniResponseUsage",
    "call_completion",
    "debug_log",
    "get_config",
    "get_last_response",
    "get_tokens",
    "logger",
    "mcp",
    "on_completion",
    "on_event",
    "on_precompletion",
    "on_tools",
    "set_config",
    "text_generator",
    "tools_caller",
]
__inited: bool = False


def init():
    global __all__, __inited
    if not __inited:
        logger.info("AmritaCore is initalizing......")
        import jieba

        from . import builtins

        __all__ += [builtins.__name__]

        jieba.initialize()


async def load_amrita():
    logger.info("Loading AmritaCore......")
    config = get_config()
    if config.function_config.agent_mcp_client_enable:
        logger.info("Loading MCP clients......")
        clients = list(config.function_config.agent_mcp_server_scripts)
        await mcp.ClientManager().initialize_scripts_all(clients)
