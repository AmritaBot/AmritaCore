<div v-pre >

# 安全机制

## 6.1 Cookie 安全检测

### 6.1.1 提示词注入防护

AmritaCore 通过其 Cookie 安全检测机制实现了提示词注入防护。此功能在对话中添加了一个独特的"cookie"，有助于检测攻击者是否试图通过注入恶意指令来操控 AI 的行为。

Cookie 系统通过在对话上下文中插入一个唯一标识符来工作，该标识符在整个会话期间保持一致。如果在 AI 回复的意外位置检测到此 Cookie，则表明可能存在提示词注入攻击。

### 6.1.2 CookieConfig 配置

[CookieConfig](../api-reference/classes/CookieConfig.md) 类管理 Cookie 相关的安全设置：

```python
from amrita_core.config import CookieConfig

# 启用 Cookie 安全检测
security_config = CookieConfig(
    enable_cookie=True,              # 启用 Cookie 泄漏检测机制
    cookie="custom_cookie_string"    # 自定义 Cookie 字符串（默认为随机字符串）
)

# 或让系统自动生成随机 Cookie
default_security_config = CookieConfig(enable_cookie=True)
```

如果未显式提供 Cookie，它将自动生成为随机字母数字字符串，确保跨会话的唯一性。

### 6.1.3 安全检测示例

下面是如何实现和使用 Cookie 安全检测：

```python
from amrita_core.config import AmritaConfig, CookieConfig, set_config
from amrita_core import ChatObject
from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.backends import LegacyBackend

# Cookie 安全默认启用，无需显式初始化

# 设置安全配置
security_config = AmritaConfig(
    cookie=CookieConfig(enable_cookie=True)
)
set_config(security_config)

# Cookie 安全将自动应用于对话
chat = ChatObject(
)
```

## 6.2 模板安全增强

### 6.2.1 Jinja2模板转义

AmritaCore自动对Jinja2模板中的用户提供的内容应用HTML转义，以**防止用户输入破坏系统消息的结构化格式**。

**增强的模板安全性**：

```jinja2
{% if original_msg %}
<INPUT>
{{original_msg|escape}}  {# 自动应用转义 #}
</INPUT>
{% endif %}
```

现在 `|escape` 过滤器会自动应用于系统消息模板中的 `original_msg` 变量，确保任何包含特殊字符（如 `<`、`>`、`{`、`}` 等）的用户输入在包含到提示中之前都被正确转义。这可以防止：

- **模板结构损坏**：包含花括号 `{{}}` 或其他Jinja2语法的用户输入不会干扰模板渲染
- **XML/HTML结构破坏**：特殊字符如 `<` 和 `>` 不会破坏系统消息中使用的类XML结构
- **意外的模板执行**：防止用户提供的内容被解释为模板代码

**安全影响**：

- 维护系统消息结构的完整性
- 当用户输入包含模板语法时，防止模板注入
- 确保无论用户输入内容如何，都能保持可预测的提示格式
- 向后兼容 - 现有模板继续按预期工作

### 6.2.2 适配器类型安全验证

AmritaCore现在包含内置的适配器使用类型安全验证，以防止意外误用适配器。

**自动类型验证**：

```python
from amrita_core.libchat import call_completion

# 如果适配器不支持 "text-gen"，这将引发 RuntimeError
response = await call_completion(preset=text_gen_preset, messages=["Hello"])

# 嵌入适配器被验证仅用于嵌入调用
embeddings = await call_completion(preset=embedding_preset, messages=["Hello"])
```

**验证逻辑**：

- 当使用 `call_completion()` 进行文本生成时，系统验证适配器是否支持 `"text-gen"` 类型
- 如果嵌入专用适配器用于文本生成，则会抛出带有清晰错误消息的 `RuntimeError`
- 这可以防止静默失败和适配器误用时的混淆行为

**示例错误消息**：

```shell
RuntimeError: Invalid adapter type for text-gen when using adapter: MyEmbeddingAdapter, this adapter only supports embed.
```

### 6.2.3 安全模板使用的最佳实践

在AmritaCore中使用自定义Jinja2模板时，请遵循以下安全最佳实践：

1. **使用内置转义**：依赖AmritaCore对用户提供的内容进行自动转义
2. **验证模板变量**：确保自定义模板变量不包含可执行代码
3. **避免原始HTML**：除非完全控制内容，否则不要使用 `|safe` 过滤器
4. **使用恶意输入测试**：始终使用潜在的恶意输入测试模板，以验证转义是否正常工作

**安全的自定义模板示例**：

