"""Step-loop control nodes for the built-in ReAct agent.

The decisions the Step loop takes *between* tool rounds live here as Sense
nodes and predicates, so the workflow can express them with ``NATIVE_IF``
instead of an ``if`` chain buried in ``ReActAgentStrategy.intro_step``:

* ``NEEDS_DECOMPOSITION`` / ``HAS_READY_NODE`` / ``USES_SIMPLE_STEP`` /
  ``PLAN_EXHAUSTED`` — mutually exclusive predicates over ``AgentRunState``.
* ``STEP_DECOMPOSE`` / ``STEP_BEGIN_NODE`` / ``STEP_BEGIN_SIMPLE`` /
  ``STEP_BEGIN_BOUNDARY`` / ``STEP_PLAN_STATUS`` / ``STEP_SUMMARY`` — one
  action each, idempotent where a Step boundary may be re-entered.
* ``apply_plan_update`` — table dispatch for the ``update_step`` built-in.

The strategy keeps thin wrappers (``intro_step`` / ``leave_step`` /
``_decide_decomposition`` / ``_inject_plan_status`` / ``_summarize_step`` /
``_handle_update_step``) that call the same functions. A direct caller and the
workflow therefore share one implementation; the workflow is the path that
turns the predicates into graph branches.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from amrita_sense import Node
from amrita_sense.logging import logger

from amrita_core.builtins.agent.state import (
    DAGNode,
    DecomposeDecision,
    StepSummary,
)
from amrita_core.builtins.types import AgentStepDecomposeMetadata
from amrita_core.contexts import AgentLoopState
from amrita_core.libchat import call_completion, get_last_response
from amrita_core.types import Message

if TYPE_CHECKING:
    from amrita_core.builtins.agent.react_base import BaseReActAgentStrategy
    from amrita_core.builtins.agent.state import AgentRunState

DECOMPOSE_SYSTEM_PROMPT = (
    "# Task Decomposition Decision\n"
    "Decide whether this task needs multi-step execution.\n"
    "\n"
    "## Use SIMPLE mode (needs_decomposition=false) when:\n"
    "SIMPLE mode is still ReAct — the normal tool loop runs;\n"
    "it just is not step-driven (no DAG decomposition).\n"
    "Most requests, including routine questions and simple\n"
    "tasks, belong here.\n"
    "- Chitchat, greetings, or casual conversation\n"
    "- A direct question answerable from the conversation context\n"
    "- A single tool call suffices (lookup, calculation, format conversion)\n"
    "- Summarizing or rephrasing content already available\n"
    "- The user asks for a direct answer without further work\n"
    "\n"
    "## Use STEP mode (needs_decomposition=true, DAG) ONLY when:\n"
    "- Multiple dependent steps are required\n"
    "- Information must be gathered first, then used to produce the result\n"
    "- Research or multi-source synthesis\n"
    "\n"
    "## Rules\n"
    "- NEVER create a single-node DAG; if one step covers the task, use simple mode.\n"
    '- DAG node ids are short semantic names ("search-web", "read-docs", "write-summary"), never step-1/step-2.\n'
    'Output strictly as JSON: {"needs_decomposition": bool, "dag": [...], "reason": "..."}\n'
    "\n"
    "## Examples\n"
    "Example 1 (simple):\n"
    "User: What is 2+2?\n"
    'Output: {"needs_decomposition": false, "dag": [], "reason": "Simple arithmetic; answer directly."}\n'
    "\n"
    "Example 2 (complex):\n"
    "User: Summarize the repo docs: first list all doc files, then read each one, then write a summary.\n"
    'Output: {"needs_decomposition": true, '
    '"dag": [{"id": "list-files", "description": "List all doc files", "depends_on": []}, '
    '{"id": "read-docs", "description": "Read each doc file", "depends_on": ["list-files"]}, '
    '{"id": "write-summary", "description": "Write the summary", "depends_on": ["read-docs"]}], '
    '"reason": "Reading depends on listing; writing depends on reading."}'
)

DECOMPOSE_USER_PROMPT = (
    "Now decide whether the above task needs decomposition. "
    "Output ONLY the JSON object, nothing else: "
    '{"needs_decomposition": bool, "dag": [...], "reason": "..."}'
)

SUMMARY_SYSTEM_PROMPT = (
    "# Step Summary\n"
    "Summarize what was accomplished in this step using a short "
    "subject-predicate phrase: a verb (past tense) + an object phrase. "
    'Output strictly as JSON: {"verb": "...", "object": "..."}\n'
    "\n"
    "## Examples\n"
    "Example 1 (research step):\n"
    "Step: the assistant searched the web for the latest version, "
    "then read the changelog page, then answered with the version number.\n"
    'Output: {"verb": "Retrieved", "object": "latest version number"}\n'
    "\n"
    "Example 2 (computation step):\n"
    "Step: the assistant called the calculator tool with 2+2 and got 4.\n"
    'Output: {"verb": "Calculated", "object": "2+2 result"}'
)

SUMMARY_USER_PROMPT = (
    "Now summarize the step above. "
    'Output ONLY the JSON object, nothing else: {"verb": "...", "object": "..."}'
)


def strategy_of(loop: AgentLoopState) -> "BaseReActAgentStrategy":
    """Resolve the step-loop strategy, rejecting strategies without the hooks.

    Imported lazily: ``react_base`` imports the workflow components, so a
    module-level import here would close the cycle.
    """
    from amrita_core.builtins.agent.react_base import BaseReActAgentStrategy

    strategy = loop.strategy
    if not isinstance(strategy, BaseReActAgentStrategy):
        raise RuntimeError(
            "The step loop requires a BaseReActAgentStrategy subclass, "
            f"got {type(strategy).__name__}"
        )
    return strategy


def _state(loop: AgentLoopState) -> "AgentRunState":
    strategy = strategy_of(loop)
    return strategy._init_run_state()


# Predicates — the graph branches on these instead of the strategy deciding.


def needs_decomposition(rs: "AgentRunState | None") -> bool:
    """The first Step has not decided yet whether the task gets a DAG."""
    return bool(
        rs is not None
        and rs.step_index == 0
        and not rs.decomposition_done
        and rs.plan is None
        and not rs.simple_mode
    )


def has_ready_node(rs: "AgentRunState | None") -> bool:
    """Plan mode with a DAG node whose dependencies are all satisfied."""
    if rs is None or rs.simple_mode or not rs.plan:
        return False
    return rs.next_ready_node() is not None


def uses_simple_step(rs: "AgentRunState | None") -> bool:
    """Bare run (or a plan that was dropped): one implicit ``execute`` Step."""
    return bool(rs is not None and (rs.simple_mode or not rs.plan))


def plan_exhausted(rs: "AgentRunState | None") -> bool:
    """Plan mode with no runnable node left (all done or unready deps)."""
    if rs is None or rs.simple_mode or not rs.plan:
        return False
    return rs.next_ready_node() is None


def should_inject_plan_status(rs: "AgentRunState | None") -> bool:
    """A plan exists, so the current snapshot is worth showing to the model."""
    return bool(rs is not None and not rs.simple_mode and rs.plan)


@Node()
def NEEDS_DECOMPOSITION(loop: AgentLoopState) -> bool:
    """Graph predicate: the first Step still owes a decompose decision."""
    return needs_decomposition(loop.run_state)


@Node()
def HAS_READY_NODE(loop: AgentLoopState) -> bool:
    """Graph predicate: plan mode with a runnable DAG node."""
    return has_ready_node(loop.run_state)


@Node()
def USES_SIMPLE_STEP(loop: AgentLoopState) -> bool:
    """Graph predicate: bare run, one implicit ``execute`` Step."""
    return uses_simple_step(loop.run_state)


@Node()
def PLAN_EXHAUSTED(loop: AgentLoopState) -> bool:
    """Graph predicate: plan mode with nothing left to run."""
    return plan_exhausted(loop.run_state)


@Node()
def SHOULD_INJECT_PLAN_STATUS(loop: AgentLoopState) -> bool:
    """Graph predicate: a plan snapshot is worth injecting."""
    return should_inject_plan_status(loop.run_state)


# Actions — one node per outcome the predicates select.


@Node()
async def STEP_PREPARE(loop: AgentLoopState) -> None:
    """Step boundary preamble: expose ``update_step`` and drain peer messages.

    Runs before decomposition and Step selection so an incoming peer message
    is part of the context the decompose call and the plan snapshot see.
    ``intro_step`` repeats both calls; the tool exposure is idempotent and the
    drain is empty the second time.
    """
    st = strategy_of(loop)
    st._ensure_step_tools()
    await st._drain_peer_input()


@Node()
async def STEP_DECOMPOSE(loop: AgentLoopState) -> None:
    """First Step only: ask the model whether to decompose, then store the DAG."""
    await decide_decomposition(strategy_of(loop))


@Node()
def STEP_BEGIN_NODE(loop: AgentLoopState) -> None:
    """Enter the next ready DAG node as the current Step."""
    rs = _state(loop)
    node = rs.next_ready_node()
    assert node is not None, "STEP_BEGIN_NODE ran without a ready node"
    rs.begin_node(node)


@Node()
def STEP_BEGIN_SIMPLE(loop: AgentLoopState) -> None:
    """Enter the single implicit ``execute`` Step of a bare run."""
    rs = _state(loop)
    if rs.open_step_index == rs.step_index:
        # Re-entry guard: intro_step or a graph branch already opened this Step.
        return
    rs.begin_step("execute")


@Node()
def STEP_BEGIN_BOUNDARY(loop: AgentLoopState) -> None:
    """Plan finished or blocked mid-run: open a boundary Step."""
    rs = _state(loop)
    if rs.open_step_index == rs.step_index:
        return
    rs.begin_step("verify")


@Node()
def STEP_PLAN_STATUS(loop: AgentLoopState) -> None:
    """Inject the current plan snapshot (idempotent: only when it changed)."""
    inject_plan_status(strategy_of(loop))


@Node()
async def STEP_SUMMARY(loop: AgentLoopState) -> None:
    """Ask for the subject-predicate summary of the Step that just ended."""
    await summarize_step(strategy_of(loop))


@Node()
def STEP_SUMMARY_FALLBACK(loop: AgentLoopState) -> None:
    """Degrade the summary when the model call failed or returned garbage."""
    apply_summary_fallback(strategy_of(loop))


# Function bodies shared by the nodes and the strategy wrappers.


def _snapshot_lines(rs: "AgentRunState") -> list[str]:
    done = set(rs.completed_step_ids)
    lines = []
    for node in rs.plan or []:
        state = "done" if node.id in done else "pending"
        if node.id == rs.current_step_id:
            state = "current"
        deps = f" (after: {', '.join(node.depends_on)})" if node.depends_on else ""
        lines.append(f"- {node.id} [{state}]{deps}: {node.description}")
    return lines


def plan_status_snapshot(rs: "AgentRunState") -> str | None:
    """Render the plan snapshot, or ``None`` when there is nothing to show."""
    if rs.simple_mode or not rs.plan:
        return None
    return "[Plan status]\n" + "\n".join(_snapshot_lines(rs))


def plan_status_note(rs: "AgentRunState") -> str:
    """The guidance appended to a fresh plan snapshot."""
    done = set(rs.completed_step_ids)
    remaining = [
        n.id for n in (rs.plan or []) if n.id not in done and n.id != rs.current_step_id
    ]
    current = next((n for n in (rs.plan or []) if n.id == rs.current_step_id), None)
    return (
        (
            f"\n[Current step] {current.id}: {current.description}\n"
            if current is not None
            else "\n[Current step] (none)\n"
        )
        + "Work on this step ONLY. Do not produce the final answer for the whole "
        "task yet — the remaining steps cover the rest, and answering now makes "
        "them look redundant.\n"
        "You are executing this plan. NEVER call agent_stop while any step is still "
        "`pending` or `current`"
        + (f" (still pending: {', '.join(remaining)})" if remaining else "")
        + ": it ends the entire task and discards every remaining step. A finished "
        "step needs no signal — just stop calling tools and the framework advances "
        "to the next step on its own. If a step turns out to be wrong, redundant, or "
        "impossible (its tool keeps failing with persistent ERROR results), fix the "
        "plan with update_step (remove_step / add_step / replan) and carry on; never "
        "use agent_stop to escape the plan. When a tool fails, retry at most once. "
        "Do NOT use mark_done — the framework marks steps done for you."
    )


def inject_plan_status(stg: "BaseReActAgentStrategy") -> None:
    """Append the plan snapshot when it changed since the last injection."""
    rs = stg._init_run_state()
    snapshot = plan_status_snapshot(rs)
    if snapshot is None or snapshot == stg._last_plan_snapshot:
        return
    stg._last_plan_snapshot = snapshot
    stg.ctx.message.append(
        Message(role="user", content=snapshot + plan_status_note(rs))
    )
    logger.debug(
        f"Plan status injected into context ({len(snapshot.splitlines()) - 1} nodes)."
    )


async def decide_decomposition(stg: "BaseReActAgentStrategy") -> None:
    """One LLM call: simple mode or a DAG, with a degradation path."""
    rs = stg._init_run_state()
    prompt: list = [
        Message(role="system", content=DECOMPOSE_SYSTEM_PROMPT),
        *stg.ctx.message.unwrap(exclude_system=True),
        Message(role="user", content=DECOMPOSE_USER_PROMPT),
    ]
    try:
        resp = await get_last_response(
            call_completion(
                prompt, preset=stg.preset, config=stg.config, usage=stg.usage
            )
        )
        if not (resp.content or "").strip():
            req_id = getattr(resp.metadata, "original_request_id", None)
            logger.warning(
                f"Empty decomposition response (request_id={req_id}, "
                f"thinking_content={bool(resp.reasoning_content)}); "
                "fallback: Sorry, no response was returned"
            )
            raise ValueError("empty decomposition response")
        decision = DecomposeDecision.model_validate_json(resp.content)
    except Exception as e:
        logger.warning(f"Decomposition decision failed, running directly: {e!s}")
        decision = DecomposeDecision(needs_decomposition=False)

    rs.simple_mode = not decision.needs_decomposition
    rs.plan = decision.dag if decision.needs_decomposition else None
    rs.decomposition_done = True
    logger.debug(
        f"Decompose decision: simple_mode={rs.simple_mode}, "
        f"plan={[n.id for n in (rs.plan or [])]}"
    )
    dag_ids = [n.id for n in (rs.plan or [])]
    dag_desc = {n.id: n.description for n in (rs.plan or [])}
    dag_desc_str = (
        ", ".join(f"{n.id} ({n.description})" for n in (rs.plan or []))
        if rs.plan
        else ""
    )
    await stg._emit_step_event(
        content=(
            "[step] decompose: "
            + ("simple mode (no DAG)" if rs.simple_mode else f"DAG [{dag_desc_str}]")
            + f" — {decision.reason}"
        ),
        metadata=AgentStepDecomposeMetadata(
            type="step",
            extra_type="decompose",
            needs_decomposition=decision.needs_decomposition,
            simple_mode=rs.simple_mode,
            dag=dag_ids,
            descriptions=dag_desc,
            reason=decision.reason,
        ),
    )


async def summarize_step(stg: "BaseReActAgentStrategy") -> None:
    """One LLM call for the subject-predicate summary; raises on failure."""
    rs = stg._init_run_state()
    prompt: list = [
        Message(role="system", content=SUMMARY_SYSTEM_PROMPT),
        *stg.ctx.message.unwrap(exclude_system=True),
        Message(role="user", content=SUMMARY_USER_PROMPT),
    ]
    resp = await get_last_response(
        call_completion(prompt, preset=stg.preset, config=stg.config, usage=stg.usage)
    )
    if not (resp.content or "").strip():
        req_id = getattr(resp.metadata, "original_request_id", None)
        logger.warning(
            f"Empty summary response (request_id={req_id}, "
            f"thinking_content={bool(resp.reasoning_content)}); "
            "fallback: Sorry, no response was returned"
        )
        raise ValueError("empty summary response")
    rs.last_summary = StepSummary.model_validate_json(resp.content)


def apply_summary_fallback(stg: "BaseReActAgentStrategy") -> None:
    """Keep the Step auditable when the summary call produced nothing usable."""
    rs = stg._init_run_state()
    rs.last_summary = StepSummary(verb="Completed", object=rs.current_phase or "")


async def maybe_decompose(stg: "BaseReActAgentStrategy") -> None:
    """Decompose if the run state still needs it (no-op on the graph path)."""
    if needs_decomposition(stg._init_run_state()):
        await decide_decomposition(stg)


def begin_step_for_current_state(stg: "BaseReActAgentStrategy") -> str:
    """Open the Step the current run state calls for, returning its kind.

    Returns ``"node"``, ``"simple"`` or ``"boundary"`` so a direct caller can
    log which branch a graph-driven run would have taken.
    """
    rs = stg._init_run_state()
    if rs.open_step_index == rs.step_index:
        # A graph STEP_BEGIN_* node already opened this Step; consume the mark.
        rs.open_step_index = -1
        return "already"
    if rs.simple_mode or not rs.plan:
        rs.begin_step("execute")
        rs.open_step_index = -1
        return "simple"
    node = rs.next_ready_node()
    if node is None:
        rs.begin_step("verify")
        rs.open_step_index = -1
        return "boundary"
    rs.begin_node(node)
    rs.open_step_index = -1
    return "node"


# update_step — table dispatch, one handler per action.


def _apply_replan(rs: "AgentRunState", args: dict[str, Any]) -> None:
    dag = args.get("dag")
    if not dag:
        return
    rs.plan = [DAGNode.model_validate(n) for n in dag]
    rs.completed_step_ids = []
    rs.current_step_id = None


def _apply_mark_done(rs: "AgentRunState", args: dict[str, Any]) -> None:
    rs.complete_current_node()


def _apply_add_step(rs: "AgentRunState", args: dict[str, Any]) -> None:
    node = args.get("node")
    if not node:
        return
    if rs.plan is None:
        rs.plan = []
    rs.plan.append(DAGNode.model_validate(node))


def _apply_remove_step(rs: "AgentRunState", args: dict[str, Any]) -> None:
    nid = args.get("node_id")
    if not nid:
        return
    if rs.plan:
        rs.plan = [n for n in rs.plan if n.id != nid]
    if nid in rs.completed_step_ids:
        rs.completed_step_ids.remove(nid)


PLAN_UPDATE_ACTIONS: dict[str, Callable[["AgentRunState", dict[str, Any]], None]] = {
    "replan": _apply_replan,
    "mark_done": _apply_mark_done,
    "add_step": _apply_add_step,
    "remove_step": _apply_remove_step,
}


def apply_plan_update(stg: "BaseReActAgentStrategy", args: dict[str, Any]) -> None:
    """Apply one ``update_step`` action through the handler table.

    Revisions that change nothing (unknown action, missing payload) still bump
    ``plan_revision``: the counter reports attempts, which is what the model
    is told when it asks whether its edit landed.
    """
    rs = stg._init_run_state()
    action = args.get("action")
    handler = PLAN_UPDATE_ACTIONS.get(action) if isinstance(action, str) else None
    if handler is not None:
        handler(rs, args)
    rs.plan_revision += 1
    logger.info(
        f"update_step({action}) applied, plan_revision={rs.plan_revision}, "
        f"plan={[n.id for n in (rs.plan or [])]}, done={rs.completed_step_ids}"
    )


__all__ = [
    "DECOMPOSE_SYSTEM_PROMPT",
    "HAS_READY_NODE",
    "NEEDS_DECOMPOSITION",
    "PLAN_EXHAUSTED",
    "PLAN_UPDATE_ACTIONS",
    "SHOULD_INJECT_PLAN_STATUS",
    "STEP_BEGIN_BOUNDARY",
    "STEP_BEGIN_NODE",
    "STEP_BEGIN_SIMPLE",
    "STEP_DECOMPOSE",
    "STEP_PLAN_STATUS",
    "STEP_PREPARE",
    "STEP_SUMMARY",
    "STEP_SUMMARY_FALLBACK",
    "USES_SIMPLE_STEP",
    "apply_plan_update",
    "apply_summary_fallback",
    "begin_step_for_current_state",
    "decide_decomposition",
    "has_ready_node",
    "inject_plan_status",
    "maybe_decompose",
    "needs_decomposition",
    "plan_exhausted",
    "plan_status_note",
    "plan_status_snapshot",
    "should_inject_plan_status",
    "strategy_of",
    "summarize_step",
    "uses_simple_step",
]
