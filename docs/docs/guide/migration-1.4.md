# Migration Guide: 1.3 -> 1.4

AmritaCore 1.4 lets a tool return something other than text — an image, a file
reference — and moves adapter capability flags into one `FeatureFlag` object.
Existing tools and adapters keep working; the checklist at the end lists what to
re-check.

## At a Glance

| Changed                                          | What to do                                                                                                                                        |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ToolResult.content`                             | Type widened from `str` to `str \| list[Content]`. Code that reads `.content` as a string should use `.text` (or `content_text()`).                |
| Tool handlers                                   | May return `str \| list[Content]`. Everything else is still JSON-encoded, so no change is required.                                                |
| `ModelAdapter.supports_agentic_call`             | Deprecated. Read `features.agentic_call`; the old field is translated and kept in sync, so third-party adapters need no edit to keep working.       |
| `ModelAdapter.features` (new `FeatureFlag`)      | Adapters now declare what they can put on the wire. The gateway degrades what a protocol cannot carry.                                             |
| `StepToolReturnEvent.result`                     | Type widened to match `ToolResult.content`; handlers that read it as a string should use `content_text()`.                                          |

## 1. Tool Results Can Be Content Blocks

`ToolResult.content` is now `TOOL_RESULT_CONTENT` (`str | list[Content]`). A tool
that returns a `list[Content]` — text, image, file blocks — has it stored and
forwarded as-is:

```python
@simple_tool
async def screenshot(url: str) -> list[Content]:
    """Capture a page."""
    return [
        TextContent(text=f"captured {url}"),
        ImageContent(image_url=ImageUrl(url=png)),
    ]
```

A `list[Content]` is passed through untouched; **any other** return value is
still JSON-encoded into a string, exactly as before. Returning a `dict`, a
number or a plain `list` of dicts behaves the way it used to.

The text view is what everything outside the wire reads:

```python
result.text  # "captured https://...<image>"
content_text(result.content)
```

Non-text blocks collapse to `<image>` / `<file:name>` there. If your code does
`result.content.startswith(...)` or passes `.content` into a string API, switch
it to `.text`. This applies to `StepToolReturnEvent.result` too — matchers that
inspect the result should go through `content_text()`.

## 2. Capabilities Are Declared Once, in `FeatureFlag`

`supports_agentic_call` was a single boolean for a single capability. There are
now three, and they describe the **wire**, not the model:

```python
from amrita_core.base.adapter import FeatureFlag, ModelAdapter


class MyAdapter(ModelAdapter):
    features = FeatureFlag(
        agentic_call=True,  # implements agentic_call_api()
        input_multimodal=True,  # non-text blocks in user/system content
        tool_result_multimodal=False,  # non-text blocks in tool message content
    )
```

Defaults are all `False` — a flag is a claim, and an adapter that says nothing is
assumed to carry nothing.

Compatibility: an adapter that declares only `supports_agentic_call = True` has
it translated into `features.agentic_call` at class creation, and the old
attribute stays in sync with the new one. Nothing breaks; the field is
deprecated, not removed.

Assign the **whole** `FeatureFlag` on the subclass — it is a frozen dataclass, so
in-place field assignment was never possible.

## 3. The Gateway Checks What the Protocol Cannot Carry

Before each request, the gateway looks at the target adapter's `features`. Two
kinds of content take different paths:

- a **tool result** carrying a block the protocol cannot hold raises
  `UnsupportedContentError` before the request is sent. The agent loop replaces
  the offending blocks with the error's `notice` on a **copy** of the payload and
  retries the round, so the model knows the media is missing and can ask the tool
  for text or pick another tool;
- a **`user` / `system` message** is degraded: the block becomes a text notice on
  a **copy** of the message, and a warning is logged once per protocol.

```
<image omitted: the current adapter cannot carry it>
```

Consequences worth knowing:

- **Stored history is untouched.** A later fallback to a stronger adapter still
  has the original blocks.
- **One warning per (protocol, payload kind).** A long-running process does not
  flood its log; it also will not warn again after the first turn. The tool-result
  path logs no warning at all — the exception is the signal.
- **Fallback re-negotiates.** Each attempt is prepared against the preset that is
  actually going to be used, so a protocol switch mid-run is handled. A capability
  mismatch is not retried as a transport failure — swapping presets cannot add
  wire support.
- **`file` blocks are not carried by any built-in adapter.** The Anthropic
  endpoint needs `source.type="file"` plus the `anthropic-beta:
  files-api-2025-04-14` header, which the adapter cannot inject yet; the block
  becomes `<file:name omitted: ...>` instead of vanishing. Previously it was
  dropped silently, which left the model answering about a file it never got.

Built-in declarations:

| Adapter                        | `input_multimodal` | `tool_result_multimodal` |
| ------------------------------ | ------------------ | ------------------------ |
| `openai` (Chat Completions)    | ✅                 | ❌                       |
| `openai-responses` (Responses) | ✅                 | ✅                       |
| `anthropic` (Messages)         | ✅                 | ✅                       |

## Checklist

- [ ] Code that reads `ToolResult.content` as a string now uses `.text`.
- [ ] Matchers reading `StepToolReturnEvent.result` use `content_text()`.
- [ ] Custom adapters declare `features` (or keep the deprecated
      `supports_agentic_call`, which still works).
- [ ] If you rely on images from tools, check your adapter declares
      `tool_result_multimodal`; otherwise `UnsupportedContentError` is raised and
      the model is handed a text notice to retry from.
- [ ] Catch `AdapterError` (not vendor SDK exceptions) around adapter calls;
      the original is on `.original`.
