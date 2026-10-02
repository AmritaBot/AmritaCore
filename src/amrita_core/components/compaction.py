"""History management — the policy object and its workflow nodes.

``ContextCompactor`` owns everything about what happens when history
outgrows the model's attention window: where the trigger sits relative to
that window, and how the oversized history is brought back inside it.
``LLMConfig.context_strategy`` picks the action — ``compact`` folds the
oldest prefix into a summary, ``slide`` drops the oldest messages outright.
Both the between-turn node and the between-Step handling inside the agent
loop drive that same object, so one model is described by one threshold.

Under ``compact`` the summary is stored on ``MemoryModel.abstract`` and
rendered back into the system instruction by the train template, so nothing
is injected into the message list and provider message-ordering rules stay
untouched. Under ``slide`` nothing is rendered: the surviving tail is sent
verbatim.

```mermaid
flowchart LR
    A[MemoryModel.messages] -->|over threshold?| B{context_strategy}
    B -->|compact| C[split at newest user message]
    C --> D[summarize prefix, merged with memory.abstract]
    D --> E[memory.abstract]
    B -->|slide| F[drop oldest by weighted estimate]
    F --> G[memory.messages]
    E --> H[train template renders SUMMARY]
```
"""

from dataclasses import dataclass
from typing import Literal

from amrita_sense import Node
from amrita_sense.logging import logger

from amrita_core.config import AmritaConfig
from amrita_core.consts import ABSTRACT_INSTRUCTION
from amrita_core.contexts import AbilityState, MemoryContext, RespState
from amrita_core.enums import SuspendEnum
from amrita_core.libchat import call_completion, get_last_response, text_generator
from amrita_core.types.memory import MemoryModel
from amrita_core.types.message import CONTENT_LIST_TYPE, Message
from amrita_core.types.preset import (
    ModelPreset,
    resolve_max_context,
    resolve_max_output,
)
from amrita_core.types.tool import ToolResult
from amrita_core.usage import SessionUsageProxy


def split_history(
    messages: CONTENT_LIST_TYPE,
) -> tuple[CONTENT_LIST_TYPE, CONTENT_LIST_TYPE]:
    """Split history into the compactable prefix and the retained tail.

    The cut lands on the newest ``user`` message, so the tail always starts a
    clean turn and no assistant tool call is ever separated from its tool
    results. Returns ``([], messages)`` when there is nothing to fold.
    """
    cut = 0
    for idx, msg in enumerate(messages):
        if msg.role == "user":
            cut = idx
    return list(messages[:cut]), list(messages[cut:])


@dataclass
class CompactionResult:
    """Outcome of a successful fold."""

    messages: CONTENT_LIST_TYPE
    """History that survives the fold, starting at a clean turn boundary."""

    summary: str
    """The summary that replaces the folded prefix."""


