# ToolResult

ToolResult 类表示工具调用的结果。

## 属性

- `role` (Literal["tool"])：角色，固定为 "tool"
- `name` (str)：工具名
- `content` (str)：工具返回的内容
- `tool_call_id` (str)：工具调用 ID

## 描述

ToolResult 类继承自 BaseModel，用于表示工具调用的结果。当工具完成执行后，其结果被封装为 ToolResult 对象，供对话流使用。
