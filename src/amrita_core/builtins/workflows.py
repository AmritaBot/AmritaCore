from amrita_sense import WHILE
from amrita_sense.instructions.alias import ALIAS
from amrita_sense.instructions.native import (
    NATIVE_DO,
)
from amrita_sense.instructions.subprogram import ARCHIVED_SEGMENT
from amrita_sense.instructions.workfl_ctrl import NOP

from amrita_core.chatmanager.enums import BuiltinName
from amrita_core.components.llm import JINJA2_RENDER, LLM_COMPLETION
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

REACT_BLOCK = (
    STRATEGY_INIT
    >> AGENT_ENTRY
    >> WHILE(SINGLE_STRATEGY_CALL(fallback_on_fail=False)).ACTION(REACT_COUNTER)
    >> AGENT_POST_PROCESS
)


# Native step-loop block: task loop = NATIVE_DO(STEP_BODY).WHILE(task_cond),
# Step = intro/leave markers, iteration = single_execute in NATIVE_WHILE.
STEP_REACT_BLOCK = (
    STRATEGY_INIT
    >> AGENT_ENTRY
    >> NATIVE_DO(STEP_BODY).WHILE(task_cond)
    >> AGENT_POST_PROCESS
)

# ChatObject variant: _run_strategy jumps to AGENT_STRATEGY; the block is
# archived (JMP-skip) with a trailing NOP aliased STRATEGY_EOF as fall-through.
CHATOBJECT_STEP_REACT = ARCHIVED_SEGMENT(
    ALIAS(AGENT_ENTRY, BuiltinName.AGENT_STRATEGY)
    >> NATIVE_DO(STEP_BODY).WHILE(task_cond)
    >> AGENT_POST_PROCESS
) >> ALIAS(NOP, BuiltinName.STRATEGY_EOF)

SIMPLE_REACT = (
    LOAD_STATE
    >> JINJA2_RENDER
    >> BUILD_MESSAGE
    >> REACT_BLOCK
    >> LLM_COMPLETION
    >> COMMIT_MEMORY
)

SIMPLE_STEP_REACT = (
    LOAD_STATE
    >> JINJA2_RENDER
    >> BUILD_MESSAGE
    >> STEP_REACT_BLOCK
    >> LLM_COMPLETION
    >> COMMIT_MEMORY
)

REACT_ONLY = LOAD_STATE >> JINJA2_RENDER >> BUILD_MESSAGE >> REACT_BLOCK
STEP_REACT_ONLY = LOAD_STATE >> JINJA2_RENDER >> BUILD_MESSAGE >> STEP_REACT_BLOCK

SIMPLE_CHAT = (
    LOAD_STATE >> JINJA2_RENDER >> BUILD_MESSAGE >> LLM_COMPLETION >> COMMIT_MEMORY
)
