# Suspend & Resume Mechanism

**Note: This is an advanced feature for special scenarios. Most users do not need to use it directly.**

AmritaCore provides an explicit, lightweight suspend mechanism that allows external control over the execution flow of `ChatObject`, enabling you to pause and resume processing at specific points. Typical use cases include:

- Interactive debugging with state inspection between processing steps
- Custom flow control in complex multi-agent systems
- Coordination with external systems that require synchronization points

## How It Works

Core internal methods of `ChatObject` (such as `_entry`, `_run`, `_run_strategy`) are decorated with the `@suspend` decorator. They automatically check for suspend signals before execution.

Basic workflow:

1. Call `await chat.wait_to_suspend(timeout)` **outside** the main `ChatObject` execution context from a separate async task
2. `ChatObject` will automatically pause when reaching the next `@suspend` decorated method
3. Resume execution by calling `chat.resume()`

## Manual Usage of `_wait_for_continue()`

For fine-grained control, you can manually call `await chat._wait_for_continue()` in your own async functions to create custom suspend points:

```python
import asyncio
from amrita_core import create_agent, minimal_init

async def custom_processing_step(chat_obj):
    """Custom business logic with a manual suspend point"""
    print("Start processing...")
    await asyncio.sleep(0.5)

    # Manual suspend point: blocks only if suspend is triggered externally
    await chat_obj._wait_for_continue()

    print("Resume after suspend point...")
    await asyncio.sleep(0.5)

async def main():
    await minimal_init()
    agent = create_agent(
        base_url="https://api.example.com",
        api_key="your-api-key",
        model="gpt-3.5-turbo",
    )

    chat = agent.get_chatobject("Hello!")

    # External independent control task
    async def external_controller(chat_obj):
        await chat_obj.wait_to_suspend(timeout=5.0)
        print("Chat suspended.")
        await asyncio.sleep(1)
        chat_obj.resume()
        print("Chat resumed.")

    controller_task = asyncio.create_task(external_controller(chat))

    try:
        await custom_processing_step(chat)
        async with chat.begin():
            async for response in chat.get_response_generator():
                content = response if isinstance(response, str) else response.get_content()
                print(content, end="", flush=True)
    finally:
        controller_task.cancel()

asyncio.run(main())
```

### Key Points

- `_wait_for_continue()` is invoked automatically by all `@suspend` decorated methods
- You can insert custom suspend points anywhere in your business logic
- It returns immediately without blocking if no suspend is pending
- Implemented with async signal scheduling, isolated from main business flow

## Standard Usage Example

```python
import asyncio
from amrita_core import create_agent, minimal_init

async def main():
    await minimal_init()
    agent = create_agent(
        base_url="https://api.example.com",
        api_key="your-api-key",
        model="gpt-3.5-turbo",
    )

    chat = agent.get_chatobject("Hello!")

    # External concurrent control logic
    async def external_controller(chat_obj):
        await chat_obj.wait_to_suspend(timeout=5.0)
        print("Chat suspended, you may inspect or modify states here.")
        # Custom operations: state checking, context modification, external integration
        chat_obj.resume()

    async with chat.begin():
        controller_task = asyncio.create_task(external_controller(chat))
        try:
            async for response in chat.get_response_generator():
                content = response if isinstance(response, str) else response.get_content()
                print(content, end="", flush=True)
        finally:
            controller_task.cancel()

asyncio.run(main())
```

## Important Notes

- Control interfaces must be called from a separate concurrent task outside the main `ChatObject` async context
- The timeout parameter in `wait_to_suspend` prevents infinite blocking
- This is a low-level capability intended for framework extension, advanced debugging, and custom workflow orchestration

## When Not to Use This Feature

For common scenarios, please use the standard interaction patterns:

- Streaming response: `async with chat.begin(): async for response in chat.get_response_generator()`
- Callback-based response: `chat.set_callback_func(callback)` + `await chat.begin()`
- Full complete response: `async with chat.begin(): response = await chat.full_response()`

Only use the suspend/resume mechanism for advanced scenarios that require fine external control over internal execution.
