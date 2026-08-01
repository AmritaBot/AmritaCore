# Jinja2 模板

<div v-pre>

## 概述

AmritaCore 使用 [Jinja2](https://jinja.palletsprojects.com/) 模板来根据对话上下文、记忆状态和配置实现动态提示词构建。这一强大功能允许你创建灵活且具有上下文感知能力的系统提示词，适应当前对话状态。

## 模板变量

在 AmritaCore 中渲染 Jinja2 模板时，以下变量可用：

### 内置变量

#### `train`

- **类型**：`Message[str]`
- **描述**：包含 AI 助手基本指令的系统消息（训练数据）。
- **用法**：`{{ train.content }}` 访问系统提示内容。

#### `memory`

- **类型**：`MemoryModel`
- **描述**：包含消息历史和上下文摘要的对话记忆。
- **关键属性**：
  - `memory.messages`：对话消息列表
  - `memory.abstract`：上下文摘要（启用记忆摘要时）

#### `chatobj`

- **类型**：`ChatObject`
- **描述**：包含会话和交互细节的当前聊天处理对象。
- **关键属性**：
  - `chatobj.session_id`：当前会话标识符
  - `chatobj.stream_id`：唯一的流标识符
  - `chatobj.timestamp`：当前交互的时间戳
  - `chatobj.user_input`：当前用户输入

#### `config`

- **类型**：`AmritaConfig`
- **描述**：控制系统行为的配置对象。
- **关键属性**：
  - `config.cookie.enable`：是否启用 cookie 安全
  - `config.llm.enable_memory_abstract`：是否启用记忆摘要

### 通过 `jinja2_vars` 传递自定义变量

除了内置变量外，你可以在创建 `ChatObject` 时通过 `jinja2_vars` 参数向模板传递自定义变量。

**关键限制**：在模板渲染期间，`jinja2_vars` 字典被**直接解包**使用 `**self.jinja2_vars`。这意味着：

1. **直接变量访问**：`jinja2_vars` 字典中的键可以直接作为模板变量访问
   - 示例：`jinja2_vars={"role": "expert", "company": "Amrita"}` 使 `{{ role }}` 和 `{{ company }}` 在模板中可用

2. **不能覆盖变量**：**不能在 `jinja2_vars` 中使用与内置变量名**（`train`、`memory`、`chatobj` 或 `config`）匹配的键。尝试这样做将导致 `TypeError`。

3. **保留关键字**：键 `'self'` 被保留，不能在 `jinja2_vars` 中使用

## 默认模板

AmritaCore 提供了一个展示常见用法的默认模板：

```text
<SCHEMA>
{% if config.cookie.enable %}
<HIDDEN>{{ config.cookie.cookie }}</HIDDEN>
{% endif %}
请以你自己的角色身份参与讨论。在回答不同话题时尽量不要使用相似短语。用户的消息包含在用户输入中。
你的角色设定在 <SYSTEM_INSTRUCTIONS> 标签中，之前对话的摘要在 <SUMMARY> 标签中（如果提供）。
</SCHEMA>

<SYSTEM_INSTRUCTIONS>
{{ train.content }}
</SYSTEM_INSTRUCTIONS>
{% if memory.abstract and config.llm.enable_memory_abstract %}
<SUMMARY>
{{ memory.abstract }}
</SUMMARY>
{% endif %}
```

## 自定义模板

你可以在创建 `ChatObject` 时提供自定义 Jinja2 模板：

```python
from jinja2 import Template
from amrita_core.chatmanager import ChatObject

# 定义自定义模板
custom_template = Template("""
# 系统角色
你是 {{ role_name | default('一个乐于助人的助手') }}。

# 当前上下文
会话 ID：{{ chatobj.session_id }}
时间戳：{{ chatobj.timestamp }}

# 指令
{{ train.content }}

# 对话历史摘要
{% if memory.abstract %}
之前的对话：{{ memory.abstract }}
{% endif %}

# 当前任务
请基于上述上下文和指令处理用户的请求。
""")

chat = ChatObject(
    train=Message(role="system", content="基础指令"),
    user_input="你好！",
    session_id="session_123",
    train_template=custom_template,
    jinja2_vars={"role_name": "专业的代码审查者"}
)
```

> **重要**：`train_template` 必须是 `jinja2.Template` 对象，而非纯字符串。使用 `Template(your_string)` 构建。

## 模板渲染过程

模板渲染发生在 `ChatObject` 的 `_run()` 方法期间：

1. 用户消息被添加到记忆中
2. 模板以异步方式渲染，结合所有变量：
   - 内置变量：`train`、`memory`、`chatobj`、`config`
   - 来自 `jinja2_vars` 的自定义变量（直接解包）
3. **不可覆盖**：由于 Python 禁止重复关键字参数，`jinja2_vars` 不能包含与内置变量名匹配的键
4. 渲染后的内容成为新的系统消息内容
5. 应用记忆限制
6. 消息被发送到 LLM

```python
# 内部渲染代码（仅供参考）
self.train.content = await asyncio.to_thread(
    self.template.render,
    train=self.train,
    memory=self.data,
    chatobj=self,
    config=config,
    **self.jinja2_vars,
)
```

## 最佳实践

### 安全考虑

- 始终验证模板输入以防止注入攻击
- 在适当的情况下使用 Jinja2 的内置转义机制
- 谨慎处理用户提供的模板变量
- 避免在 `jinja2_vars` 中使用保留关键字 `'self'`
- **绝不使用内置变量名**（`train`、`memory`、`chatobj`、`config`）作为 `jinja2_vars` 中的键

### 性能优化

- 保持模板简单，避免复杂逻辑
- 谨慎使用条件语句（`{% if %}`）
- 尽可能缓存常用模板

### 上下文管理

- 对长对话使用 `memory.abstract`
- 使用 `config` 变量动态控制模板行为
- 在需要上下文时包含相关会话信息
- 通过 `jinja2_vars` 传递业务特定数据进行动态定制
- **使用唯一的键名**：始终选择与内置变量不冲突的自定义变量名

### 错误处理

- 优雅地处理模板渲染错误
- 为缺失的变量提供回退内容
- 使用各种输入场景测试模板
- **避免命名冲突**：确保你的自定义变量名与内置变量不同

## 高级用法示例

### 直接变量访问

```text
# 直接使用自定义变量
你好！我是 {{ assistant_name }}，来自 {{ company_name }}。
我的专长是 {{ expertise_area }}。

{{ train.content }}
```

```python
chat = ChatObject(
    train={"content": "你是一个 AI 助手。", "role": "system"},
    user_input="介绍一下你自己",
    context=None,
    session_id="session_123",
    jinja2_vars={
        "assistant_name": "Amrita 助手",
        "company_name": "Amrita Corp",
        "expertise_area": "AI 和自动化"
    }
)
```

### 安全的自定义变量（推荐方式）

```text
# 使用带前缀的自定义变量以避免冲突
{{ train.content }}

# 业务上下文
公司：{{ business_context_company_name }}
部门：{{ business_context_department }}

# 用户上下文
用户角色：{{ user_context_role }}
首选语言：{{ user_context_language }}
```

```python
# 使用唯一的键名避免任何冲突
chat = ChatObject(
    train={"content": "适当地帮助用户。", "role": "system"},
    user_input="帮我完成这个任务",
    context=None,
    session_id="session_123",
    jinja2_vars={
        "business_context_company_name": "Amrita Corp",
        "business_context_department": "工程部",
        "user_context_role": "开发者",
        "user_context_language": "zh"
    }
)
```

### 嵌套结构替代方案

```text
# 在模板逻辑中使用嵌套结构
{{ train.content }}

# 业务上下文
公司：{{ get_business_info('company_name') }}
部门：{{ get_business_info('department') }}
```

```python
# 传递一个具有唯一名称的函数或对象
def get_business_info(key):
    business_data = {
        "company_name": "Amrita Corp",
        "department": "工程部"
    }
    return business_data.get(key, "")

chat = ChatObject(
    train={"content": "协助内部查询。", "role": "system"},
    user_input="我们的远程办公政策是什么？",
    context=None,
    session_id="session_123",
    jinja2_vars={"get_business_info": get_business_info}
)
```

### 使用自定义变量实现多语言支持

```text
{% if language == 'zh' %}
你是一个{{ role }}。
{{ train.content }}
{% else %}
You are a {{ role }}.
{{ train.content }}
{% endif %}
```

```python
# 通过 jinja2_vars 传递语言和角色
chat = ChatObject(
    train={"content": "你是一个 AI 助手。", "role": "system"},
    user_input="你好！",
    context=None,
    session_id="session_123",
    jinja2_vars={"language": "zh", "role": "AI专家"}
)
```

### 业务上下文集成

```text
# 公司上下文
公司：{{ company_name }}
部门：{{ department }}
当前项目：{{ project_name }}

# 指令
{{ train.content }}

# 回复指南
始终引用公司政策并保持适合 {{ department }} 的专业语气。
```

```python
# 通过 jinja2_vars 传递业务上下文
chat = ChatObject(
    train={"content": "协助内部查询。", "role": "system"},
    user_input="我们的远程办公政策是什么？",
    context=None,
    session_id="session_123",
    jinja2_vars={
        "company_name": "Amrita Corp",
        "department": "工程部",
        "project_name": "AmritaCore v2.0"
    }
)
```

AmritaCore 中的 Jinja2 模板提供了一种强大的方式来创建动态、上下文感知的提示，增强 AI 助手的能力，同时保持灵活性和安全性。`jinja2_vars` 参数可以将自定义业务逻辑和上下文数据无缝集成到提示模板中，但需要注意自定义变量名不能与内置变量冲突。

</div>
