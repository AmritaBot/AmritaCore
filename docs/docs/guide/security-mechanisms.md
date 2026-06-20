<div v-pre >

# Security Mechanisms

## 6.1 Cookie Security Detection

### 6.1.1 Prompt Injection Protection

AmritaCore implements robust prompt injection protection through its cookie security detection mechanism. This feature adds a unique "cookie" to conversations that helps detect if an attacker is attempting to manipulate the AI's behavior by injecting malicious instructions.

The cookie system works by inserting a unique identifier into the conversation context that remains consistent throughout a session. If this cookie is detected in unexpected places in the AI's response, it indicates a potential prompt injection attack.

### 6.1.2 CookieConfig Configuration

The [CookieConfig](../api-reference/classes/CookieConfig.md) class manages cookie-related security settings:

```python
from amrita_core.config import CookieConfig

# Enable cookie security detection
security_config = CookieConfig(
    enable_cookie=True,              # Enable the cookie leak detection mechanism
    cookie="custom_cookie_string"    # Custom cookie string (defaults to random string)
)

# Or let the system generate a random cookie automatically
default_security_config = CookieConfig(enable_cookie=True)
```

The cookie is automatically generated as a random alphanumeric string if not explicitly provided, ensuring uniqueness across sessions.

### 6.1.3 Security Detection Examples

Here's how to implement and use the cookie security detection:

```python
from amrita_core.config import AmritaConfig, CookieConfig
from amrita_core import ChatObject
from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.backends import LegacyBackend

# Set up security configuration
security_config = AmritaConfig(
    cookie=CookieConfig(enable_cookie=True)
)

from amrita_core.config import set_config
set_config(security_config)

# The cookie security will automatically be applied to conversations
chat = ChatObject(
    train={"role": "system", "content": "You are a helpful assistant."},
    user_input="Hello!",
    context=None,
    session_id="secure_session",
    backend=BackendSlots(ability=LegacyBackend(), memory=LegacyBackend()),
)
```

## 6.2 Content Filtering

### 6.2.1 Content Filtering Mechanism

AmritaCore provides a flexible content filtering mechanism that can be customized to meet specific security requirements. The framework doesn't include a built-in content filter by default, but provides hooks to implement custom filtering:

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

@on_precompletion().handle()
async def content_filter(event: PreCompletionEvent):
    """
    Filter potentially unsafe content before processing
    """
    # Check user messages for potentially harmful content
    for msg in event.messages:
        if msg.role == "user":
            # Implement your content filtering logic here
            if contains_harmful_content(msg.content):
                # Replace with a safer message or add a warning
                msg.content = "[CONTENT FILTERED FOR SAFETY]"



def contains_harmful_content(content: str) -> bool:
    """
    Example function to detect harmful content
    This is a simplified example - a real implementation would be more sophisticated
    """
    harmful_keywords = [
        "jailbreak", "ignore instructions", "prompt injection",
        "system prompt", "role play as", "never say"
    ]

    content_lower = content.lower()
    return any(keyword in content_lower for keyword in harmful_keywords)
```

### 6.2.2 Custom Filtering Rules

Implement custom filtering rules based on your specific requirements:

```python
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.on import on_completion

@on_completion().handle()
async def response_filter(event: CompletionEvent):
    """
    Filter the AI's response for sensitive information
    """
    # Check for potential data leakage in the response
    if contains_sensitive_info(event.response):
        # Log the incident and modify the response if necessary
        print(f"Potential sensitive info detected in response: {event.response[:100]}...")
        # Optionally modify the response
        # event.response = "[RESPONSE MODIFIED FOR SECURITY]"



def contains_sensitive_info(content: str) -> bool:
    """
    Detect if response contains sensitive information
    """
    # Example: Check for apparent internal system information
    sensitive_patterns = [
        "system:", "internal:", "admin:", "password:", "secret:"
    ]

    content_lower = content.lower()
    return any(pattern in content_lower for pattern in sensitive_patterns)
```

### 6.2.3 Sensitive Information Detection

Implement detection for sensitive information to prevent data leakage:

```python
import re

