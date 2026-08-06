# SuspendEnum

The > **v0.12.0 migration**: `SuspendEnum` and `BuiltinName` have been moved from `amrita_core.chatmanager.enums` to `amrita_core.enums`. The old module now emits a `DeprecationWarning` and will be removed in v0.13.x.

`SuspendEnum` class provides standardized breakpoint tags for the suspend/resume mechanism in AmritaCore.

## Description

`SuspendEnum` is a string enumeration that defines built-in breakpoint tags corresponding to key execution points in the `ChatObject` lifecycle. These standard tags enable precise control over the execution flow without requiring custom string literals.

## Enum Values

### `LOAD_STATE`

- **Value**: `"ChatObject::load_state"`
- **Description**: Triggered when loading runtime state from backends
- **Usage**: Occurs at the start of execution to load memory and ability context from the configured BackendSlots. Useful for debugging state loading or implementing custom state initialisation

### `ENTRY_POINT`

- **Value**: `"ChatObject::_entry"`
- **Description**: Triggered at the very beginning of ChatObject execution
- **Usage**: Useful for pre-execution setup, logging, or initialisation hooks before the main workflow starts

### `TRAIN_RENDER`

- **Value**: `"ChatObject::render_train_template"`
- **Description**: Triggered when rendering the Jinja2 training/prompt template
- **Usage**: Ideal for inspecting or modifying the rendered system prompt

### `MEMORY`

- **Value**: `"ChatObject::memory_limiting"`
- **Description**: Triggered before memory summarization when context exceeds token limits
- **Usage**: Perfect for inspecting or modifying context before automatic summarization

### `MESSAGES_PREPARED`

- **Value**: `"ChatObject::prepare_send_messages"`
- **Description**: Triggered after the message list is prepared but before running pre-completion matchers
- **Usage**: Great for final message validation or last-minute modifications

### `PRECOMPLE`

- **Value**: `"matcher_call::pre_completion"`
- **Description**: Triggered before sending messages to the LLM for completion
- **Usage**: Useful for final message validation, security checks, or context modification before model inference

### `STRATEGY_START`

- **Value**: `"ChatObject::run_strategy_start"`
- **Description**: Triggered when the agent strategy execution begins
- **Usage**: Ideal for strategy-level instrumentation or custom pre-strategy logic

### `LLM_CALL`

- **Value**: `"ChatObject::call_llm"`
- **Description**: Triggered during the actual LLM API call
- **Usage**: Useful for monitoring API latency or injecting behaviour around model inference

### `SINGLE_TOOL`

- **Value**: `"ChatObject::single_tool_call"`
- **Description**: Triggered before each individual tool call during agent execution
- **Usage**: Ideal for debugging tool interactions, validating tool parameters, or implementing custom tool approval logic

### `COMPLE`

- **Value**: `"matcher_call::post_completion"`
- **Description**: Triggered after receiving the model response but before processing it
- **Usage**: Great for response validation, content filtering, or implementing custom response handling logic

### `MEMORY_APPEND`

- **Value**: `"Component::memory_append"`
- **Description**: Triggered when appending the LLM response to the context message wrap
- **Usage**: Exposed by the [`APPEND_RESPONSE`](../api-reference/classes/APPEND_RESPONSE.md) component node. Occurs after LLM completion to add the model's response as an assistant message.

### `APPLY_CONTEXT`

- **Value**: `"Component::apply_context"`
- **Description**: Triggered when applying the final context wrap back to the memory model
- **Usage**: Exposed by the [`APPLY_CONTEXT`](../api-reference/classes/APPLY_CONTEXT.md) component node. Occurs before memory commit to write the updated message list into `MemoryModel.messages`.

### `COMMIT_MEMORY`

- **Value**: `"ChatObject::commit_memory"`
- **Description**: Triggered after the execution pipeline completes, when memory is being committed back to the backend
- **Usage**: Occurs at the very end of the workflow to persist conversation state. Useful for monitoring persistence or implementing custom memory commit logic

### `FINALIZE`

- **Value**: `"ChatObject::finalize"`
- **Description**: Triggered at the end of the ChatObject execution pipeline
- **Usage**: Useful for cleanup, logging final state, or post-processing

## BuiltinName

`BuiltinName` is a companion enumeration that provides aliases for internal framework components. Currently defined:

### `AGENT_STRATEGY`

- **Value**: `"ChatObject::__agent_main__"`
- **Description**: Internal alias for the agent strategy subprogram used by the workflow engine

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
        train=train.model_dump(),
    )

    # External controller using standard breakpoints
    async def controller(chat_obj):
        # Wait for tool call breakpoint
        await chat_obj.io_stream.wait_to_suspend(SuspendEnum.SINGLE_TOOL.value)
        print("About to call a tool!")

        # Resume and wait for completion breakpoint
        chat_obj.io_stream.resume()
        await chat_obj.io_stream.wait_to_suspend(SuspendEnum.COMPLE.value)
        print("Received model response!")
        chat_obj.io_stream.resume()

    controller_task = asyncio.create_task(controller(chat))

    try:
        async with chat.begin():
            async for response in chat.io_stream.get_response_generator():
                print(response, end="", flush=True)
            await chat  # Wait for the task to finish before exiting
    finally:
        controller_task.cancel()
```

## Best Practices

- **Use Standard Tags**: Prefer `SuspendEnum` values over custom string tags for better maintainability
- **Version Compatibility**: Standard tags are guaranteed to be stable across versions
- **Debugging**: Combine multiple standard breakpoints for comprehensive debugging workflows
- **Security**: Use `PRECOMPLE` breakpoint for final security validation before model calls

## Related Documentation

- [Suspend & Resume Mechanism](../../advanced/suspend.md)
- [ChatObject Class](ChatObject.md)
