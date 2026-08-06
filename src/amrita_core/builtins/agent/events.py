"""Step lifecycle events for the built-in ReAct step loop.

Emitted at every Step boundary (``intro_step`` / ``leave_step``) and after
each tool round (``after_iteration``).  The events are *mutable*: registered
``@matcher`` handlers may modify event fields (e.g. override the summary) and
the lifecycle hook reads the modified values back.  Handlers may also raise
:class:`StepAbortError` — the hook passes it in ``exception_ignored`` so it
propagates through ``trigger_event`` and the hook can act on it (skip the
remaining work, inject prompts, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from amrita_sense.hook.event import ConstructableEvent

if TYPE_CHECKING:
    from amrita_core.builtins.agent.state import AgentRunState


class StepAbortError(BaseException):
    """Control-flow exception raised by a step-lifecycle matcher.

    Passed via ``exception_ignored`` to ``MatcherFactory.trigger_event`` so
    it propagates out of the event dispatch back to the lifecycle hook, which
    decides how to act on it (skip remaining work, end the Step early, ...).
    """


@dataclass
class StepIntroEvent(ConstructableEvent):
    """Broadcast when a Step begins (``intro_step``).

    Handlers may modify ``override_phase`` to redirect the phase name.
    """

    step_index: int
    phase: str | None
    simple_mode: bool = False
    plan_summary: str = ""
    # Mutable: handlers may set this to change the Step's phase name.
    override_phase: str | None = None

    @property
    def event_type(self) -> str:
        return "agent.step_intro"

    def get_event_type(self) -> str:
        return self.event_type

    @classmethod
    def constructor(cls, rs: "AgentRunState") -> "StepIntroEvent":
        """Construct from the step run state."""
        plan = rs.plan or []
        return cls(
            step_index=rs.step_index,
            phase=rs.current_phase,
            simple_mode=rs.simple_mode,
            plan_summary=", ".join(n.description for n in plan[:5]),
        )


@dataclass
class StepLeaveEvent(ConstructableEvent):
    """Broadcast when a Step finishes (``leave_step``).

    Handlers may modify ``override_verb`` / ``override_object`` to replace
    the subject-predicate summary produced by ``_summarize_step``.
    """

    step_index: int
    phase: str | None
    verb: str = ""
    object: str = ""
    stall_injected: bool = False
    # Mutable: handlers may set these to override the auto summary.
    override_verb: str | None = None
    override_object: str | None = None

    @property
    def event_type(self) -> str:
        return "agent.step_leave"

    def get_event_type(self) -> str:
        return self.event_type

    @classmethod
    def constructor(cls, rs: "AgentRunState") -> "StepLeaveEvent":
        """Construct from the step run state."""
        summary = rs.last_summary
        return cls(
            step_index=rs.step_index,
            phase=rs.current_phase,
            verb=summary.verb if summary else "",
            object=summary.object if summary else "",
            stall_injected=rs.stall_injected,
        )


@dataclass
class StepIterationEvent(ConstructableEvent):
    """Broadcast after each tool round inside the execute Step.

    Handlers may raise :class:`StepAbortError` to end the Step early (the
    hook sets ``exec_finished`` so ``iter_cond`` stops the iteration loop).
    """

    step_index: int
    phase: str | None
    tool_signatures: list[str]
    # Mutable: handlers may set this to force-end the Step.
    end_step: bool = False

    @property
    def event_type(self) -> str:
        return "agent.step_iteration"

    def get_event_type(self) -> str:
        return self.event_type

    @classmethod
    def constructor(cls, rs: "AgentRunState") -> "StepIterationEvent":
        """Construct from the step run state."""
        return cls(
            step_index=rs.step_index,
            phase=rs.current_phase,
            tool_signatures=list(rs.step_tool_signatures),
        )


@dataclass
class StepToolCallEvent(ConstructableEvent):
    """Broadcast *before* a regular tool executes.

    Handlers may modify ``arguments`` (rewrite the call) or raise
    :class:`StepAbortError` to cancel the call — the caller returns a
    ``"Cancelled: ..."`` result without executing the tool.
    """

    step_index: int
    phase: str | None
    tool_name: str
    tool_id: str
    arguments: str = "{}"
    # Mutable: handlers may set this to cancel the call without raising.
    cancel: bool = False

    @property
    def event_type(self) -> str:
        return "agent.tool_call"

    def get_event_type(self) -> str:
        return self.event_type

    @classmethod
    def constructor(
        cls,
        rs: "AgentRunState",
        tool_name: str,
        tool_id: str,
        arguments: str,
    ) -> "StepToolCallEvent":
        """Construct from the step run state and the tool call."""
        return cls(
            step_index=rs.step_index,
            phase=rs.current_phase,
            tool_name=tool_name,
            tool_id=tool_id,
            arguments=arguments,
        )


@dataclass
class StepToolReturnEvent(ConstructableEvent):
    """Broadcast *after* a regular tool returned.

    Handlers may modify ``result`` (rewrite what the model sees) or raise
    :class:`StepAbortError` to skip appending the result to the context.
    """

    step_index: int
    phase: str | None
    tool_name: str
    tool_id: str
    result: str = ""
    # Mutable: handlers may set this to skip writing the result back.
    skip_append: bool = False

    @property
    def event_type(self) -> str:
        return "agent.tool_return"

    def get_event_type(self) -> str:
        return self.event_type

    @classmethod
    def constructor(
        cls,
        rs: "AgentRunState",
        tool_name: str,
        tool_id: str,
        result: str,
    ) -> "StepToolReturnEvent":
        """Construct from the step run state and the tool result."""
        return cls(
            step_index=rs.step_index,
            phase=rs.current_phase,
            tool_name=tool_name,
            tool_id=tool_id,
            result=result,
        )


__all__ = [
    "StepAbortError",
    "StepIntroEvent",
    "StepIterationEvent",
    "StepLeaveEvent",
    "StepToolCallEvent",
    "StepToolReturnEvent",
]
