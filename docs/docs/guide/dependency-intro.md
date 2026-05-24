# AmritaSense Dependency

> Starting from AmritaCore v0.9.0rc1, core infrastructure has been extracted to the `amrita-sense` package.

## Overview

`amrita-sense` (>=0.2.1) is the **foundational runtime** for AmritaCore, providing the workflow engine, event system, and streaming capabilities. AmritaCore builds the Agent layer (strategy, sessions, tools, MCP, adapters) on top of it.

**AmritaCore = AmritaSense + Agent Layer**

Full documentation: [**https://sense.amritabot.com**](https://sense.amritabot.com)

## Migrated Modules Quick Reference

| AmritaCore Old Path                                                    | AmritaSense New Path          | AmritaSense Docs                                                                           |
| ---------------------------------------------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------ |
| `amrita_core.streaming`                                                | `amrita_sense.streaming`      | [SuspendObjectStream API](https://sense.amritabot.com/reference/api/suspend-object-stream) |
| `amrita_core.logging`                                                  | `amrita_sense.logging`        | Built-in — no separate docs                                                                |
| `amrita_core.hook.event`                                               | `amrita_sense.hook.event`     | [Event System](https://sense.amritabot.com/guide/advanced/event_system)                    |
| `amrita_core.hook.matcher`                                             | `amrita_sense.hook.matcher`   | [Event System](https://sense.amritabot.com/guide/advanced/event_system)                    |
| `amrita_core.hook.exception`                                           | `amrita_sense.hook.exception` | [Control Flow](https://sense.amritabot.com/guide/concepts/flow_control)                    |
| Workflow engine (`Node`, `NodeComposeRendered`, `WorkflowInterpreter`) | `amrita_sense` top-level      | [Compose & Execute](https://sense.amritabot.com/guide/concepts/compose_and_exec)           |
| `ALIAS`, `ARCHIVED_NODES`                                              | `amrita_sense` top-level      | [Control Flow](https://sense.amritabot.com/guide/concepts/flow_control)                    |
| Dependency injection (`Depends`)                                       | `amrita_sense.runtime.deps`   | [Dependency Injection](https://sense.amritabot.com/guide/advanced/dependency_injection)    |

## Installation

```bash
pip install amrita_core
# amrita-sense is installed automatically — no manual steps required
```

## Migration Guide

| Old Import (amrita_core)           | New Import (amrita-sense)           |
| ---------------------------------- | ----------------------------------- |
| `amrita_core.logging`              | `amrita_sense.logging`              |
| `amrita_core.streaming`            | `amrita_sense.streaming`            |
| `amrita_core.hook.matcher`         | `amrita_sense.hook.matcher`         |
| `amrita_core.hook.event.BaseEvent` | `amrita_sense.hook.event.BaseEvent` |
| `amrita_core.hook.exception`       | `amrita_sense.hook.exception`       |

Old import paths still work but are deprecated; they emit a `DeprecationWarning`.

## Version Requirements

- **amrita-sense**: `>=0.2.1`
- **Python**: `>=3.10,<3.15`
