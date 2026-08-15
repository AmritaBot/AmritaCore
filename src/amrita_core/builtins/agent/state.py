"""Step-level runtime state for the built-in ReAct agent.

This module defines the *semantic* state of the agent run — the part that
lives outside the Sense workflow.  The workflow itself stays linear
(``NATIVE_DO`` loop); all the "intelligence" (task decomposition DAG,
phase tracking, stall detection, token accounting) is carried here so the
workflow nodes only need to read/write this state via DI.
"""

from __future__ import annotations

import time
from graphlib import TopologicalSorter
from typing import TYPE_CHECKING

from pydantic import Field

from amrita_core.types.base import BaseModel

if TYPE_CHECKING:
    from amrita_core.usage import SessionUsageProxy


class DAGNode(BaseModel):
    """A sub-step of the task DAG (semantic layer only, not executed as a graph)."""

    id: str = ""
    description: str = ""
    depends_on: list[str] = Field(default_factory=list)


class DecomposeDecision(BaseModel):
    """LLM output for the analyze phase: whether to decompose and the DAG."""

    needs_decomposition: bool = False
    dag: list[DAGNode] = Field(default_factory=list)
    reason: str = ""


class StepSummary(BaseModel):
    """Short subject-predicate phrase summarizing a completed Step.

    Examples:
        - verb="Reviewed", object="codebase"
        - verb="Explored", object="the real definition of ..."
    """

    verb: str = "Completed"
    object: str = ""


class TokenBudget(BaseModel):
    """Token accounting based on real API usage values."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    budget: int | None = None
    """Per-run prompt-token budget (``None`` = unlimited).

    Injected from ``config.function_config.agent_step_token_budget`` by the
    strategy when the run state is created; ``exhausted`` compares the
    accumulated ``prompt_tokens`` against it.
    """

    @property
    def exhausted(self) -> bool:
        """Whether the accumulated prompt tokens reached the budget.

        ``False`` when no budget is configured (unlimited).  The workflow
        iteration conditions consult this to stop the loop before burning
        more tokens.
        """
        if self.budget is None:
            return False
        return self.prompt_tokens >= self.budget

    def update(self, usage: object | None) -> None:
        """Accumulate tokens from a ``UniResponseUsage``-like object."""
        if usage is None:
            return
        for attr in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = getattr(usage, attr, None)
            if value is None:
                continue
            setattr(self, attr, getattr(self, attr) + value)

    def refresh_window(
        self, usage: SessionUsageProxy | None, since_ts: float | None
    ) -> None:
        """Set this Step's prompt window from the ledger proxy (non-cumulative).

        The budget compares prompt tokens recorded since ``since_ts``, so a
        single ``record`` per Step boundary replaces the old per-call
        ``update`` accumulation.
        """
        if usage is None or since_ts is None:
            self.prompt_tokens = 0
            self.completion_tokens = 0
            self.total_tokens = 0
            return
        self.prompt_tokens = usage.prompt_since(since_ts)
        self.completion_tokens = 0
        self.total_tokens = 0

    def reset(self) -> None:
        """Reset the accumulated counts to zero, keeping the budget.

        Used after between-Step compression so the next Step starts from a
        fresh baseline without losing the configured per-run budget.
        """
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0


Phase = str
"""Reasoning phase name — a DAG node id (or ``"execute"`` in simple mode).

