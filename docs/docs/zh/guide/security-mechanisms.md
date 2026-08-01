<div v-pre />

# 安全机制

## Cookie 安全检测

### 提示注入保护

AmritaCore 通过其 cookie 安全检测机制实现了健壮的提示注入保护。该功能向对话中添加一个唯一的 "cookie"，帮助检测攻击者是否试图通过注入恶意指令来操纵 AI 的行为。

cookie 系统通过向对话上下文中插入一个在会话期间保持一致的唯一标识符来工作。如果此 cookie 在 AI 响应的意外位置被检测到，则表明存在潜在的提示注入攻击。

### CookieConfig 配置

[CookieConfig](../api-reference/classes/CookieConfig.md) 类管理 cookie 相关的安全设置。Cookie 安全**默认启用**（`enable_cookie=True`）——除非你想自定义 cookie 字符串，否则无需显式配置：

```python
from amrita_core.config import CookieConfig

# Cookie 安全默认开启。以下示例展示如何更改 cookie。
security_config = CookieConfig(
    enable_cookie=True,              # 已是默认值，仅为清晰起见展示
    cookie="custom_cookie_string"    # 自定义 cookie 字符串（默认为随机字符串）
)

# 或让系统自动生成随机 cookie（这是默认行为）
default_security_config = CookieConfig(enable_cookie=True)
```

### 安全检测示例

```python
from amrita_core.config import AmritaConfig, CookieConfig
from amrita_core import ChatObject
from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.backends import LegacyBackend

# 设置安全配置
security_config = AmritaConfig(
    cookie=CookieConfig(enable_cookie=True)
)

from amrita_core.config import set_config
set_config(security_config)

# cookie 安全将自动应用于对话
chat = ChatObject(
    train={"role": "system", "content": "你是一个乐于助人的助手。"},
    user_input="你好！",
    context=None,
    session_id="secure_session",
    backend=BackendSlots(ability=LegacyBackend(), memory=LegacyBackend()),
)
```

## 内容过滤

### 内容过滤机制

AmritaCore 提供了灵活的内容过滤机制，可根据特定安全需求自定义。框架默认不包含内置的内容过滤器，但提供了实现自定义过滤的钩子：

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

@on_precompletion().handle()
async def content_filter(event: PreCompletionEvent):
    """在处理前过滤潜在不安全的内容"""
    for msg in event.messages:
        if msg.role == "user":
            if contains_harmful_content(msg.content):
                msg.content = "[内容因安全原因被过滤]"

def contains_harmful_content(content: str) -> bool:
    """检测有害内容的示例函数"""
    harmful_keywords = [
        "jailbreak", "ignore instructions", "prompt injection",
        "system prompt", "role play as", "never say"
    ]
    content_lower = content.lower()
    return any(keyword in content_lower for keyword in harmful_keywords)
```

### 敏感信息检测

实现敏感信息检测以防止数据泄露：

```python
import re

def detect_sensitive_information(text: str):
    """检测文本中各种类型的敏感信息"""
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

## 模板安全增强

### Jinja2 模板转义

AmritaCore 自动对 Jinja2 模板中的用户提供内容应用 HTML 转义，以**防止用户输入破坏系统消息的结构化格式**。

```jinja2
{% if original_msg %}
<INPUT>
{{original_msg|escape}}  {# 此处自动应用转义 #}
</INPUT>
{% endif %}
```

### 适配器类型安全验证

AmritaCore 内置了对适配器使用的类型安全验证，防止适配器被意外误用：

```python
from amrita_core.libchat import call_completion

# 如果适配器不支持 "text-gen"，将引发 RuntimeError
response = await call_completion(preset=text_gen_preset, messages=["你好"])
```

### 安全模板使用最佳实践

1. **使用内置转义**：依赖 AmritaCore 对用户提供内容的自动转义
2. **验证模板变量**：确保自定义模板变量不包含可执行代码
3. **避免原始 HTML**：除非完全控制内容，否则绝不要使用 `|safe` 过滤器
4. **使用恶意输入测试**：始终用潜在的恶意输入测试模板，以验证转义是否正常工作

```python
from jinja2 import Template

# 安全模板——用户内容将被转义
safe_template = Template("""
系统：{{ role_instructions }}
用户输入：{{ user_input|escape }}
上下文：{{ context_summary|escape }}
""")
```

