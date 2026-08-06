# DAGNode

A sub-step of the task plan produced by the decomposition decision. The DAG is
a **semantic layer only** — execution stays linear (topological order), it is
not a parallel graph.

```python
from amrita_core.builtins.agent.state import DAGNode

node = DAGNode(
    id="search-web",
    description="Search the web",
    depends_on=["list-files"],
)
```

## Fields

| Field         | Type        | Meaning                                |
| ------------- | ----------- | -------------------------------------- |
| `id`          | `str`       | Semantic id (also the Step phase name) |
| `description` | `str`       | What this sub-step does                |
| `depends_on`  | `list[str]` | Ids this sub-step depends on           |

## Related

- [AgentRunState](AgentRunState.md) — holds `plan: list[DAGNode]`
- [DecomposeDecision](DecomposeDecision.md) — the LLM output producing the DAG