@dataclass
class ContextCompactor:
    """History-management policy and operation for one model.

    Constructed per use site from the live config, preset and run ledger, so
    the trigger always reflects the model actually being called.

    ```mermaid
    flowchart TD
        C[ContextCompactor] --> B[budget: preset window or global fallback]
        C --> T[threshold: budget x compaction_trigger_ratio]
        C --> S[needs_management: measured prompt vs threshold]
        C --> F[compact: summarize prefix, keep tail]
        C --> D[slide: drop oldest by weighted estimate]
    ```
    """

    config: AmritaConfig
    preset: ModelPreset | None = None
    usage: SessionUsageProxy | None = None
    instruction: str = ABSTRACT_INSTRUCTION
    """System prompt handed to the summarizer."""

    @property
    def strategy(self) -> Literal["compact", "slide", "none"]:
        """Which history-management policy this run uses."""
        return self.config.llm.context_strategy

    @property
    def enabled(self) -> bool:
        """Whether any history management runs at all.

        ``none`` disables both policies, so history grows unbounded and the
        provider is left to reject the request. Overflow recovery is skipped
        too: rewriting history is exactly what the user asked not to happen.
        """
        return self.strategy != "none"

    @property
    def budget(self) -> int:
        """Input-token budget: the preset's window, else the global default."""
        if self.preset is None:
            return self.config.llm.session_tokens_windows
        return resolve_max_context(self.preset, self.config)

    @property
    def threshold(self) -> int:
        """Prompt size at which history management is forced.

        Derived from the attention window so the trigger follows the model
        instead of a hand-maintained global number.
        """
        return int(self.budget * self.config.llm.compaction_trigger_ratio)

    @property
    def slide_target(self) -> int:
        """Prompt size ``slide`` trims down to.

        Below ``threshold`` so the trimmed history does not land back on the
        trigger and re-slide on the very next request.
        """
        return int(self.budget * self.config.llm.slide_target_ratio)

    @property
    def message_limit(self) -> int:
        """Message count at which management is forced regardless of tokens.

        The token trigger needs the provider to report usage; this fallback
        covers gateways that report none, and very large windows.
        """
        return self.config.llm.memory_length_limit

    @property
    def summary_preset(self) -> ModelPreset | None:
        """Preset for the summarizer call, with its own output ceiling.

        A reasoning model spends its output budget on thinking before it emits
        any content, so a summary call that inherits a small ``max_output``
        comes back with an empty answer and the fold silently does nothing.
        ``LLMConfig.compaction_max_tokens`` raises the ceiling for this call
        only; ``0`` keeps the preset's own value.
        """
        budget = self.config.llm.compaction_max_tokens
        if self.preset is None or budget <= 0:
            return self.preset
        if resolve_max_output(self.preset, self.config) >= budget:
            return self.preset
        return self.preset.model_copy(update={"max_output": budget})

    def needs_management(self, memory: MemoryModel | None) -> bool:
        """Whether ``memory`` outgrew the budget and has a droppable head.

        Fires on whichever trigger comes first: the prompt size the provider
        reported for the previous request (no local tokenizer needed), or the
        message-count fallback. Shared by both policies — they differ in what
        they do, not in when they start.

        Returns ``False`` when history management is disabled, or when the
        action the active policy would take has nothing to work on: folding
        needs a prefix before the newest turn, sliding needs more than one
        message. Reporting ``True`` in those cases would run the node, reset
        the measurement and change nothing.
        """
        if not self.enabled or memory is None:
            return False
        messages = memory.messages
        if self.strategy == "compact":
            prefix, _ = split_history(messages)
            if not prefix:
                return False
        elif len(messages) <= 1:
            return False
        if self.message_limit > 0 and len(messages) >= self.message_limit:
            return True
        if memory.usage is None:
            return False
        return memory.usage.prompt_tokens >= self.threshold

    def should_compact(self, memory: MemoryModel | None) -> bool:
        """Whether ``memory`` should be folded into a summary.

        True only under the ``compact`` policy: under ``slide`` the caller
        must drop messages instead, and rewriting a verbatim history into a
        summary would be the wrong operation entirely.
        """
        return self.strategy == "compact" and self.needs_management(memory)

    async def summarize(
        self,
        prefix: CONTENT_LIST_TYPE,
        previous: str = "",
    ) -> str:
        """Summarize ``prefix``, merging it into ``previous`` when given.

        Returns the stripped summary, or an empty string when the model
        produced nothing usable. Callers decide what an empty result means.
        """
        body = "".join(f"{it}\n" for it in text_generator(prefix, split_role=True))
        if previous:
            body = f"<EXISTING_SUMMARY>\n{previous}\n</EXISTING_SUMMARY>\n\n{body}"
        prompt: CONTENT_LIST_TYPE = [
            Message[str](role="system", content=self.instruction),
            Message[str](
                role="user",
                content=(
                    "Make a summary of full informations in message list:"
                    "\n\n```text\n" + body + "\n```"
                ),
            ),
        ]
        response = await get_last_response(
            call_completion(
                prompt,
                preset=self.summary_preset,
                config=self.config,
                usage=self.usage,
            )
        )
        return (response.content or "").strip()

    async def fold(
        self,
        messages: CONTENT_LIST_TYPE,
        previous: str = "",
    ) -> CompactionResult | None:
        """Summarize the foldable prefix and return the surviving history.

        Atomic: the summary is produced first and nothing is returned until a
        non-empty one exists, so a failed summarization leaves the caller's
        history exactly as it was. Returns ``None`` when there is nothing to
        fold or the model returned no summary.
        """
        prefix, tail = split_history(messages)
        if not prefix:
            logger.debug("Compaction skipped: nothing to fold")
            return None
        logger.debug(f"Compacting {len(prefix)} history messages..")
        summary = await self.summarize(prefix, previous)
        if not summary:
            logger.warning(
                "Compaction produced an empty summary, keeping history intact"
            )
            return None
        logger.debug(f"Compaction completed, folded {len(prefix)} messages")
        return CompactionResult(messages=tail, summary=summary)

    async def compact(self, memory: MemoryModel) -> bool:
        """Fold ``memory`` in place, storing the summary on ``abstract``.

        On success the prefix is dropped, ``abstract`` is replaced and the
        measured usage is cleared so the next request measures itself again.
        Returns whether the fold happened.
        """
        result = await self.fold(memory.messages, memory.abstract)
        if result is None:
            return False
        memory.messages = result.messages
        memory.abstract = result.summary
        memory.usage = None
        return True

    def _weights(self, messages: CONTENT_LIST_TYPE) -> list[int]:
        """Per-message character counts, used as the token-share weights.

        A message with no text at all (a bare tool call) still occupies a
        slot in the payload, so the floor is 1 rather than 0 — a zero weight
        would let it be dropped for free while contributing nothing to the
        estimated total.
        """
        return [
            max(
                1, sum(len(chunk) for chunk in text_generator([msg], full_message=True))
            )
            for msg in messages
        ]

    def _estimate(self, messages: CONTENT_LIST_TYPE, reported: int) -> list[int]:
        """Spread the provider's reported prompt size over the messages.

        The provider reports one number for the whole payload, so the split
        can only be estimated. Weighting by character count tracks the real
        distribution far better than a flat average: a long tool result takes
        a large share and a short user turn takes a small one, whereas the
        average would over-drop when the big messages sit at the tail and
        under-drop when they sit at the head.

        The shares are normalized against ``reported``, so the estimate sums
        back to exactly what the provider measured — the only error is in how
        it is distributed between messages, never in the total.
        """
        weights = self._weights(messages)
        total = sum(weights)
        if not total:
            return []
        return [max(1, round(w / total * reported)) for w in weights]

    def _safe_cut(self, messages: CONTENT_LIST_TYPE, cut: int) -> int:
        """Move ``cut`` to a position the provider's validator will accept.

        ``libchat._validate_msg_list`` enforces two invariants on every
        payload, and dropping a prefix can break both:

        1. every ``tool`` result must follow an assistant message that
           declared its ``tool_call_id``;
        2. every ``tool_call_id`` an assistant declared must have a result.

        The first pass retreats to the newest ``user`` message. A turn is
        self-contained — ``user`` → ``assistant(tool_calls)`` → ``tool``* →
        ``assistant`` — so a turn boundary satisfies both invariants by
        construction, and this is the path taken in practice. When the retreat
        lands on index 0 there is nothing to drop, so the second pass walks
        *forward* to the next boundary instead; without it an over-budget
        history whose first turn is oversized would slide forever and never
        shrink.

        The third pass covers a history that was already inconsistent when
        it arrived (folded by an older version, or written straight to the
        store). A head made of orphaned ``tool`` results is invalid no matter
        where the turn boundary sits, so those are stepped over. Advancing
        changes which assistant messages count as "before the cut", so the
        declared set is rebuilt and the test re-run — hence a loop rather
        than a single check.
        """
        requested = cut
        while cut > 0 and messages[cut].role != "user":
            cut -= 1
        if cut == 0 and requested > 0:
            cut = requested
            while cut < len(messages) - 1 and messages[cut].role != "user":
                cut += 1
            if messages[cut].role != "user":
                return 0

        while cut < len(messages):
            msg = messages[cut]
            if not isinstance(msg, ToolResult):
                break
            declared = {
                tc.id
                for prev in messages[:cut]
                if isinstance(prev, Message) and prev.tool_calls
                for tc in prev.tool_calls
            }
            if msg.tool_call_id in declared:
                break
            cut += 1

        return cut

    def slide(self, messages: CONTENT_LIST_TYPE, reported: int) -> int:
        """Drop the oldest messages until the estimate falls to the target.

        The counterpart to :meth:`compact` under the ``slide`` policy: the
        tail survives verbatim and no extra model call is made, at the cost
        of losing the dropped turns outright.

        ``reported`` is the prompt size the provider measured for the payload
        these messages produced — the caller knows it (``memory.usage``
        between turns, the Step token window inside the agent loop) and the
        message list alone does not carry it.

        The guard reads ``reported`` rather than ``sum(estimates)``: the
        shares are rounded to integers, so their sum can land a token below
        the measurement and read as "still fits" when the caller already
        decided otherwise. ``>=`` triggers, matching ``needs_management``.

        Mutates ``messages`` in place. Returns the number of messages dropped
        (``0`` when nothing moved).
        """
        if reported < self.threshold:
            return 0

        estimates = self._estimate(messages, reported)
        total = sum(estimates)
        need = total - self.slide_target
        consumed = 0
        cut = 0
        while cut < len(messages) - 1 and consumed < need:
            consumed += estimates[cut]
            cut += 1

        cut = self._safe_cut(messages, cut)
        if cut <= 0:
            return 0
        del messages[:cut]
        logger.debug(f"Slid {cut} messages out of the history window")
        return cut


