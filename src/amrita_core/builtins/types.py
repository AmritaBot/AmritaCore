"""TypedDict subclasses for builtin metadata payloads."""

from __future__ import annotations

from typing import Literal

from amrita_core.contents import MessageMetadataPayload


class AgentReasoningMetadata(MessageMetadataPayload):
    """Metadata for pre-resolve reasoning summary."""

    last_step: str
    summary: str


class AgentReasoningChunkMetadata(MessageMetadataPayload):
    """Metadata for streaming reasoning chunks."""

    content: str


class AgentToolCallMetadata(MessageMetadataPayload):
    """Metadata for tool call notifications."""

    function_name: str
    is_done: bool
    tool_id: str
    err: BaseException | None


class AgentLoopErrorMetadata(MessageMetadataPayload):
    """Metadata for loop reasoning detection errors."""

    chat_object_id: str
    error: str


class AgentMiddleMessageMetadata(MessageMetadataPayload):
    """Metadata for LLM middle messages."""

    content: str


class HookErrorMetadata(MessageMetadataPayload):
    """Metadata for hook-level error responses (e.g. cookie filter)."""

    content: str


#  React Reasoning Enhancement Metadata


class AgentStructuredReasoningChunkMetadata(MessageMetadataPayload):
    """Metadata for individual steps within structured chain-of-thought reasoning.

    Each step is classified into a reasoning phase:
    - ``analyze``: Understanding the user input and breaking down the problem
    - ``plan``: Formulating a strategy or action plan
    - ``execute``: Carrying out the planned actions or calling tools
    - ``verify``: Checking intermediate results for correctness
    """

    step_index: int
    """Zero-based index of the current reasoning step."""

    total_steps: int | None
    """Estimated total number of reasoning steps. May be None if unknown."""

    sub_problem: str | None
    """Brief description of the sub-problem being addressed in this step."""

    phase: Literal["analyze", "plan", "execute", "verify"] | None
    """Current reasoning phase for this step."""


class AgentReflectionMetadata(MessageMetadataPayload):
    """Metadata for post-reasoning self-reflection results.

    Emitted when ``ReactConfig.enable_reflection`` is True.
    The agent evaluates its own reasoning chain for contradictions,
    completeness, and alignment with the user's intent.
    """

    reflection_type: Literal["self_check", "contradiction_check", "completeness_check"]
    """Type of reflection being performed."""

    result: Literal["pass", "warning", "fail"]
    """Outcome of the reflection check.

    - ``pass``: Reasoning is sound; proceed to final answer.
    - ``warning``: Minor issue found; correction is optional.
    - ``fail``: Significant problem detected; a correction instruction
      will be injected into the context."""

    detail: str
    """Human-readable explanation of the reflection result."""


class AgentToolPredictionMetadata(MessageMetadataPayload):
    """Metadata for tool predictions made during structured reasoning.

    Emitted when ``ReactConfig.tool_prediction`` is True.
    Lists the tools the model expects to need for the upcoming steps.
    """

    predicted_tools: list[str]
    """Names of tools predicted to be needed."""

    predicted_next_action: str
    """Brief description of the next action the model expects to take."""


# Native step-loop Metadata — emitted by the step-loop strategy lifecycle
# (intro/leave, decomposition, stall recovery, compression) for front-ends.


class AgentStepIntroMetadata(MessageMetadataPayload):
    """Metadata for entering a Step (``intro_step``).

    Emitted once per phase boundary (analyze/plan/execute/verify) with the
    current global step index and mode so the front-end can render the step
    progression.
    """

    phase: str | None
    """The phase being entered — a DAG node id (or ``"execute"`` in simple
    mode)."""

    step_index: int
    """Global step counter (1-based, mirrors ``<think_step>``)."""

    simple_mode: bool
    """True when the LLM decided to run directly (no decomposition)."""

    current_step_id: str | None
    """Id of the DAG node being executed (``None`` in simple mode)."""

    description: str | None
    """Description of the DAG node being executed (``None`` in simple mode)."""


class AgentStepLeaveMetadata(MessageMetadataPayload):
    """Metadata for leaving a Step (``leave_step``).

    Emitted once per phase boundary; for the execute phase it carries the
    subject-predicate summary produced by ``_summarize_step``.
    """

    phase: str | None
    """The phase being left — a DAG node id (or ``"execute"`` in simple
    mode)."""

    step_index: int
    """Global step counter (1-based)."""

    stall_injected: bool
    """True when a "give up" prompt was injected in this Step."""

    summary_verb: str | None
    """Subject-predicate summary verb, e.g. ``"Reviewed"``."""

    summary_object: str | None
    """Subject-predicate summary object phrase."""


class AgentStepDecomposeMetadata(MessageMetadataPayload):
    """Metadata for the decomposition decision (analyze phase)."""

    needs_decomposition: bool
    """Whether the LLM decided the task needs multi-step execution."""

    simple_mode: bool
    """``not needs_decomposition`` — bare run without a DAG."""

    dag: list[str]
    """Ids of the DAG nodes (``[]`` in simple mode)."""

    descriptions: dict[str, str]
    """Node id → description map for the DAG (``{}`` in simple mode)."""

    reason: str
    """LLM-provided rationale for the decision."""


class AgentStepStallMetadata(MessageMetadataPayload):
    """Metadata for stall detection and the injected "give up" prompt."""

    signatures: list[str]
    """The repeated tool-call signatures that triggered the stall."""

    injected: bool
    """True once the give-up prompt was appended to the context."""


class AgentStepCompressMetadata(MessageMetadataPayload):
    """Metadata for between-Step history compression."""

    prompt_tokens: int
    """Real API prompt-token count that triggered the compression."""

    threshold: int | None
    """Configured ``memory_abstract_threshold`` (``None`` = never)."""
