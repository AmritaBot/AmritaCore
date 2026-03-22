# Jinja2 模板

## 概述

AmritaCore 使用 [Jinja2](https://jinja.palletsprojects.com/) 模板来实现基于对话上下文、记忆状态和配置的动态提示构建。这一强大功能允许您创建灵活且具有上下文感知能力的系统提示，这些提示能够适应当前对话状态。

## 模板变量

在 AmritaCore 中渲染 Jinja2 模板时，以下变量可用：

### 内置变量

#### `train`

- **类型**: `Message[str]`
- **描述**: 系统消息（训练数据），包含 AI 助手的基础指令。
- **用法**: `{{ train.content }}` 访问系统提示内容。

#### `memory`

- **类型**: `MemoryModel`
- **描述**: 包含消息历史和上下文摘要的对话记忆。
- **关键属性**:
  - `memory.messages`: 对话消息列表
  - `memory.abstract`: 上下文摘要（启用记忆抽象时）

#### `chatobj`

- **类型**: `ChatObject`
- **描述**: 当前聊天处理对象，包含会话和交互详细信息。
- **关键属性**:
  - `chatobj.session_id`: 当前会话标识符
  - `chatobj.stream_id`: 唯一流标识符
  - `chatobj.timestamp`: 当前交互的时间戳
  - `chatobj.user_input`: 当前用户输入

#### `config`

- **类型**: `AmritaConfig`
- **描述**: 控制系统行为的配置对象。
- **关键属性**:
  - `config.cookie.enable`: 是否启用 Cookie 安全
  - `config.cookie.cookie`: Cookie 值（启用时）
  - `config.llm.enable_memory_abstract`: 是否启用记忆抽象
  - 各种其他 LLM 和系统配置选项

### 通过 `jinja2_vars` 的自定义变量

除了内置变量外，您还可以在创建 `ChatObject` 时使用 `jinja2_vars` 参数向模板传递自定义变量。

**关键限制**：`jinja2_vars` 字典在模板渲染期间**直接解包**（使用 `**self.jinja2_vars`）。这意味着：

1. **直接变量访问**：`jinja2_vars` 字典中的键可以直接作为模板变量访问
   - 示例：`jinja2_vars={"role": "expert", "company": "Amrita"}` 使得 `{{ role }}` 和 `{{ company }}` 在模板中可用

2. **无变量覆盖**：**您不能在 `jinja2_vars` 中使用与内置变量名**（`train`、`memory`、`chatobj` 或 `config`）。尝试这样做会导致 `TypeError`，因为 Python 不允许在函数调用中使用重复的关键字参数。

3. **保留关键字**：键 `'self'` 是保留关键字，不能在 `jinja2_vars` 中使用

- **参数**: `jinja2_vars` (dict[str, Any] | None)
- **描述**: 传递给模板系统的自定义变量字典
- **限制**: 键必须 NOT 与内置变量名（`train`、`memory`、`chatobj`、`config`）冲突

## 默认模板

AmritaCore 提供了一个默认模板，展示了常见的使用模式：

```text
<SCHEMA>
{% if config.cookie.enable %}
<HIDDEN>{{ config.cookie.cookie }}</HIDDEN>
{% endif %}
请以您自己的角色身份参与讨论。在回应不同话题时，尽量不要使用相似的短语。用户的消息包含在用户输入中。
您的角色设置在 <SYSTEM_INSTRUCTIONS> 标签中，之前对话的摘要在 <SUMMARY> 标签中（如果提供）。
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

此模板包括：

- 用于安全的条件性 Cookie 包含
- 来自训练消息的系统指令
- 启用记忆抽象时的上下文摘要

## 自定义模板

创建 `ChatObject` 时可以提供自定义 Jinja2 模板：

```python
from jinja2 import Template
from amrita_core.chatmanager import ChatObject

# 定义自定义模板
custom_template = Template("""
# 系统角色
您是 {{ role_name | default('一个乐于助人的助手') }}。

# 当前上下文
会话 ID: {{ chatobj.session_id }}
时间戳: {{ chatobj.timestamp }}

# 指令
{{ train.content }}

# 对话历史摘要
{% if memory.abstract %}
之前的对话: {{ memory.abstract }}
{% endif %}

# 当前任务
在保持您作为 {{ role_name | default('一个乐于助人的助手') }} 的角色的同时，处理用户的请求。
""")

# 使用带有 jinja2_vars 的自定义模板
chat = ChatObject(
    train={"content": "您是一位专业的 Python 开发者。", "role": "system"},
    user_input="如何在 AmritaCore 中使用 Jinja2 模板？",
    context=None,
    session_id="session_123",
    train_template=custom_template,
    jinja2_vars={"role_name": "Python 专家"}
)
```

## 模板渲染过程

模板渲染发生在 `ChatObject` 的 `_run()` 方法期间：

1. 用户消息被添加到记忆中
2. 模板使用所有变量异步渲染：
   - 内置变量：`train`、`memory`、`chatobj`、`config`
   - 来自 `jinja2_vars` 的自定义变量（直接解包）
3. **无法覆盖**：由于 Python 对重复关键字参数的限制，`jinja2_vars` 不能包含与内置变量名匹配的键
4. 渲染后的内容成为新的系统消息内容
5. 应用记忆限制
6. 将消息发送给 LLM

```python
# 内部渲染代码（仅供参考）
self.train.content = await self.template.render_async(
    train=self.train,
    memory=self.data,
    chatobj=self,
    config=config,
    **self.jinja2_vars,  # 直接解包 - 启用自定义变量但防止冲突
)
```

## 最佳实践

### 1. 安全考虑

- 始终验证模板输入以防止注入攻击
- 在适当时使用 Jinja2 的内置转义机制
- 对用户提供的模板变量要谨慎
- 避免在 `jinja2_vars` 中使用保留关键字 `'self'`
- **切勿使用内置变量名**（`train`、`memory`、`chatobj`、`config`）作为 `jinja2_vars` 中的键

### 2. 性能优化

- 保持模板简单，避免复杂逻辑
- 谨慎使用条件语句（`{% if %}`）
- 在可能的情况下缓存常用模板

### 3. 上下文管理

- 利用 `memory.abstract` 处理长对话
- 使用 `config` 变量动态控制模板行为
- 在需要上下文时包含相关的会话信息
- 通过 `jinja2_vars` 传递业务特定数据以实现动态自定义
- **使用唯一键名**：始终选择不与内置变量冲突的自定义变量名

### 4. 错误处理

- 优雅地处理模板渲染错误
- 为缺失的变量提供后备内容
- 使用各种输入场景测试模板
- **避免命名冲突**：确保您的自定义变量名与内置变量不同

## 高级使用示例

### 直接变量访问

```text
# 直接使用自定义变量
你好！我是 {{ assistant_name }}，来自 {{ company_name }}。
我的专长领域是 {{ expertise_area }}。

{{ train.content }}
```

```python
chat = ChatObject(
    train={"content": "You are an AI assistant.", "role": "system"},
    user_input="Tell me about yourself",
    context=None,
    session_id="session_123",
    jinja2_vars={
        "assistant_name": "Amrita Assistant",
        "company_name": "Amrita Corp",
        "expertise_area": "AI and automation"
    }
)
```

### 安全的自定义变量（推荐方法）

```text
# 使用前缀自定义变量以避免冲突
{{ train.content }}

# 业务上下文
公司: {{ business_context_company_name }}
部门: {{ business_context_department }}

# 用户上下文
用户角色: {{ user_context_role }}
首选语言: {{ user_context_language }}
```

```python
# 使用唯一键名以避免任何冲突
chat = ChatObject(
    train={"content": "Assist the user appropriately.", "role": "system"},
    user_input="Help me with this task",
    context=None,
    session_id="session_123",
    jinja2_vars={
        "business_context_company_name": "Amrita Corp",
        "business_context_department": "Engineering",
        "user_context_role": "developer",
        "user_context_language": "en"
    }
)
```

### 嵌套结构替代方案

```text
# 在模板逻辑中使用嵌套结构
{{ train.content }}

# 业务上下文
公司: {{ get_business_info('company_name') }}
部门: {{ get_business_info('department') }}
```

```python
# 传递具有唯一名称的单个函数或对象
def get_business_info(key):
    business_data = {
        "company_name": "Amrita Corp",
        "department": "Engineering"
    }
    return business_data.get(key, "")

chat = ChatObject(
    train={"content": "协助处理内部查询。", "role": "system"},
    user_input="我们关于远程工作的政策是什么？",
    context=None,
    session_id="session_123",
    jinja2_vars={"get_business_info": get_business_info}
)
```

### 使用自定义变量的多语言支持

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
    train={"content": "You are an AI assistant.", "role": "system"},
    user_input="Hello!",
    context=None,
    session_id="session_123",
    jinja2_vars={"language": "zh", "role": "AI专家"}
)
```

### 业务上下文集成

```text
# 公司上下文
公司: {{ company_name }}
部门: {{ department }}
当前项目: {{ project_name }}

# 指令
{{ train.content }}

# 响应指南
始终引用公司政策，并保持适合 {{ department }} 的专业语气。
```

```python
# 通过 jinja2_vars 传递业务上下文
chat = ChatObject(
    train={"content": "协助处理内部查询。", "role": "system"},
    user_input="我们关于远程工作的政策是什么？",
    context=None,
    session_id="session_123",
    jinja2_vars={
        "company_name": "Amrita Corp",
        "department": "工程部",
        "project_name": "AmritaCore v2.0"
    }
)
```

AmritaCore 中的 Jinja2 模板提供了一种强大的方式来创建动态的、具有上下文感知能力的提示，从而增强 AI 助手的功能，同时保持灵活性和安全性。`jinja2_vars` 参数实现了自定义业务逻辑和上下文数据与提示模板的无缝集成，同时具有重要的安全约束：自定义变量名不得与内置变量冲突。
