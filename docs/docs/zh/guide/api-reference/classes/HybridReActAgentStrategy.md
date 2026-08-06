# HybridReActAgentStrategy

> **已弃用**：计划在 **v0.14.0** 移除。推荐使用 [ReActAgentStrategy](ReActAgentStrategy.md)。
>
> **v0.13 维护性修复**：
> - 推理内容存入 `Message.reasoning_content`（不再作为普通文本），thinking 模式（DeepSeek）下正确回传，不再 HTTP 400；
> - 工具结果以 **ToolCall-ToolResult 配对**追加（XML 渲染文本保留在 ToolResult 内容中），满足 OpenAI 兼容 API 的配对要求。

`HybridReActAgentStrategy` 是**针对混合专家（MoE）架构模型优化**的专用 agent 策略。

## 继承

- 继承自：[BaseReActAgentStrategy](BaseReActAgentStrategy.md)
- 类别：`"agent-mixed"`

## 关键特性

- **ToolCall 触发**：通过标准 ToolCall 机制启动工具执行
- **基于上下文的集成**：将工具结果作为纯文本消息追加，而非结构化的 ToolResult 对象
- **XML 标签格式**：使用 `<TOOL_CALL>` 和 `<TOOL_RESULT>` XML 标签表示工具交互
- **MoE 专用优化**：解决 MoE 模型难以区分工具调用状态和完成状态的问题

## 工具函数模式

```xml
<TOOL_CALL name="tool">
    <PARAMS>
        <PARAM name="param1">value1</PARAM>
    </PARAMS>
</TOOL_CALL>

<TOOL_RESULT name="tool">
   工具执行结果内容
</TOOL_RESULT>
```

## ⚠️ 安全注意事项

- **提示注入风险**：将工具结果作为纯文本 `user` 消息追加，如果工具输出不可信或未经消毒，可能使模型暴露于注入攻击
- **最小消毒**：此策略仅提供基本的标签对转义，**不执行**语义级别过滤或内容验证
- **安全责任**：用户**必须**在生产环境中对工具结果实施全面的输入验证、语义分析和内容消毒
