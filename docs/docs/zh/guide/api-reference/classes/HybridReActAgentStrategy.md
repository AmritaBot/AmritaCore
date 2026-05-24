# HybridReActAgentStrategy

`HybridReActAgentStrategy` 是一种专门针对**混合专家（MoE）架构模型**优化的Agent策略。

此策略解决了某些MoE模型在区分工具和完成标识符时内部状态机的模糊性问题。与依赖显式ToolCall-ToolResult交互的传统工具链方法不同，这种混合方法使用ToolCall触发结合将纯文本直接附加到上下文。

## 继承关系

- 继承自: [BaseReActAgentStrategy](BaseReActAgentStrategy.md)
- 类别: `"agent-mixed"`

## 关键特性

- **ToolCall触发**: 通过标准ToolCall机制启动工具执行
- **基于上下文的集成**: 将工具结果作为纯文本消息附加，而不是结构化的ToolResult对象
- **XML标签格式**: 使用 `<TOOL_CALL>` 和 `<TOOL_RESULT>` XML标签表示工具交互
- **MoE特定优化**: 解决MoE模型在区分工具调用状态和完成状态时遇到的问题

## 属性

- `regexes` (ClassVar[list[tuple[re.Pattern, str]]]): 用于XML标签清理的正则表达式
- `_tool_call_jinja2` ([Template](https://jinja.palletsprojects.com/)): 用于渲染工具调用和结果的Jinja2模板
- `_process_message` (list[str]): 处理工具消息的临时存储

## 构造函数参数

- `ctx` ([StrategyContext](StrategyContext.md)): 包含chat_object、配置和消息上下文的策略上下文

## 工具函数模式

```xml
<!-- 工具调用 -->
<TOOL_CALL name="tool">
    <PARAMS>
        <!-- 参数作为键值对传递 -->
        <PARAM name="param1">value1</PARAM>
    </PARAMS>
</TOOL_CALL>

<!-- 工具结果 -->
<TOOL_RESULT name="tool">
   工具执行结果内容
</TOOL_RESULT>
```

## 安全考虑

**⚠️ 重要安全警告**:

- **提示注入风险**: 将工具结果作为纯 `user` 消息附加可能会在工具输出不可信或未清理时使模型暴露于注入攻击
- **最小化清理**: 此策略仅提供基本的标签对转义，**不执行**语义级过滤或内容验证
- **安全责任**: 用户**必须**在生产环境中为工具结果实现全面的输入验证、语义分析和内容清理

## 使用示例

```python
import asyncio
from amrita_core import create_agent, minimal_init
from amrita_core.builtins.agent import HybridReActAgentStrategy

async def use_hybrid_strategy():
    # 初始化AmritaCore
    await minimal_init()

    # 为MoE模型创建带有混合策略的Agent
    agent = create_agent(
        url="https://api.moemodel.com",
        key="your-api-key",
        strategy=HybridReActAgentStrategy
    )

    # 使用Agent
    chat = agent.get_chatobject("使用可用工具分析这些数据")
    async with chat.begin():
        response = await chat.full_response()
```

## 何时使用

当使用以下情况时使用 `HybridReActAgentStrategy`：

- **混合专家（MoE）模型**，如Mixtral、Qwen-MoE等
- 模型在处理标准ToolCall-ToolResult消息对时表现出不一致行为
- 场景中模型的内部状态机难以区分工具调用和完成状态

## 何时不使用

避免使用 `HybridReActAgentStrategy` 当：

- 使用标准LLM提供商（OpenAI、Anthropic等）- 改用 [ReActAgentStrategy](ReActAgentStrategy.md)
- 安全是主要关注点且无法实现适当的输入验证
- 需要严格的OpenAI兼容消息格式
