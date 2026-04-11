# SuspendEnum

The `SuspendEnum` class provides standardized breakpoint tags for the suspend/resume mechanism in AmritaCore.

## Description

`SuspendEnum` is a string enumeration that defines built-in breakpoint tags corresponding to key execution points in the `ChatObject` lifecycle. These standard tags enable precise control over the execution flow without requiring custom string literals.

## Enum Values

### `MEMORY`

- **Value**: `"ChatObject::memory_limiting"`
- **Description**: Triggered before memory summarization when context exceeds token limits
- **Usage**: Perfect for inspecting or modifying context before automatic summarization

### `SINGLE_TOOL`

- **Value**: `"ChatObject::single_tool_call"`
- **Description**: Triggered before each individual tool call during agent execution
- **Usage**: Ideal for debugging tool interactions, validating tool parameters, or implementing custom tool approval logic

### `PRECOMPLE`

- **Value**: `"matcher_call::pre_completion"`
- **Description**: Triggered before sending messages to the LLM for completion
- **Usage**: Useful for final message validation, security checks, or context modification before model inference

### `COMPLE`

- **Value**: `"matcher_call::post_completion"`
- **Description**: Triggered after receiving the model response but before processing it
- **Usage**: Great for response validation, content filtering, or implementing custom response handling logic

## Usage Example

```python
from amrita_core import ChatObject, SuspendEnum
from amrita_core.types import MemoryModel, Message

async def main():
    context = MemoryModel()
    train = Message(content="You are a helpful assistant.", role="system")

    chat = ChatObject(
        context=context,
        session_id="session_123",
        user_input="What's the weather like?",
        train=train.model_dump()
    )

    # External controller using standard breakpoints
    async def controller(chat_obj):
        # Wait for tool call breakpoint
        await chat_obj.wait_to_suspend(SuspendEnum.SINGLE_TOOL.value)
        print("About to call a tool!")

        # Resume and wait for completion breakpoint
        chat_obj.resume()
        await chat_obj.wait_to_suspend(SuspendEnum.COMPLE.value)
        print("Received model response!")
        chat_obj.resume()

    controller_task = asyncio.create_task(controller(chat))

    try:
        async with chat.begin():
            async for response in chat.get_response_generator():
                print(response, end="", flush=True)
    finally:
        controller_task.cancel()
```

## Best Practices

- **Use Standard Tags**: Prefer `SuspendEnum` values over custom string tags for better maintainability
- **Version Compatibility**: Standard tags are guaranteed to be stable across versions
- **Debugging**: Combine multiple standard breakpoints for comprehensive debugging workflows
- **Security**: Use `PRECOMPLE` breakpoint for final security validation before model calls

## Related Documentation

- [Suspend & Resume Mechanism](../../concepts/suspend.md)
- [ChatObject Class](ChatObject.md)
