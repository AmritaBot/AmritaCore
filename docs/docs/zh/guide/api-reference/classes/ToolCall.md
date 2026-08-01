# ToolCall

ToolCall 类表示工具的一次调用。

## 属性

- `id` (str)：工具调用的 ID
- `function` (Function)：模型调用的函数
- `type` (Literal["function"])：工具类型，目前仅支持 "function"

## 描述

ToolCall 类继承自 BaseModel，用于表示 AI 模型发起的工具调用。当 AI 模型确定需要调用某个工具时，会生成一个 ToolCall 对象，包含要调用的函数和参数信息。

ToolCall 是 AmritaCore 工具调用系统的关键组件，使 AI 模型能够与外部工具和服务交互。