**模板变量命名安全**：
如 [Jinja2 模板变量安全](../extensions-integration/jinja2-templates.md#模板变量命名安全) 部分所述，避免使用与内置参数（`train`、`memory`、`chatobj`、`config`）冲突的变量名，以防止因重复关键字参数导致的 `TypeError`。

### 综合安全架构

AmritaCore 的安全增强功能共同提供纵深防御：

| 安全层         | 提供的保护         | 支持 |
| -------------- | ------------------ | ---- |
| Cookie 检测    | 提示注入检测       | 是   |
| 模板转义       | 提示中的 XSS 预防  | 是   |
| 适配器类型验证 | 防止适配器误用     | 是   |
| 会话隔离       | 防止跨会话数据泄露 | 是   |

这些层次确保 AmritaCore 应用程序在保持易用性和开发者生产力的同时，能够抵御常见的攻击向量。

## 会话隔离

会话隔离由[数据后端](./concepts/data-backend.md)机制处理。每个 `ChatObject` 接收一个 `BackendSlots` 实例，该实例控制每个会话的记忆和能力如何加载和持久化。

### 后端驱动的隔离

默认的 `LegacyBackend` 将所有会话数据存储在进程内全局容器中。对于更强的隔离，实现自定义后端：

```python
from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.backends import LegacyBackend

# 默认：全局容器（所有会话共享工具/预设）
backend = BackendSlots(ability=LegacyBackend(), memory=LegacyBackend())
```

### 会话 ID 管理

每个会话由唯一的 `session_id` 字符串标识。后端使用此 ID 来查找或创建每个会话的状态：

```python
import uuid
from amrita_core.types import MemoryModel

def create_session_id() -> str:
    """生成唯一的会话标识符。"""
    return uuid.uuid4().hex
```

### 数据隔离示例

通过使用严格分离每个会话记忆的自定义后端来确保数据隔离：

```python
from amrita_core import ChatObject
from amrita_core.base.backend import BackendSlots, MemoryBackend
from amrita_core.builtins.backends import LegacyBackend
from amrita_core.types import MemoryModel

class IsolatedMemoryBackend(MemoryBackend):
    """由 dict 支持的每个会话的记忆。"""
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
            train={"role": "system", "content": "你是一个有帮助的助手。"},
            user_input=user_input,
            context=None,
            session_id=session_id,
            backend=self._slot,
        )
        async with chat.begin():
            response = await chat.full_response()
            await chat  # 等待任务完成再退出
        return response
```

### 跨会话保护

防止跨会话污染：

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

@on_precompletion().handle()
async def session_isolation_check(event: PreCompletionEvent, session_id: str = None):
    """确保会话特定数据不会跨会话泄露"""
    if session_id:
        for msg in event.messages:
            if session_id in msg.content and msg.role != "system":
                print(f"警告：会话 ID 出现在非系统消息中：{msg.content}")
```

## 访问控制

### 权限机制

虽然 AmritaCore 本身不实现全面的权限系统，但它提供了钩子来集成外部访问控制机制：

```python
from typing import Dict, List
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

class AccessControlManager:
    def __init__(self):
        self.user_permissions: Dict[str, List[str]] = {}

    def has_permission(self, user_id: str, permission: str) -> bool:
        """检查用户是否具有特定权限"""
        user_perms = self.user_permissions.get(user_id, [])
        return permission in user_perms

    def add_permission(self, user_id: str, permission: str):
        """向用户授予权限"""
        if user_id not in self.user_permissions:
            self.user_permissions[user_id] = []
        if permission not in self.user_permissions[user_id]:
            self.user_permissions[user_id].append(permission)

access_manager = AccessControlManager()

@on_precompletion().handle()
async def check_access_control(event: PreCompletionEvent, user_id: str = None):
    """处理前检查访问权限"""
    if user_id:
        if not access_manager.has_permission(user_id, "advanced_tools"):
            event.messages = filter_advanced_tools(event.messages)

def filter_advanced_tools(messages):
    """如果用户没有权限，移除或修改请求高级工具的消息"""
    return messages
```

### 访问限制

实施速率限制和访问约束：

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

# 在 API 端点中使用
def handle_request(user_id: str):
    if not rate_limiter.is_allowed(user_id):
        raise Exception("超过速率限制")
    pass
```

### 审计日志

实现审计日志以跟踪与安全相关的事件：

```python
from amrita_core.logging import logger
from amrita_core.hook.event import PreCompletionEvent, CompletionEvent
from amrita_core.hook.on import on_precompletion, on_completion

@on_precompletion().handle()
async def log_request(event: PreCompletionEvent, user_id: str = None):
    """记录传入请求以供审计"""
    user_identifier = user_id or "anonymous"
    logger.info(f"来自用户 {user_identifier} 的请求：{len(event.messages)} 条消息")
    for msg in event.messages:
        if msg.role == "user":
            logger.debug(f"用户 {user_identifier} 说：{msg.content[:100]}...")

@on_completion().handle()
async def log_response(event: CompletionEvent, user_id: str = None):
    """记录响应以供审计"""
    user_identifier = user_id or "anonymous"
    logger.info(f"对用户 {user_identifier} 的响应：{len(event.response)} 个字符")
    logger.debug(f"对 {user_identifier} 的响应：{event.response[:100]}...")
```
