# 提示词工程

LLM 是**续写机器**——它会完成上下文建立的任何模式。下面的每个技巧都源于
这一事实。

## 1. 末尾指令胜过中间指令

step 循环中的辅助 LLM 调用（分解、Step 摘要）是最佳例子：把输出指令放在
**最末尾**，作为新的 `user` 消息，而不是放在 system prompt 中间：

```text
Now decide whether the above task needs decomposition.
Output ONLY the JSON object, nothing else:
{"needs_decomposition": bool, "dag": [...], "reason": "..."}
```

原因：上下文以 agent 最后的 `ToolResult` 结尾；没有明确的末尾指令，模型会
"继续对话"而不是切换为 JSON 输出。

## 2. System Prompt 中的 Few-Shot 示例

真实世界示例胜过 schema 描述：

```text
Example 1 (simple):
User: What is 2+2?
Output: {"needs_decomposition": false, "dag": [], "reason": "Simple arithmetic."}

Example 2 (complex):
User: Summarize the repo docs...
Output: {"needs_decomposition": true, "dag": [{"id": "list-files", ...}], ...}
```

## 3. 语义化 id，而非编号

要求结构化计划时，指定简短**语义化** id（`search-web`、`read-docs`）——它们
兼作 Step 的 phase 名，产生可读的时间线。显式禁止 `step-1`、`step-2`。

## 4. 严格 JSON 纪律

- 说"Output strictly as JSON"
- 模型不听话时优雅降级：`try/except` 包裹解析并回退（step 循环对分解和
  摘要就是这样做的）
- thinking 模型会出现空响应——把它当作*降级*路径，不要解析垃圾

## 5. Give-Up Prompt 模式

agent 循环时，指示它停止**并告诉它工具是非法的**：

```text
You have been calling the same tool repeatedly without making progress —
the task is now ABANDONED.
- Use ONLY the information you have already gathered.
- Any additional tool call is ILLEGAL and will be rejected.
- Write your final answer as plain text now.
(Give up when there are no solutions.)
```

有效因为它 (a) 改变模式（abandoned）、(b) 明确禁止循环动作、(c) 给出具体
下一步动作。

## 下一步

[Jinja2 模板](jinja2-templates.md)——train 消息模板系统。
