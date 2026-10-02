# Migration Guide: 1.1 → 1.2

AmritaCore 1.2 turns history management into an explicit **policy**. The boolean
that used to enable or disable it is gone, and with it two identifiers that only
made sense while there was a single policy. This page lists every breaking change
and what to use instead.

## At a Glance

| Removed / renamed                                       | Replacement                                                       |
| ------------------------------------------------------- | ----------------------------------------------------------------- |
| `LLMConfig.enable_compaction`                           | `LLMConfig.context_strategy` (`"compact"` / `"slide"` / `"none"`) |
| `LLMConfig.auto_retry`                                  | (none — the framework never read it)                              |
| `COMPACT_HISTORY` (pre-composed pipeline)               | `MANAGE_HISTORY`                                                  |
| `COMPACT` (workflow node)                               | `MANAGE_CONTEXT`                                                  |
| `should_compact` (the node predicate)                   | `should_manage_context`                                           |

## 1. History Is a Policy, Not a Switch

`enable_compaction` was a boolean, so switching it off left history unbounded and
the provider rejected the request once the window was exceeded. It is replaced by
`context_strategy`, which says what should happen instead:

```python
# before
config.llm.enable_compaction = True

# after
config.llm.context_strategy = "compact"  # "compact" | "slide" | "none"
```

| Value       | Effect                                                                                                           |
| ----------- | ---------------------------------------------------------------------------------------------------------------- |
| `"compact"` | Folds the oldest prefix into an LLM summary stored on `MemoryModel.abstract`. One extra call per trim, gist kept |
| `"slide"`   | Drops the oldest messages outright, down to `slide_target_ratio` × the window. No extra call, tail kept verbatim |
| `"none"`    | Nothing — history grows until the provider rejects the request                                                   |

The triggers are unchanged: the prompt size the provider reported for the previous
request reaching `compaction_trigger_ratio` × the preset's `max_context`, or the
history reaching `memory_length_limit` messages.

`"none"` also disables overflow recovery — with no policy to shrink history,
retrying after a `ContextOverflowError` would fail identically.

## 2. `slide` Costs Nothing but Forgets

The new `"slide"` policy is for sessions whose early turns are disposable: a long
tool-calling run, where paying for a summary call on every trim is worse than
losing the transcript.

It needs no tokenizer. Each message's share of the reported prompt size is
estimated by normalizing its rendered length, so the weights sum back to the
measurement, and the trim lands at `slide_target_ratio` × `max_context`:

```python
config.llm.context_strategy = "slide"
config.llm.slide_target_ratio = 0.7  # must stay below compaction_trigger_ratio
```

The cut never lands mid-turn and never strands a tool result whose declaring call
it removed, so the trimmed payload still passes the gateway validator.

Keep `slide_target_ratio` below `compaction_trigger_ratio`. Equal values would
trim history straight back onto the trigger and re-run on every request.

## 3. `auto_retry` Is Gone

`LLMConfig.auto_retry` was never read by the framework — `max_retries` and
`max_fallbacks` are what actually govern retrying. Setting it had no effect, so it
was removed rather than left as a decoy. Delete the assignment; there is nothing
to replace it with.

## 4. The Node and Pipeline Names Followed

Both names assumed the only policy was folding, which is no longer true:

| Before                  | After                                    |
| ----------------------- | ---------------------------------------- |
| `COMPACT` node          | `MANAGE_CONTEXT` node                    |
| `COMPACT_HISTORY` graph | `MANAGE_HISTORY` graph                   |
| `should_compact` node   | `should_manage_context` node             |

`ContextCompactor.should_compact()` is still there — it is the `"compact"`-only
narrowing of the new `needs_management()` predicate, for callers that want to ask
"would this fold?" rather than "does this policy want to run?".

These only matter if you compose your own workflow or assert on the pipeline;
passing `workflow=None` or one of the shipped `SIMPLE_*` graphs is unaffected.

## Next

[API Reference](api-reference/index.md) — the current surface, or
[Migration Guide: 0.13 → 1.0](migration.md) — the previous breaking release.
