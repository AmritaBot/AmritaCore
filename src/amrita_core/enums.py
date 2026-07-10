from enum import Enum


class SuspendEnum(str, Enum):
    LOAD_STATE = "ChatObject::load_state"
    MEMORY = "ChatObject::memory_limiting"
    MEMORY_APPEND = "Component::memory_append"
    SINGLE_TOOL = "ChatObject::single_tool_call"
    PRECOMPLE = "matcher_call::pre_completion"
    COMPLE = "matcher_call::post_completion"
    ENTRY_POINT = "ChatObject::_entry"
    TRAIN_RENDER = "ChatObject::render_train_template"
    MESSAGES_PREPARED = "ChatObject::prepare_send_messages"
    STRATEGY_START = "ChatObject::run_strategy_start"
    LLM_CALL = "ChatObject::call_llm"
    FINALIZE = "ChatObject::finalize"
    ADVANCE_COUNTER = "ChatObject::advance_counter"
    CALL_SINGLE_STRATEGY = "ChatObject::call_single_strategy"
    COMMIT_MEMORY = "ChatObject::commit_memory"
    APPLY_CONTEXT = "Component::apply_context"


class BuiltinName(str, Enum):
    AGENT_STRATEGY = "ChatObject::__agent_main__"
    STRATEGY_EOF = "ChatObject::__strategy_eof__"
