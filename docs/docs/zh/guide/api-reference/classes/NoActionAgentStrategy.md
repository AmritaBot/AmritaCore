# NoActionAgentStrategy

`NoActionAgentStrategy` 是一个简单的工作流策略，不执行任何操作。可在需要放弃工具调用过程时使用。

## 继承

- 继承自：[AgentStrategy](AgentStrategy.md)
- 类别：`"workflow"`

## 方法

### run()

无操作实现，立即返回而不执行任何操作。

### on_exception(exc)

无操作异常处理器，立即返回。

**参数**：

- `exc` (BaseException)：发生的异常