def detect_sensitive_information(text: str):
    """
    Detect various types of sensitive information in text
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

## 6.3 Template Security Enhancements

### 6.3.1 Jinja2 Template Escaping

AmritaCore automatically applies HTML escaping to user-provided content in Jinja2 templates to **prevent user input from breaking the structured format of system messages**.

**Enhanced Template Safety**:

```jinja2
{% if original_msg %}
<INPUT>
{{original_msg|escape}}  {# Automatic escaping applied here #}
</INPUT>
{% endif %}
```

The `|escape` filter is now automatically applied to the `original_msg` variable in system message templates, ensuring that any user input containing special characters (like `<`, `>`, `{`, `}`, etc.) is properly escaped before being included in prompts. This prevents:

- **Template Structure Corruption**: User input with curly braces `{{}}` or other Jinja2 syntax won't interfere with template rendering
- **XML/HTML Structure Breakage**: Special characters like `<` and `>` won't break the XML-like structure used in system messages
- **Unintended Template Execution**: Prevents user-provided content from being interpreted as template code

**Security Impact**:

- Maintains the integrity of system message structure
- Prevents template injection when user input contains template syntax
- Ensures predictable prompt formatting regardless of user input content
- Backward compatible - existing templates continue to work as expected

### 6.3.2 Adapter Type Safety Validation

AmritaCore now includes built-in type safety validation for adapter usage to prevent accidental misuse of adapters.

**Automatic Type Validation**:

```python
from amrita_core.libchat import call_completion

# This will raise RuntimeError if adapter doesn't support "text-gen"
response = await call_completion(preset=text_gen_preset, messages=["Hello"])

# Embedding adapters are validated to only be used for embedding calls
embeddings = await call_completion(preset=embedding_preset, messages=["Hello"])
```

**Validation Logic**:

- When using `call_completion()` for text generation, the system validates that the adapter supports `"text-gen"` type
- If an embedding-only adapter is used for text generation, a `RuntimeError` is raised with clear error message
- This prevents silent failures and confusing behavior when adapters are misused

**Example Error Message**:

```shell
RuntimeError: Invalid adapter type for text-gen when using adapter: MyEmbeddingAdapter, this adapter only supports embed.
```

### 6.3.3 Best Practices for Secure Template Usage

When working with custom Jinja2 templates in AmritaCore, follow these security best practices:

1. **Use Built-in Escaping**: Rely on AmritaCore's automatic escaping for user-provided content
2. **Validate Template Variables**: Ensure custom template variables don't contain executable code
3. **Avoid Raw HTML**: Never use the `|safe` filter unless you have complete control over the content
4. **Test with Malicious Input**: Always test templates with potentially malicious input to verify escaping works correctly

**Safe Custom Template Example**:

```python
from jinja2 import Template

# Safe template - user content will be escaped
safe_template = Template("""
SYSTEM: {{ role_instructions }}
USER INPUT: {{ user_input|escape }}
CONTEXT: {{ context_summary|escape }}
""")

# Use with confidence - escaping is handled automatically
rendered = safe_template.render(
    role_instructions="You are a helpful assistant",
    user_input="<script>alert('xss')</script>",  # Will be escaped
    context_summary="Previous conversation context"
)
```

**Template Variable Naming Security**:
As documented in the [Jinja2 Template Variables Safety](../extensions-integration/jinja2-templates.md#template-variable-naming-safety) section, avoid using variable names that conflict with built-in parameters (`train`, `memory`, `chatobj`, `config`) to prevent `TypeError` due to duplicate keyword arguments.

### 6.3.4 Comprehensive Security Architecture

AmritaCore's security enhancements work together to provide defense in depth:

| Security Layer          | Protection Provided                 | Supported |
| ----------------------- | ----------------------------------- | --------- |
| Cookie Detection        | Prompt injection detection          | Yes       |
| Template Escaping       | XSS prevention in prompts           | Yes       |
| Adapter Type Validation | Prevents adapter misuse             | Yes       |
| Session Isolation       | Prevents cross-session data leakage | Yes       |

These layers ensure that AmritaCore applications remain secure against common attack vectors while maintaining ease of use and developer productivity.

## 6.4 Session Isolation

Session isolation is handled by the [data backend](../guide/concepts/data-backend.md) mechanism. Each `ChatObject` receives a `BackendSlots` instance that controls how memory and abilities are loaded and persisted per session.

### 6.4.1 Backend-Driven Isolation

The default `LegacyBackend` stores all session data in in-process global containers. For stronger isolation, implement a custom backend:

```python
from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.backends import LegacyBackend

# Default: global containers (all sessions share tools/presets)
backend = BackendSlots(ability=LegacyBackend(), memory=LegacyBackend())
```

### 6.4.2 Session ID Management

Each session is identified by a unique `session_id` string. The backend uses this ID to look up or create per-session state:

```python
import uuid
from amrita_core.types import MemoryModel

def create_session_id() -> str:
    """Generate a unique session identifier."""
    return uuid.uuid4().hex
```

### 6.4.3 Data Isolation Example

Ensure data isolation by using a custom backend that strictly separates per-session memory:

```python
from amrita_core import ChatObject
from amrita_core.base.backend import BackendSlots, MemoryBackend
from amrita_core.builtins.backends import LegacyBackend
from amrita_core.types import MemoryModel

class IsolatedMemoryBackend(MemoryBackend):
    """Per-session memory backed by a dict."""
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
            train={"role": "system", "content": "You are a helpful assistant."},
            user_input=user_input,
            context=None,
            session_id=session_id,
            backend=self._slot,
        )
        async with chat.begin():
            return await chat.full_response()
```

### 6.4.4 Cross-Session Protection

Protect against cross-session contamination:

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

@on_precompletion().handle()
async def session_isolation_check(event: PreCompletionEvent, session_id: str = None):
    """
    Ensure that session-specific data doesn't leak across sessions
    """
    # Verify that no session-specific identifiers appear inappropriately
    if session_id:
        for msg in event.messages:
            if session_id in msg.content and msg.role != "system":
                # This could indicate a potential leak or injection
                print(f"Warning: Session ID appeared in non-system message: {msg.content}")


```

## 6.5 Access Control

### 6.4.1 Permission Mechanisms

While AmritaCore itself doesn't implement a comprehensive permission system, it provides hooks to integrate with external access control mechanisms:

```python
from typing import Dict, List
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

class AccessControlManager:
    def __init__(self):
        self.user_permissions: Dict[str, List[str]] = {}

    def has_permission(self, user_id: str, permission: str) -> bool:
        """
        Check if a user has a specific permission
        """
        user_perms = self.user_permissions.get(user_id, [])
        return permission in user_perms

    def add_permission(self, user_id: str, permission: str):
        """
        Grant a permission to a user
        """
        if user_id not in self.user_permissions:
            self.user_permissions[user_id] = []
        if permission not in self.user_permissions[user_id]:
            self.user_permissions[user_id].append(permission)

access_manager = AccessControlManager()

@on_precompletion().handle()
async def check_access_control(event: PreCompletionEvent, user_id: str = None):
    """
    Check access permissions before processing
    """
    if user_id:
        # Example: Check if user can access advanced tools
        if not access_manager.has_permission(user_id, "advanced_tools"):
            # Filter out advanced tool usage
            event.messages = filter_advanced_tools(event.messages)



def filter_advanced_tools(messages):
    """
    Remove or modify messages that request advanced tools if user doesn't have permission
    """
    # Implementation would depend on your specific tool access requirements
    return messages
```

### 6.4.2 Access Limitations

Implement rate limiting and access constraints:

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
        # Clean old requests
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if now - req_time < timedelta(seconds=self.time_window)
        ]

        if len(self.requests[user_id]) >= self.max_requests:
            return False

        self.requests[user_id].append(now)
        return True

rate_limiter = RateLimiter(max_requests=5, time_window=60)

# Use in your API endpoint
def handle_request(user_id: str):
    if not rate_limiter.is_allowed(user_id):
        raise Exception("Rate limit exceeded")

    # Process the request
    pass
```

### 6.4.3 Audit Logging

Implement audit logging to track security-relevant events:

```python
from amrita_core.logging import logger
from amrita_core.hook.event import PreCompletionEvent, CompletionEvent
from amrita_core.hook.on import on_precompletion, on_completion

@on_precompletion().handle()
async def log_request(event: PreCompletionEvent, user_id: str = None):
    """
    Log incoming requests for audit purposes
    """
    user_identifier = user_id or "anonymous"

    logger.info(f"Request from user {user_identifier}: {len(event.messages)} messages")

    # Log user messages specifically
    for msg in event.messages:
        if msg.role == "user":
            logger.debug(f"User {user_identifier} said: {msg.content[:100]}...")



@on_completion().handle()
async def log_response(event: CompletionEvent, user_id: str = None):
    """
    Log responses for audit purposes
    """
    user_identifier = user_id or "anonymous"

    logger.info(f"Response to user {user_identifier}: {len(event.response)} chars")
    logger.debug(f"Response to {user_identifier}: {event.response[:100]}...")


```

</div>