```python
from jinja2 import Template

# 安全模板 - 用户内容将被转义
safe_template = Template("""
SYSTEM: {{ role_instructions }}
USER INPUT: {{ user_input|escape }}
CONTEXT: {{ context_summary|escape }}
""")

# 可放心使用 - 转义已自动处理
rendered = safe_template.render(
    role_instructions="You are a helpful assistant",
    user_input="<script>alert('xss')</script>",  # 将被转义
    context_summary="Previous conversation context"
)
```

**模板变量命名安全**：
如 [Jinja2模板变量安全](../extensions-integration/jinja2-templates.md#template-variable-naming-safety) 部分所述，避免使用与内置参数（`train`、`memory`、`chatobj`、`config`）冲突的变量名，以防止由于重复关键字参数导致的 `TypeError`。

### 6.2.4 综合安全架构

AmritaCore的安全增强功能协同工作，提供纵深防御：

| 安全层         | 提供的保护         | 是否支持 |
| -------------- | ------------------ | -------- |
| Cookie检测     | 提示注入检测       | 是       |
| 模板转义       | 提示中的XSS防护    | 是       |
| 适配器类型验证 | 防止适配器误用     | 是       |
| 会话隔离       | 防止跨会话数据泄露 | 是       |

这些层确保AmritaCore应用程序在保持易用性和开发人员生产力的同时，能够抵御常见攻击向量。

## 6.3 内容过滤

### 6.3.1 内容过滤机制

AmritaCore 提供了一个灵活的内容过滤机制，可以根据特定安全要求进行自定义。框架默认不包含内置内容过滤器，但提供了实现自定义过滤的钩子：

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

@on_precompletion().handle()
async def content_filter(event: PreCompletionEvent):
    """
    处理前过滤潜在不安全内容
    """
    # 检查用户消息中的潜在有害内容
    for msg in event.messages:
        if msg.role == "user":
            # 在此处实现您的内容过滤逻辑
            if contains_harmful_content(msg.content):
                # 替换为更安全的消息或添加警告
                msg.content = "[出于安全考虑已过滤内容]"



def contains_harmful_content(content: str) -> bool:
    """
    检测有害内容的示例函数
    这是一个简化的示例 - 实际实现会更复杂
    """
    有害关键词 = [
        "越狱", "忽略指令", "提示词注入",
        "系统提示", "角色扮演", "永远不要说"
    ]

    content_lower = content.lower()
    return any(keyword in content_lower for keyword in 有害关键词)
```

### 6.3.2 自定义过滤规则

根据您的特定要求实现自定义过滤规则：

```python
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.on import on_completion

@on_completion().handle()
async def response_filter(event: CompletionEvent):
    """
    过滤 AI 回复中的敏感信息
    """
    # 检查回复中是否包含潜在敏感信息
    if contains_sensitive_info(event.response):
        # 记录事件并在必要时修改回复
        print(f"回复中检测到潜在敏感信息: {event.response[:100]}...")
        # 可选择修改回复
        # event.response = "[出于安全考虑已修改回复]"



def contains_sensitive_info(content: str) -> bool:
    """
    检测回复是否包含敏感信息
    """
    # 示例：检查明显的内部系统信息
    sensitive_patterns = [
        "system:", "internal:", "admin:", "password:", "secret:"
    ]

    content_lower = content.lower()
    return any(pattern in content_lower for pattern in sensitive_patterns)
```

### 6.3.3 敏感信息检测

实现敏感信息检测以防止数据泄露：

```python
import re

def detect_sensitive_information(text: str):
    """
    检测文本中的各种敏感信息
    """
    patterns = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"
    }

    found_items = {}
    for item_type, pattern in patterns.items():
        matches = re.findall(pattern, text)
        if matches:
            found_items[item_type] = matches

    return found_items
```

## 6.4 会话隔离

会话隔离由[数据后端](../guide/concepts/data-backend.md)机制处理。每个 `ChatObject` 接收一个 `BackendSlots` 实例，控制每个会话的记忆和能力的加载与持久化方式。

### 6.4.1 后端驱动的隔离

默认的 `LegacyBackend` 将所有会话数据存储在进程内全局容器中。如需更强的隔离，可实现自定义后端：

```python
from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.backends import LegacyBackend

# 默认：全局容器（所有会话共享工具/预设）
backend = BackendSlots(ability=LegacyBackend(), memory=LegacyBackend())
```

### 6.4.2 会话ID管理

每个会话由唯一的 `session_id` 字符串标识。后端使用此 ID 查找或创建每个会话的状态：

```python
import uuid
def create_session_id() -> str:
    """生成唯一会话标识符。"""
    return uuid.uuid4().hex