@Node()
def should_manage_context(ability: AbilityState, mem: MemoryContext) -> bool:
    """Condition node: did the history outgrow the budget this round?

    Shared by both policies — ``compact`` and ``slide`` start at the same
    point and differ only in what they do about it.

    Upstream: LOAD_STATE — must have set `mem.memory`.

    Downstream: MANAGE_CONTEXT — runs only when this returns `True`.
    """
    compactor = ContextCompactor(config=ability.config, preset=ability.preset)
    return compactor.needs_management(mem.memory)


@Node(SuspendEnum.MEMORY)
async def MANAGE_CONTEXT(
    ability: AbilityState, mem: MemoryContext, resp: RespState
) -> None:
    """Bring an oversized history back inside the budget.

    Dispatches on ``LLMConfig.context_strategy``: ``compact`` folds the
    oldest prefix into ``memory.abstract``, ``slide`` drops the oldest
    messages outright. Both clear ``memory.usage`` so the next request
    measures itself instead of re-triggering on a stale figure.

    Context Dependencies:
        * AbilityState — provides config and the active preset.
        * MemoryContext — reads/writes `memory.messages`, `memory.abstract`.
        * RespState — provides the run ledger the summary call reports to.

    Upstream: LOAD_STATE — must have set `mem.memory`.

    Downstream: JINJA2_RENDER — renders the new `memory.abstract` into the
    system instruction.

    Suspend Point: `SuspendEnum.MEMORY`.
    """
    memory = mem.memory
    if memory is None:
        raise RuntimeError(
            "Memory is not set, please run `LOAD_STATE` before managing context"
        )
    compactor = ContextCompactor(
        config=ability.config,
        preset=ability.preset,
        usage=resp.usage,
    )
    if compactor.strategy == "slide":
        reported = memory.usage.prompt_tokens if memory.usage is not None else 0
        compactor.slide(memory.messages, reported)
        #  The measurement described a payload that no longer exists; clear it
        #  so the next request measures itself instead of re-triggering on a
        #  stale, larger number.
        memory.usage = None
    else:
        await compactor.compact(memory)


__all__ = [
    "MANAGE_CONTEXT",
    "CompactionResult",
    "ContextCompactor",
    "should_manage_context",
    "split_history",
]
