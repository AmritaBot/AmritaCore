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
from amrita_core import init, ChatObject
from amrita_core.types import MemoryModel, Message

# Initialize with security enabled
init()

# Set up security configuration
security_config = AmritaConfig(
    cookie=CookieConfig(enable_cookie=True)
)

from amrita_core.config import set_config
set_config(security_config)

# The cookie security will automatically be applied to conversations
context = MemoryModel()
train = Message(content="You are a helpful assistant.", role="system")

chat = ChatObject(
    context=context,
    session_id="secure_session",
    user_input="Hello!",
    train=train.model_dump()
)
```

## 6.2 Content Filtering

### 6.2.1 Content Filtering Mechanism

AmritaCore provides a flexible content filtering mechanism that can be customized to meet specific security requirements. The framework doesn't include a built-in content filter by default, but provides hooks to implement custom filtering:

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

@on_precompletion()
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

@on_completion()
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

## 6.3 Session Isolation

### 6.3.1 SessionsManager (Session Manager)

AmritaCore implements a powerful session isolation mechanism through the SessionsManager class, which is a singleton class used to manage tools, configurations, and presets for different sessions, ensuring that the state between each session is independent of each other.

The main functions of SessionsManager include:

1. **Session Lifecycle Management**
   - `new_session(config)`: Creates a new session and returns its unique ID
   - `init_session(session_id)`: Initializes resources for the specified session
   - `drop_session(session_id)`: Deletes the specified session and its associated resources

2. **Session Resource Access**
   - `get_session_tools(session_id)`: Gets the tool manager for the session
   - `get_session_config(session_id)`: Gets the configuration object for the session
   - `get_session_presets(session_id)`: Gets the preset manager for the session

3. **Session Status Query**
   - `get_registered_sessions()`: Gets all registered session IDs
   - `get_session_config_safe(session_id)`: Safely gets session configuration (returns None if session does not exist)

Here is an example of using SessionsManager:

```python
from amrita_core.sessions import SessionsManager

# Get session manager instance
session_manager = SessionsManager()

# Create new session
session_id = session_manager.new_session()

# Get session configuration
config = session_manager.get_session_config(session_id)

# Get session tool manager
tools_manager = session_manager.get_session_tools(session_id)

# Get session preset manager
presets_manager = session_manager.get_session_presets(session_id)

# Set session-specific configuration
from amrita_core.config import AmritaConfig
new_config = AmritaConfig()
session_manager.set_session_config(session_id, new_config)

# Delete session
session_manager.drop_session(session_id)
```

### 6.3.2 Session ID Management

Proper session management is crucial for maintaining isolation between different users or conversations:

```python
import uuid
from amrita_core.types import MemoryModel
from amrita_core.sessions import SessionsManager

def create_secure_session() -> tuple[str, MemoryModel]:
    """
    Create a new secure session with unique ID and memory context using SessionsManager
    """
    session_manager = SessionsManager()
    session_id = session_manager.new_session()
    context = MemoryModel()
    
    return session_id, context

# Example usage
session_id, context = create_secure_session()
```

### 6.3.3 Data Isolation Assurance

Ensure data isolation by properly separating conversation contexts using SessionsManager:

```python
from amrita_core import ChatObject
from amrita_core.types import Message
from amrita_core.sessions import SessionsManager

class SecureConversationManager:
    def __init__(self):
        self.session_manager = SessionsManager()
    
    async def process_user_input(self, session_id: str, user_input: str):
        """
        Process user input in a secure, isolated session
        """
        # Verify if session exists
        if session_id not in self.session_manager.get_registered_sessions():
            # Create new session if it doesn't exist
            session_id = self.session_manager.new_session()
        
        # Get configuration from session manager
        config = self.session_manager.get_session_config(session_id)
        
        # Use session-specific configuration
        chat = ChatObject(
            context=None,  # Session manager handles context
            session_id=session_id,
            user_input=user_input,
            config=config
        )
        
        async with chat.begin():
            response = await chat.full_response()
        
        return response
```

### 6.3.4 Cross-Session Protection

Protect against cross-session contamination:

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

@on_precompletion()
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

## 6.4 Access Control

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

@on_precompletion()
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

@on_precompletion()
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
    
    

@on_completion()
async def log_response(event: CompletionEvent, user_id: str = None):
    """
    Log responses for audit purposes
    """
    user_identifier = user_id or "anonymous"
    
    logger.info(f"Response to user {user_identifier}: {len(event.response)} chars")
    logger.debug(f"Response to {user_identifier}: {event.response[:100]}...")
    
    
```
