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
from amrita_core.config import AmritaConfig, CookieConfig
from amrita_core import init, ChatObject
from amrita_core.types import MemoryModel, Message

# 初始化并启用安全功能
init()

# 设置安全配置
security_config = AmritaConfig(
    cookie=CookieConfig(enable_cookie=True)
)

from amrita_core.config import set_config
set_config(security_config)

# Cookie 安全将自动应用于对话
context = MemoryModel()
train = Message(content="您是一个有用的助手。", role="system")

chat = ChatObject(
    context=context,
    session_id="secure_session",
    user_input="你好！",
    train=train.model_dump()
)
```

## 6.2 内容过滤

### 6.2.1 内容过滤机制

AmritaCore 提供了一个灵活的内容过滤机制，可以根据特定安全要求进行自定义。框架默认不包含内置内容过滤器，但提供了实现自定义过滤的钩子：

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

@on_precompletion()
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

### 6.2.2 自定义过滤规则

根据您的特定要求实现自定义过滤规则：

```python
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.on import on_completion

@on_completion()
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

### 6.2.3 敏感信息检测

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

## 6.3 会话隔离

### 6.3.1 会话管理器 (SessionsManager)

AmritaCore 通过 SessionsManager 类实现了一个强大的会话隔离机制，该类是一个单例类，用于管理不同会话的工具、配置和预设，确保各个会话之间的状态相互独立。

SessionsManager 的主要功能包括：

1. **会话生命周期管理**
   - `new_session()`: 创建一个新会话并返回其唯一ID
   - `init_session(session_id)`: 初始化指定会话的相关资源
   - `drop_session(session_id)`: 删除指定会话及其相关资源

2. **会话资源访问**
   - `get_session_data(session_id)`: 获取包含工具、配置、预设等的完整会话数据对象
   - 通过返回的 SessionData 对象访问会话资源：
     - `session_data.tools`: 获取会话的工具管理器
     - `session_data.config`: 获取会话的配置对象
     - `session_data.presets`: 获取会话的预设管理器

3. **会话状态查询**
   - `get_registered_sessions()`: 获取所有已注册的会话ID
   - `get_session_data(session_id, default)`: 安全获取会话数据（如果会话不存在则返回默认值）

以下是使用 SessionsManager 的示例：

```python
from amrita_core.sessions import SessionsManager

# 获取会话管理器实例
session_manager = SessionsManager()

# 创建新会话
session_id = session_manager.new_session()

# 获取会话数据
session_data = session_manager.get_session_data(session_id)
config = session_data.config
tools_manager = session_data.tools
presets_manager = session_data.presets

# 设置会话特定配置
from amrita_core.config import AmritaConfig
new_config = AmritaConfig()
session_data.config = new_config

# 删除会话
session_manager.drop_session(session_id)
```

### 6.3.2 会话ID管理

正确的会话管理对于维持不同用户或对话之间的隔离至关重要：

```python
import uuid
from amrita_core.types import MemoryModel
from amrita_core.sessions import SessionsManager

def create_secure_session() -> tuple[str, MemoryModel]:
    """
    使用 SessionsManager 创建一个新的安全会话，具有唯一的ID和记忆上下文
    """
    session_manager = SessionsManager()
    session_id = session_manager.new_session()
    session_data = session_manager.get_session_data(session_id)
    context = session_data.memory  # 使用会话数据中的记忆实例
    
    return session_id, context

# 示例用法
session_id, context = create_secure_session()
```

### 6.3.3 数据隔离保证

通过 SessionsManager 正确分离对话上下文来确保数据隔离：

```python
from amrita_core import ChatObject
from amrita_core.types import Message
from amrita_core.sessions import SessionsManager

class SecureConversationManager:
    def __init__(self):
        self.session_manager = SessionsManager()
    
    async def process_user_input(self, session_id: str, user_input: str):
        """
        在安全、隔离的会话中处理用户输入
        """
        # 验证会话是否存在
        try:
            session_data = self.session_manager.get_session_data(session_id)
        except KeyError:
            # 如果会话不存在则创建新会话
            session_id = self.session_manager.new_session()
            session_data = self.session_manager.get_session_data(session_id)
        
        # 从会话数据获取配置
        config = session_data.config
        
        # 使用会话特定的配置
        chat = ChatObject(
            context=session_data.memory,  # 使用会话特定的记忆
            session_id=session_id,
            user_input=user_input,
            config=config
        )
        
        async with chat.begin():
            response = await chat.full_response()
        
        return response
```


## 6.4 访问控制

### 6.4.1 权限机制

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

@on_precompletion()
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

### 6.4.2 访问限制

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

### 6.4.3 审计日志

实现审计日志以跟踪与安全相关的事件：

```python
from amrita_core.logging import logger
from amrita_core.hook.event import PreCompletionEvent, CompletionEvent
from amrita_core.hook.on import on_precompletion, on_completion

@on_precompletion()
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
    
    

@on_completion()
async def log_response(event: CompletionEvent, user_id: str = None):
    """
    为审计目的记录回复
    """
    user_identifier = user_id or "anonymous"
    
    logger.info(f"回复给用户 {user_identifier}: {len(event.response)} 个字符")
    logger.debug(f"回复给 {user_identifier}: {event.response[:100]}...")
    
    
```
