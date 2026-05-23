from enum import Enum


class SuspendEnum(str, Enum):
    MEMORY = "ChatObject::memory_limiting"
    SINGLE_TOOL = "ChatObject::single_tool_call"
    PRECOMPLE = "matcher_call::pre_completion"
    COMPLE = "matcher_call::post_completion"
    ENTRY_POINT = "ChatObject::_entry"
    TRAIN_RENDER = "ChatObject::render_train_template"
    MESSAGES_PREPARED = "ChatObject::prepare_send_messages"
    STRATEGY_START = "ChatObject::run_strategy_start"
    LLM_CALL = "ChatObject::call_llm"
    FINALIZE = "ChatObject::finalize"


class BuiltinName(str, Enum):
    AGENT_STRATEGY = "ChatObject::__agent_main__"
