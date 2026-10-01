"""History compaction — the policy object and its workflow nodes.

``ContextCompactor`` owns everything about compaction: where the trigger sits
relative to the model's attention window, how a history prefix is summarized,
and how the fold is applied. Both the between-turn node and the between-Step
compression inside the agent loop drive that same object, so one model is
described by one threshold.

The summary is stored on ``MemoryModel.abstract`` and rendered back into the
system instruction by the train template, so nothing is injected into the
message list and provider message-ordering rules stay untouched.

```mermaid
flowchart LR
    A[MemoryModel.messages] -->|split at newest user message| B[prefix]
    A --> C[tail]
    B -->|summarize, merged with memory.abstract| D[memory.abstract]
    C --> E[memory.messages]
    D --> F[train template renders SUMMARY]
```
"""

from dataclasses import dataclass

from amrita_sense import Node
from amrita_sense.logging import logger

from amrita_core.config import AmritaConfig
from amrita_core.consts import ABSTRACT_INSTRUCTION
from amrita_core.contexts import AbilityState, MemoryContext, RespState
from amrita_core.enums import SuspendEnum
from amrita_core.libchat import call_completion, get_last_response, text_generator
from amrita_core.types.memory import MemoryModel
from amrita_core.types.message import CONTENT_LIST_TYPE, Message
from amrita_core.types.preset import ModelPreset, resolve_max_context
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
    """Compaction policy and operation for one model.

    Constructed per use site from the live config, preset and run ledger, so
    the trigger always reflects the model actually being called.

    ```mermaid
    flowchart TD
        C[ContextCompactor] --> B[budget: preset window or global fallback]
        C --> T[threshold: budget x compaction_trigger_ratio]
        C --> S[should_compact: measured prompt vs threshold]
        C --> F[fold: summarize prefix, keep tail]
    ```
    """

    config: AmritaConfig
    preset: ModelPreset | None = None
    usage: SessionUsageProxy | None = None
    instruction: str = ABSTRACT_INSTRUCTION
    """System prompt handed to the summarizer."""

    @property
    def enabled(self) -> bool:
        """Whether the user asked for compaction at all."""
        return self.config.llm.enable_compaction

    @property
    def budget(self) -> int:
        """Input-token budget: the preset's window, else the global default."""
        if self.preset is None:
            return self.config.llm.session_tokens_windows
        return resolve_max_context(self.preset, self.config)

    @property
    def threshold(self) -> int:
        """Prompt size at which compaction is forced.

        Derived from the attention window so the trigger follows the model
        instead of a hand-maintained global number.
        """
        return int(self.budget * self.config.llm.compaction_trigger_ratio)

    @property
    def message_limit(self) -> int:
        """Message count at which compaction is forced regardless of tokens.

        The token trigger needs the provider to report usage; this fallback
        covers gateways that report none, and very large windows.
        """
        return self.config.llm.memory_length_limit

    def should_compact(self, memory: MemoryModel | None) -> bool:
        """Whether ``memory`` should be folded before the next request.

        Fires on whichever trigger comes first: the prompt size the provider
        reported for the previous request (no local tokenizer needed), or the
        message-count fallback. Returns ``False`` when compaction is disabled
        or there is no prefix that could be folded.
        """
        if not self.enabled or memory is None:
            return False
        prefix, _ = split_history(memory.messages)
        if not prefix:
            return False
        if self.message_limit > 0 and len(memory.messages) >= self.message_limit:
            return True
        if memory.usage is None:
            return False
        return memory.usage.prompt_tokens >= self.threshold

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
                preset=self.preset,
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


@Node()
def should_compact(ability: AbilityState, mem: MemoryContext) -> bool:
    """Condition node: has the last measured prompt filled the threshold?

    Upstream: LOAD_STATE — must have set `mem.memory`.

    Downstream: COMPACT — runs only when this returns `True`.
    """
    compactor = ContextCompactor(config=ability.config, preset=ability.preset)
    return compactor.should_compact(mem.memory)


@Node(SuspendEnum.MEMORY)
async def COMPACT(ability: AbilityState, mem: MemoryContext, resp: RespState) -> None:
    """Fold the conversation prefix into ``memory.abstract``.

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
            "Memory is not set, please run `LOAD_STATE` before compacting"
        )
    compactor = ContextCompactor(
        config=ability.config,
        preset=ability.preset,
        usage=resp.usage,
    )
    await compactor.compact(memory)


__all__ = [
    "COMPACT",
    "CompactionResult",
    "ContextCompactor",
    "should_compact",
    "split_history",
]
