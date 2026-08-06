# DAGNode

任务计划的一个子步骤,由分解决策产生。DAG 只是**语义层**——执行保持线性
(拓扑序),不是并行图。

```python
from amrita_core.builtins.agent.state import DAGNode

node = DAGNode(
    id="search-web",
    description="Search the web",
    depends_on=["list-files"],
)
```

## 字段

| 字段          | 类型        | 含义                             |
| ------------- | ----------- | -------------------------------- |
| `id`          | `str`       | 语义化 id(兼作 Step 的 phase 名) |
| `description` | `str`       | 该子步骤做什么                   |
| `depends_on`  | `list[str]` | 该子步骤依赖的 id                |

## 相关

- [AgentRunState](AgentRunState.md) —— 持有 `plan: list[DAGNode]`
- [DecomposeDecision](DecomposeDecision.md) —— 产生 DAG 的 LLM 输出
