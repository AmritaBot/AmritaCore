# 5. Memory and Sessions

## Why It Matters

A conversation is more than one request: the agent should remember what was said
earlier. AmritaCore separates two concerns:

- **`session_id`** — an _identifier_ for one conversation. It is **unique**: it
  names a conversation, it does not "share" anything by itself.
- **Data storage** — where the conversation history actually lives. That is the
  job of the **data backend**, not the framework.

This tutorial shows how the two fit together.

## 1. A Unique Session ID

Every `ChatObject` needs a unique `session_id` (or a pre-built `context` — the
two are mutually exclusive):

```python
import uuid

chat = agent.get_chatobject(
    "My name is Alice.",
    session_id=str(uuid.uuid4()),  # unique per conversation
)
async with chat.begin():
    ...
```

The id is passed to the backend, which uses it as the key under which history
is stored. Two conversations with _different_ ids are always independent.

## 2. Who Stores the Data? The Backend

AmritaCore itself does **not** store conversation history. It hands the
`session_id` to the data backend (`AbilityBackend` / `MemoryBackend`), and the
backend decides where the data lives:

- **`LegacyBackend`** (default) — keeps memory **in-process**: the history for
  an id lives only as long as the process does, in a global container.
- **Your own backend** — implement the backend interfaces to store history in a
  database, Redis, files, ... (see [Data Layer](../concepts/data.md)).

So whether two `ChatObject` instances "see the same history" is decided by the
**backend's storage**, not by reusing an id. If your backend keeps data under an
id, a second conversation with that id will load it; if it does not, it won't.

## 3. Memory Summarization

Long sessions hit context limits. Enable automatic summarization:

```python
from amrita_core import minimal_init
from amrita_core.config import AmritaConfig

config = AmritaConfig()
config.llm.enable_memory_abstract = True
config.llm.memory_abstract_threshold = 4000  # tokens
await minimal_init(config)
```

When the prompt exceeds the threshold, older turns are summarized before the
request is sent. (The built-in step strategy additionally performs between-Step
compression — see [Step Loop](../advanced/step-loop.md).)

## 4. What Just Happened

- `session_id` is a **unique identifier** for a conversation — naming only
- The **data backend** decides where history lives and what survives
- Summarization keeps long sessions within the context window

## Next

You have completed the tutorial path. Recommended next steps:

- [Concepts](../concepts/index.md) — understand what just happened under the hood
- [Extensions & Integration](../extensions-integration/index.md) — adapters, MCP, custom tokenizers
- [Agent Engineering](../agent-engineering/index.md) — prompt tuning and troubleshooting
