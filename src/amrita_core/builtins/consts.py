from amrita_core.builtins.tools import PROCESS_MESSAGE, REASONING_TOOL, STOP_TOOL

BUILTIN_TOOLS_NAME = {
    STOP_TOOL.function.name,
    REASONING_TOOL.function.name,
    PROCESS_MESSAGE.function.name,
}

AGENT_PROCESS_TOOLS = (
    REASONING_TOOL,
    STOP_TOOL,
    PROCESS_MESSAGE,
)
