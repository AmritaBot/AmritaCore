# Prompt Engineering

The LLM is a _continuation machine_ — it finishes whatever pattern the context
established. Every technique below follows from that fact.

## 1. End-of-Prompt Instructions Beat Mid-Prompt Ones

Auxiliary LLM calls in the step loop (decomposition, step summaries) are the
perfect example: put the output instruction **at the very end**, as a fresh
`user` message, not in the middle of the system prompt:

```text
Now decide whether the above task needs decomposition.
Output ONLY the JSON object, nothing else:
{"needs_decomposition": bool, "dag": [...], "reason": "..."}
```

Why: the context ends with the agent's last `ToolResult`; without an explicit
final instruction the model "continues the conversation" instead of switching
to JSON output.

## 2. Few-Shot Examples in the System Prompt

A real-world example beats a schema description:

```text
Example 1 (simple):
User: What is 2+2?
Output: {"needs_decomposition": false, "dag": [], "reason": "Simple arithmetic."}

Example 2 (complex):
User: Summarize the repo docs...
Output: {"needs_decomposition": true, "dag": [{"id": "list-files", ...}], ...}
```

## 3. Semantic Ids, Not Step Numbers

When asking for structured plans, require short **semantic** ids
(`search-web`, `read-docs`) — they double as Step phase names and produce
readable timelines. Explicitly forbid `step-1`, `step-2`.

## 4. Strict JSON Discipline

- Say "Output strictly as JSON"
- Degrade gracefully when the model ignores you: wrap parsing in
  `try/except` and fall back (the step loop does this for decomposition and
  summaries)
- Empty responses happen with thinking models — treat them as a _degraded_
  path, don't parse garbage

## 5. The Give-Up Prompt Pattern

When an agent loops, instruct it to stop _and tell it tools are illegal_:

```text
You have been calling the same tool repeatedly without making progress —
the task is now ABANDONED.
- Use ONLY the information you have already gathered.
- Any additional tool call is ILLEGAL and will be rejected.
- Write your final answer as plain text now.
(Give up when there are no solutions.)
```

This works because it (a) changes the pattern (abandoned), (b) forbids the
looping action explicitly, and (c) gives a concrete next action.

## Next

[Jinja2 Templates](jinja2-templates.md) — the train-message template system.
