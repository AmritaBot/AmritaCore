"""Message normalization — make history fit the active model's capabilities.

Some providers accept only plain text. A conversation that carries content
blocks (images, files) therefore has to be flattened before the request is
built, or the adapter sends blocks the model cannot read.

This is deliberately a separate concern from compaction: normalization is
lossless flattening of what is already there, while compaction throws history
away. Keeping them apart means either can run alone.

```mermaid
flowchart LR
    A[message.content: list of blocks] -->|multi-modal off| B[message.content: text]
    A -->|multi-modal on| A
```
"""

from amrita_sense import Node

from amrita_core.contexts import AbilityState, MemoryContext
from amrita_core.types.content import CT_MAP, Content
from amrita_core.types.message import Message


def flatten_content(message: Message) -> bool:
    """Replace a block-list body with its text, in place.

    Returns whether the message was rewritten. Non-user messages and messages
    whose body is already a string are left alone: assistant turns may need
    their structure preserved for tool-call pairing.
    """
    if message.role != "user" or not isinstance(message.content, list):
        return False
    parts: list[str] = []
    for block in message.content:
        if isinstance(block, dict):
            validator = CT_MAP.get(block["type"])
            if not validator:
                raise ValueError(f"Invalid content type: {block['type']}")
            block = validator.model_validate(block)
        typed: Content = block
        if typed["type"] == "text":
            parts.append(typed["text"])
    message.content = "".join(parts)
    return True


@Node()
def NORMALIZE_MESSAGES(ability: AbilityState, mem: MemoryContext) -> None:
    """Flatten content blocks when the active model cannot take them.

    A no-op when ``config.llm.enable_multi_modal`` is on. Runs on the loaded
    history, so it belongs after `LOAD_STATE` and before anything that renders
    or sends the messages.

    Context Dependencies:
        * AbilityState — provides `llm.enable_multi_modal`.
        * MemoryContext — reads/writes the message bodies.

    Upstream: LOAD_STATE — must have set `mem.memory`.

    Downstream:
        * JINJA2_RENDER / BUILD_MESSAGE — consume the flattened messages.
        * COMPACT — summarizes text instead of raw blocks.
    """
    if ability.config.llm.enable_multi_modal:
        return
    memory = mem.memory
    if memory is None:
        raise RuntimeError(
            "Memory is not set, please run `LOAD_STATE` before normalizing"
        )
    for message in memory.messages:
        if isinstance(message, Message):
            flatten_content(message)


__all__ = ["NORMALIZE_MESSAGES", "flatten_content"]