```

### 6.4.3 数据隔离示例

使用严格分离每个会话记忆的自定义后端确保数据隔离：

```python
from amrita_core import ChatObject
from amrita_core.base.backend import BackendSlots, MemoryBackend
from amrita_core.builtins.backends import LegacyBackend
from amrita_core.types import MemoryModel

class IsolatedMemoryBackend(MemoryBackend):
    """基于字典的每个会话记忆。"""
    def __init__(self):
        self._store: dict[str, MemoryModel] = {}

    async def load_memory(self, session_id: str) -> MemoryModel:
        return self._store.get(session_id, MemoryModel())

    async def commit_memory(self, session_id: str, memory: MemoryModel) -> None:
        self._store[session_id] = memory

class SecureConversationManager:
    def __init__(self):
        self._mem = IsolatedMemoryBackend()
        self._slot = BackendSlots(
            ability=LegacyBackend(),
            memory=self._mem,
        )

    async def process_user_input(self, session_id: str, user_input: str):
        chat = ChatObject(
            train={"role": "system", "content": "您是一个有用的助手。"},
            user_input=user_input,
            context=None,
            session_id=session_id,
            backend=self._slot,
        )
        async with chat.begin():
            return await chat.full_response()
```

## 6.5 访问控制

### 6.5.1 权限机制

虽然 AmritaCore 本身没有实现完整的权限系统，但它提供了与外部访问控制机制集成的钩子：

```python
from typing import Dict, List
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

class AccessControlManager:
    def __init__(self):
        self.user_permissions: Dict[str, List[str]] = {}

    def has_permission(self, user_id: str, permission: str) -> bool:
        """
        检查用户是否具有特定权限
        """
        user_perms = self.user_permissions.get(user_id, [])
        return permission in user_perms

    def add_permission(self, user_id: str, permission: str):
        """
        向用户授予权限
        """
        if user_id not in self.user_permissions:
            self.user_permissions[user_id] = []
        if permission not in self.user_permissions[user_id]:
            self.user_permissions[user_id].append(permission)

access_manager = AccessControlManager()

@on_precompletion().handle()
async def check_access_control(event: PreCompletionEvent, user_id: str = None):
    """
    处理前检查访问权限
    """
    if user_id:
        # 示例：检查用户是否可以访问高级工具
        if not access_manager.has_permission(user_id, "advanced_tools"):
            # 过滤掉高级工具使用
            event.messages = filter_advanced_tools(event.messages)



def filter_advanced_tools(messages):
    """
    如果用户没有权限，则移除或修改请求高级工具的消息
    """
    # 实现将取决于您特定的工具访问要求
    return messages
```

### 6.5.2 访问限制

实现速率限制和访问约束：

```python
from datetime import datetime, timedelta
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)

    def is_allowed(self, user_id: str) -> bool:
        now = datetime.now()
        # 清理旧请求
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if now - req_time < timedelta(seconds=self.time_window)
        ]

        if len(self.requests[user_id]) >= self.max_requests:
            return False

        self.requests[user_id].append(now)
        return True

rate_limiter = RateLimiter(max_requests=5, time_window=60)

# 在您的 API 端点中使用
def handle_request(user_id: str):
    if not rate_limiter.is_allowed(user_id):
        raise Exception("超过速率限制")

    # 处理请求
    pass
```

### 6.5.3 审计日志

实现审计日志以跟踪与安全相关的事件：

```python
from amrita_core.logging import logger
from amrita_core.hook.event import PreCompletionEvent, CompletionEvent
from amrita_core.hook.on import on_precompletion, on_completion

@on_precompletion().handle()
async def log_request(event: PreCompletionEvent, user_id: str = None):
    """
    为审计目的记录传入请求
    """
    user_identifier = user_id or "anonymous"

    logger.info(f"来自用户 {user_identifier} 的请求: {len(event.messages)} 条消息")

    # 特别记录用户消息
    for msg in event.messages:
        if msg.role == "user":
            logger.debug(f"用户 {user_identifier} 说: {msg.content[:100]}...")



@on_completion().handle()
async def log_response(event: CompletionEvent, user_id: str = None):
    """
    为审计目的记录回复
    """
    user_identifier = user_id or "anonymous"

    logger.info(f"回复给用户 {user_identifier}: {len(event.response)} 个字符")
    logger.debug(f"回复给 {user_identifier}: {event.response[:100]}...")


```

</div>
