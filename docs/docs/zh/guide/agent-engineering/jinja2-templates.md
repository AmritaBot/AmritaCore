# Jinja2 模板

系统（train）消息在每次请求前通过 **Jinja2 模板**渲染。这就是向 system
prompt 注入记忆、配置与动态上下文的方式。

## 模板上下文

模板接收以下变量：

| 变量          | 含义                         |
| ------------- | ---------------------------- |
| `train`       | 原始 train 消息              |
| `memory`      | 会话 `MemoryModel`（消息等） |
| `chatobj`     | 当前 `ChatObject`            |
| `config`      | 运行时 `AmritaConfig`        |
| `jinja2_vars` | 你的自定义变量（合并进来）   |

```jinja2
You are a helpful assistant.
Today is {{ memory.metadata.today }}.
User prefers: {{ jinja2_vars.user_language }}
```

通过 `ChatObject(..., jinja2_vars={...})` 或
`agent.get_chatobject(..., jinja2_vars={...})` 传入自定义变量。

## 变量命名安全

**你不能在 `jinja2_vars` 中使用与内置变量同名的键**
（`train`、`memory`、`chatobj`、`config`）——Python 会收到重复关键字参数并
抛 `TypeError`。请使用其他任何名字。

## 最佳实践

- 保持模板小巧；把指令推入模板，而不是整段对话
- 用 `config` 变量按部署切换行为
- 渲染错误会立即暴露——上线前用
  [工作流调试器](../advanced/workflow-debugging.md) 验证模板

## 下一步

[异常排查](troubleshooting.md)——常见失败模式与修复。
