# BaseReActAgentStrategy

`BaseReActAgentStrategy` 是 ReAct 风格 agent 的抽象基类，实现了模板方法模式。提供共享功能包括：

- 工具调用编排和执行流控制
- 推理消息生成和处理
- 循环检测与恢复机制（检测重复推理调用过多）
- 工具调用通知处理
- 通用错误处理模式
- 通过 `_suggested_stop` 标志统一停止状态管理

## 描述

此抽象类定义了所有 ReAct 风格策略继承的通用执行框架，确保行为一致，同时允许通过抽象方法进行自定义。

## 子类

- [`ReActAgentStrategy`](ReActAgentStrategy.md)：标准实现，支持 `"agent-mixed"` 类别
- [`HybridReActAgentStrategy`](HybridReActAgentStrategy.md)：针对 MoE 架构模型优化的实现