The phase is *not* a fixed four-stage enum anymore: the Step loop follows
the LLM-decomposed DAG, so each node's ``id`` becomes the phase of its Step.
"""


class AgentRunState(BaseModel):
    """Semantic run state of the built-in ReAct agent.

    Fields:

    - ``step_index``: global step counter (mirrors ``<think_step>``).
    - ``current_phase``: the active reasoning phase.
    - ``plan``: task DAG produced by the decompose decision (``None`` for
      simple tasks that run directly).
    - ``simple_mode``: True when the LLM decided NOT to decompose (bare run).
    - ``current_step_id``: id of the DAG node currently being executed.
    - ``completed_step_ids``: ids of finished DAG nodes (dependency check).
    - ``plan_revision``: number of times ``update_step`` revised the plan.
    - ``step_tool_signatures``: tool-call signatures collected within the
      current Step (stall detection).
    - ``stall_injected``: True once the "give up" prompt was injected in the
      current Step (injected only once, then the Step ends immediately).
    - ``last_summary``: subject-predicate summary of the previous Step.
    - ``tokens``: real API token accounting (compression trigger).
    - ``exec_finished``: True once the strategy finished calling tools,
      ending the execute-phase iteration loop.
    """

    step_index: int = 0
    current_phase: Phase | None = None
    plan: list[DAGNode] | None = None
    simple_mode: bool = False
    current_step_id: str | None = None
    completed_step_ids: list[str] = Field(default_factory=list)
    plan_revision: int = 0
    step_tool_signatures: list[str] = Field(default_factory=list)
    stall_injected: bool = False
    last_summary: StepSummary | None = None
    tokens: TokenBudget = TokenBudget()
    exec_finished: bool = False
    """True once the strategy finished tool calling (no more tools to call),
    which ends the execute-phase iteration loop."""
    step_started_ts: float | None = None
    """Wall-clock start of the current Step; the token-budget window anchor."""

    def begin_step(self, phase: Phase) -> None:
        """Enter a new Step: advance the counter and reset per-Step state.

        Every Step is a DAG node (or the implicit ``"execute"`` node in
        simple mode): it may span multiple tool-call iterations.
        """
        self.step_index += 1
        self.current_phase = phase
        # Fresh per-Step window for stall detection and give-up injection.
        self.step_tool_signatures = []
        self.stall_injected = False
        self.exec_finished = False
        self.step_started_ts = time.time()

    def begin_node(self, node: DAGNode) -> None:
        """Enter a DAG node as the current Step.

        Combines ``begin_step`` with the node id as phase and tracks the
        node as ``current_step_id``.
        """
        self.begin_step(node.id)
        self.current_step_id = node.id

    def record_tool_call(self, signature: str) -> None:
        """Record a tool-call signature within the current Step."""
        self.step_tool_signatures.append(signature)

    def is_stalled(self, threshold: int) -> bool:
        """True when the last ``threshold`` signatures are identical."""
        sigs = self.step_tool_signatures
        if len(sigs) < threshold:
            return False
        return len(set(sigs[-threshold:])) == 1

    def would_stall(self, signature: str, threshold: int) -> bool:
        """True when recording ``signature`` would trip the stall detector.

        Used to cancel a tool call *before* it executes: if the signature is
        already the last ``threshold - 1`` entries, adding it makes the last
        ``threshold`` identical — the call would be the first one of the
        stall window, so it is cancelled instead of executed.
        """
        if threshold <= 1:
            return False
        sigs = self.step_tool_signatures
        if len(sigs) < threshold - 1:
            return False
        window = sigs[-(threshold - 1) :]
        return all(s == signature for s in window) if window else False

    def next_ready_node(self) -> DAGNode | None:
        """Pick the next DAG node in topological order.

        Uses :class:`graphlib.TopologicalSorter` (stdlib) to resolve the
        linear execution order of the plan.  Diamond topologies (parallel
        branches) are flattened to a deterministic linear order; a cyclic
        plan degrades gracefully to the first node with satisfied
        dependencies.

        The returned node is *not* marked — call :meth:`complete_current_node`
        after its Step finishes.
        """
        if not self.plan:
            return None
        done = set(self.completed_step_ids)
        try:
            graph: dict[str, set[str]] = {
                node.id: set(node.depends_on) for node in self.plan
            }
            order = list(TopologicalSorter(graph).static_order())
        except Exception:
            # Cyclic plan: fall back to first node with satisfied deps.
            for node in self.plan:
                if node.id in done:
                    continue
                if all(dep in done for dep in node.depends_on):
                    return node
            return None
        by_id = {node.id: node for node in self.plan}
        for node_id in order:
            if node_id in done:
                continue
            node = by_id.get(node_id)
            if node is not None and all(dep in done for dep in node.depends_on):
                return node
        return None

    def complete_current_node(self) -> None:
        """Mark the current DAG node as completed."""
        if self.current_step_id and self.current_step_id not in self.completed_step_ids:
            self.completed_step_ids.append(self.current_step_id)
        self.current_step_id = None

    def all_plan_done(self) -> bool:
        """True when every DAG node has been completed."""
        if not self.plan:
            return True
        return all(n.id in self.completed_step_ids for n in self.plan)
