from enum import Enum


class SuspendEnum(str, Enum):
    LOAD_STATE = "ChatObject::load_state"
    MEMORY = "ChatObject::memory_limiting"
    SINGLE_TOOL = "ChatObject::single_tool_call"
    PRECOMPLE = "matcher_call::pre_completion"
    COMPLE = "matcher_call::post_completion"
    ENTRY_POINT = "ChatObject::_entry"
    TRAIN_RENDER = "ChatObject::render_train_template"
    MESSAGES_PREPARED = "ChatObject::prepare_send_messages"
    STRATEGY_START = "ChatObject::run_strategy_start"
    LLM_CALL = "ChatObject::call_llm"
    ADVANCE_COUNTER = "ChatObject::advance_counter"
    COMMIT_MEMORY = "ChatObject::commit_memory"
    APPLY_CONTEXT = "Component::apply_context"
    # Builtin ReAct step-loop boundary markers (native instruction loop).
    STEP_INTRO = "ChatObject::step_intro"
    STEP_LEAVE = "ChatObject::step_leave"
