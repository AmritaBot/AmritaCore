from amrita_sense import WHILE
from amrita_sense.instructions.native import (
    NATIVE_DO,
    NATIVE_IF,
)

from amrita_core.components.compaction import MANAGE_CONTEXT, should_manage_context
from amrita_core.components.llm import JINJA2_RENDER, LLM_COMPLETION
from amrita_core.components.normalize import NORMALIZE_MESSAGES
from amrita_core.components.process import BUILD_MESSAGE, COMMIT_MEMORY, LOAD_STATE
from amrita_core.components.react import (
    AGENT_ENTRY,
    AGENT_POST_PROCESS,
    REACT_COUNTER,
    SINGLE_STRATEGY_CALL,
    STEP_BODY,
    STRATEGY_INIT,
    task_cond,
)

#: Manage history before rendering so a new summary reaches the system instruction of the request it was computed for.
MANAGE_HISTORY = NATIVE_IF(should_manage_context, MANAGE_CONTEXT)

REACT_BLOCK = (
    STRATEGY_INIT
    >> AGENT_ENTRY
    >> WHILE(SINGLE_STRATEGY_CALL(fallback_on_fail=False)).ACTION(REACT_COUNTER)
    >> AGENT_POST_PROCESS
)


# Native step-loop block: task loop = NATIVE_DO(STEP_BODY).WHILE(task_cond), Step = intro/leave markers, iteration = single_execute in NATIVE_WHILE.
STEP_REACT_BLOCK = (
    STRATEGY_INIT
    >> AGENT_ENTRY
    >> NATIVE_DO(STEP_BODY).WHILE(task_cond)
    >> AGENT_POST_PROCESS
)

SIMPLE_REACT = (
    LOAD_STATE
    >> NORMALIZE_MESSAGES
    >> MANAGE_HISTORY
    >> JINJA2_RENDER
    >> BUILD_MESSAGE
    >> REACT_BLOCK
    >> LLM_COMPLETION
    >> COMMIT_MEMORY
)

SIMPLE_STEP_REACT = (
    LOAD_STATE
    >> NORMALIZE_MESSAGES
    >> MANAGE_HISTORY
    >> JINJA2_RENDER
    >> BUILD_MESSAGE
    >> STEP_REACT_BLOCK
    >> LLM_COMPLETION
    >> COMMIT_MEMORY
)

REACT_ONLY = (
    LOAD_STATE
    >> NORMALIZE_MESSAGES
    >> MANAGE_HISTORY
    >> JINJA2_RENDER
    >> BUILD_MESSAGE
    >> REACT_BLOCK
)
STEP_REACT_ONLY = (
    LOAD_STATE
    >> NORMALIZE_MESSAGES
    >> MANAGE_HISTORY
    >> JINJA2_RENDER
    >> BUILD_MESSAGE
    >> STEP_REACT_BLOCK
)

SIMPLE_CHAT = (
    LOAD_STATE
    >> NORMALIZE_MESSAGES
    >> MANAGE_HISTORY
    >> JINJA2_RENDER
    >> BUILD_MESSAGE
    >> LLM_COMPLETION
    >> COMMIT_MEMORY
)
