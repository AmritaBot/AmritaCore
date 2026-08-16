# 安全机制

## Cookie 安全检测

AmritaCore 可检测模型响应中的敏感 cookie 值并终止会话防止数据泄露：

- **启用**：`config.cookie.enable_cookie = True`
- **检测**：响应被扫描配置的 cookie 值
- **响应**：命中后会话以通用错误消息终止

```python
from amrita_core.config import AmritaConfig

config = AmritaConfig()
config.cookie.enable_cookie = True
# 配置要保护的 cookie 值
```

## 提示注入考量

工具结果与 peer 消息以文本进入模型上下文。把它们当作不可信输入：

- **内置策略**把工具结果存为 `ToolResult` 配对；已弃用的
  `HybridReActAgentStrategy` 的 XML 渲染风格注入风险更高（纯文本结果）。
- **Peer 消息**（`send_to_producer`）以 `[peer message]` 标记追加——设计
  system prompt 时把该标记当作数据而非指令。
- **自定义工具**：结果来自外部源时，返回前先校验工具输出。

## 上下文中的敏感数据

- 策略持有 `chat_object` 作为生命周期句柄——不要记录它
- `StateContext`（已弃用访问器，**v0.14.0** 移除）暴露会话 id / 记忆 /
  ability——序列化时视为敏感

## 模板安全

Jinja2 模板变量不得与内置名冲突（`train`、`memory`、`chatobj`、`config`）
——冲突抛 `TypeError`（见 [Jinja2 模板](agent-engineering/jinja2-templates.md)）。

## 会话隔离

记忆按 `session_id` 键控；不同 id 完全隔离。多租户部署使用唯一、不可猜测的
会话 id。
