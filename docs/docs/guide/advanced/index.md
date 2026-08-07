# Advanced

For developers who want to go beyond the public API — understand the execution
engine, write custom strategies, and debug at the workflow level.

> **About AmritaSense**: these pages recap AmritaSense concepts _inline_ where
> the Core needs them, and link to [sense.amritabot.com](https://sense.amritabot.com)
> for the full story. Sense-specific material is not duplicated here.

## Topics

| Page                                             | Covers                                                |
| ------------------------------------------------ | ----------------------------------------------------- |
| [AmritaSense Overview](amrita-sense-overview.md) | The execution substrate: instructions, VM, DI, stream |
| [Workflow Engine](workflow-engine.md)            | How ChatObject's pipeline is composed and executed    |
| [Suspend & Resume](suspend.md)                   | Pausing the workflow; the bidirectional stream        |
| [The Step Loop](step-loop.md)                    | The built-in step-driven ReAct loop, event by event   |
| [Workflow Debugging](workflow-debugging.md)      | Step through the interpreter, breakpoints, middleware |

## Prerequisites

- [Concepts](../concepts/index.md) — especially ChatObject and Agent Strategy
- [Agent Engineering](../agent-engineering/index.md) for the practical layer
