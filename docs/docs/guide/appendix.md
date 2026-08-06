# Appendix & Design Philosophy

## Design Philosophy

The decisions below shape the whole framework. Understanding them explains
_why_ the code looks the way it does.

### ChatObject is the Lifecycle Manager — the Unit of a Dialogue

`ChatObject` is not a thin wrapper: it owns the workflow, the interpreter, the
bidirectional stream, and every DI context for one conversation. Strategies and
hooks receive resources; ChatObject wires them together. That makes it the
basic unit of a dialogue and the natural place to attach middleware, sessions,
and lifecycle.

### The Step Is the Unit of Prompt Engineering

The built-in ReAct loop treats each **Step** (one DAG node) as an explicit
prompt-engineering unit: enter → execute → summarize. No hardcoded planner or
subagent machinery — the LLM decomposes into a **semantic DAG**, the framework
walks it in topological order with stdlib `graphlib`, and execution stays
linear. The DAG is a hint layer, not a parallel graph.

### Everything Observable and Interruptible

Every boundary emits events and metadata: step intro/leave, iteration, tool
call/return. Matchers mutate events; `StepAbortError` is the control-flow
escape hatch. Stall detection runs _inside_ the loop so a stuck agent stops
burning tokens.

### Framework-Managed Loop, Strategy-Managed Step

`get_category()` decides who owns the loop: `agent`/`agent-mixed` → the
framework loops and calls `single_execute()` per round; `rag`/`workflow` →
the strategy owns everything. This keeps custom strategies small and the
framework's guarantees (limits, rollback, events) uniform.

### Sense-Specific Knowledge Is Not Duplicated

AmritaCore recaps AmritaSense inline where needed and links out for the rest.
The documentation journey mirrors the engineering journey: run → use →
understand → extend → tune → go deeper.

## Naming Conventions

### `*Manager` vs `Multi*Manager`

Manager classes follow one simple rule:

| Name                                                            | Kind                   | Scope                                                                                                     |
| --------------------------------------------------------------- | ---------------------- | --------------------------------------------------------------------------------------------------------- |
| `ToolsManager`, `ClientManager`, `PresetManager`                | **Singleton**          | A global, process-wide container — everyone shares the same instance                                      |
| `MultiToolsManager`, `MultiClientManager`, `MultiPresetManager` | **Ordinary container** | Create your own instances for isolation (per-session tools, per-session MCP clients, per-session presets) |

The non-`Multi` managers are implemented as singletons (`__new__` + `_instance`)
over their `Multi*` base; the `Multi*` versions are plain instantiable
containers. Examples:

- `@simple_tool` registers into the global `ToolsManager`
- a `MultiToolsManager` instance can be attached to a session's ability for
  per-session tools
- `ClientManager()` (singleton) is what `load_amrita()` drives; a
  `MultiClientManager` instance gives a session its own MCP set

### Other prefixes

- `Base*` — abstract base classes (`BaseTokenizer`, `BaseReActAgentStrategy`)
- `Legacy*` — backward-compatible implementations (`LegacyBackend`)

## Glossary

| Term                      | Meaning                                                                |
| ------------------------- | ---------------------------------------------------------------------- |
| **Agent**                 | A strategy-driven executor that calls tools to achieve goals           |
| **ChatObject**            | The lifecycle manager — the unit of a dialogue                         |
| **Step**                  | One DAG node of the built-in step loop (enter → execute → leave)       |
| **Stall**                 | Repeating identical tool signatures within a Step                      |
| **`SuspendObjectStream`** | Bidirectional stream between workflow (producer) and caller (consumer) |
| **DI Context**            | Typed state injected into workflow nodes (e.g. `AgentLoopState`)       |
| **Workflow**              | A pre-compiled AmritaSense instruction sequence                        |
| **Matcher**               | An event handler registered by type string                             |
| **Preset**                | Bundle of endpoint + model + thinking config + tools                   |
| **Backend**               | `AbilityBackend` / `MemoryBackend` implementations                     |
| **Session**               | Isolated conversation history keyed by `session_id`                    |

## Abbreviations

API · JSON · HTTP · LLM · MCP (Model Context Protocol) · MoE (Mixture of
Experts) · VM (Virtual Machine) · DI (Dependency Injection) · DAG (Directed
Acyclic Graph)

## Project Resources

- **Repository**: [github.com/AmritaBot/AmritaCore](https://github.com/AmritaBot/AmritaCore)
- **Issues**: report bugs and feature requests in GitHub Issues
- **AmritaCore site**: [core.amritabot.com](https://core.amritabot.com)
- **AmritaSense docs**: [sense.amritabot.com](https://sense.amritabot.com)
- **Contributing**: see `CONTRIBUTING.md` in the repository
