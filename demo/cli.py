import asyncio
import os
import random

from amrita_core import ChatObject, init, load_amrita, logger, set_config
from amrita_core.config import AmritaConfig, FunctionConfig, LLMConfig
from amrita_core.preset import PresetManager
from amrita_core.types import MemoryModel, Message, ModelConfig, ModelPreset


def get_random_session_id():
    """Generate a random session ID"""
    return f"session_{random.randint(10000, 99999)}"


def print_welcome_message():
    """Print welcome message"""
    print("=" * 50)
    print("🤖 Welcome to AmritaCore CLI Chat System")
    print("=" * 50)
    print("Type '/help' to see available commands")
    print("Type '/new' to start a new session")
    print("Type '/quit' to exit the program")
    print("-" * 50)


def print_help():
    """Print help information"""
    help_text = """
📖 Available Commands:
  Regular text      - Chat with AI assistant
  /new              - Start a new session
  /quit or /exit    - Exit the program
  /help             - Show this help message
  /clear            - Clear screen
  /reset            - Reset conversation history
  /info             - Show current session info
    """
    print(help_text)


async def handle_user_input(
    user_input: str, context: MemoryModel, session_id: str, train: Message
) -> tuple[str, MemoryModel, bool]:
    """Process user input and return new session ID and context"""
    if user_input.lower() in ["/quit", "/exit"]:
        print("👋 Goodbye! Thank you for using AmritaCore CLI Chat System")
        return session_id, context, False  # Return False to indicate exit

    elif user_input.lower() == "/help":
        print_help()
        return session_id, context, True

    elif user_input.lower() == "/new":
        print("🔄 Starting a new session...")
        new_session_id = get_random_session_id()
        new_context = MemoryModel()
        print(f"✅ New session created, ID: {new_session_id}")
        return new_session_id, new_context, True

    elif user_input.lower() == "/clear":
        await asyncio.to_thread(os.system, ("clear" if os.name != "nt" else "cls"))
        print_welcome_message()
        return session_id, context, True

    elif user_input.lower() == "/reset":
        print("🔄 Resetting conversation history...")
        context = MemoryModel()
        print("✅ Conversation history reset")
        return session_id, context, True

    elif user_input.lower() == "/info":
        print(f"ℹ️  Current Session: {session_id}")
        print(
            f"📊 Conversation Turns: {len(context.messages) if context.messages else 0}"
        )
        return session_id, context, True
    elif user_input.startswith("/"):
        print("❌ Invalid command")
        return session_id, context, True

    # Process regular user input
    chat = ChatObject(
        context=context,
        session_id=session_id,
        user_input=user_input,
        train=train.model_dump(),
    )

    async def callback():
        nonlocal context
        if chat is None:
            return
        print("💬 Assistant: ", end="")
        async for message in chat.get_response_generator():
            content = message if isinstance(message, str) else message.get_content()
            print(content, end="")
        print("\n")  # New line

    task = asyncio.create_task(callback())

    try:
        await chat.call()
        await task
        # Update context
        context = chat.data
    except Exception as e:
        print(f"❌ An error occurred: {e!s}")

    return session_id, context, True


async def main():
    print_welcome_message()

    # Load AmritaCore
    # Set configuration
    func = FunctionConfig(
        use_minimal_context=False,
        tool_calling_mode="agent",
        agent_thought_mode="reasoning",
        # agent_mcp_client_enable=True,
        # agent_mcp_server_scripts=[],
    )
    llm = LLMConfig(
        enable_memory_abstract=True,
    )
    config = AmritaConfig(
        function_config=func,
        llm=llm,
    )

    set_config(config)

    await load_amrita()
    os.environ["LOG_LEVEL"] = "WARNING"

    # Add preset model
    preset = ModelPreset(
        model="gpt-3.5-turbo",
        base_url="Insert_your_API_endpoint_here",
        api_key="Insert_your_API_key_here",
        config=ModelConfig(stream=True),
    )

    preset_manager = PresetManager()
    preset_manager.add_preset(preset)
    logger.info("Registered preset.")

    # Initialize session
    context: MemoryModel = MemoryModel()
    session_id = get_random_session_id()
    train = Message(
        content="You are a helpful AI assistant, do not call non-existent tools, follow user's instructions.",
        role="system",
    )

    print(f"✨ Session created, ID: {session_id}")
    print("Start chatting! Type '/help' for help\n")

    # Main loop
    while True:
        try:
            user_input = input("👤 You: ").strip()

            if not user_input:
                continue

            result_session_id, result_context, continue_flag = await handle_user_input(
                user_input, context, session_id, train
            )

            if not continue_flag:
                break

            # 更新session_id和context
            session_id = result_session_id
            context = result_context

        except (EOFError, KeyboardInterrupt):
            print("\n👋 Program interrupted, goodbye!")
            break
        except Exception as e:
            print(f"❌ An unexpected error occurred: {e!s}")
            print("💡 Continuing to run...")


if __name__ == "__main__":
    init()
    asyncio.run(main())
