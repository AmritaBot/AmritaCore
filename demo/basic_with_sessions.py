"""
Basic Example with Sessions for AmritaCore - Demonstrating Session Isolation

This example demonstrates how to use the SessionsManager to create and manage
isolated sessions with separate contexts, configurations, and tools.
"""

import asyncio

from amrita_core import ChatObject, init, load_amrita, logger
from amrita_core.config import AmritaConfig, CookieConfig, FunctionConfig, LLMConfig
from amrita_core.preset import PresetManager
from amrita_core.sessions import SessionsManager
from amrita_core.types import Message, ModelConfig, ModelPreset


async def basic_with_sessions_example():
    """
    Example demonstrating session isolation in AmritaCore.
    Shows how to create multiple isolated sessions with separate contexts.
    """
    print("🔐 Starting AmritaCore Session Isolation Example")
    print("-" * 60)

    # Initialize SessionsManager
    session_manager = SessionsManager()

    # Configure AmritaCore with security features
    func = FunctionConfig(
        use_minimal_context=False,
        tool_calling_mode="agent",
        agent_thought_mode="reasoning",
    )

    llm = LLMConfig(
        enable_memory_abstract=True,
    )

    # Enable cookie security detection for session isolation
    cookie_config = CookieConfig(enable_cookie=True)

    config = AmritaConfig(function_config=func, llm=llm, cookie=cookie_config)

    # Apply the configuration
    from amrita_core.config import set_config

    set_config(config)

    # Load AmritaCore components
    await load_amrita()

    # Setup model preset - define which LLM to use
    preset = ModelPreset(
        model="gpt-3.5-turbo",
        base_url="INSERT_YOUR_API_ENDPOINT_HERE",  # Replace with actual endpoint
        api_key="INSERT_YOUR_API_KEY_HERE",  # Replace with actual API key
        config=ModelConfig(stream=True),
    )

    # Register the model preset
    preset_manager = PresetManager()
    preset_manager.add_preset(preset)
    preset_manager.set_default_preset(preset.name)
    logger.info("✅ Registered model preset.")

    print("👥 Creating multiple isolated sessions...")

    # Create two separate sessions
    session1_id = session_manager.new_session()
    session2_id = session_manager.new_session()

    print(f"🔒 Session 1 ID: {session1_id[:8]}...")
    print(f"🔒 Session 2 ID: {session2_id[:8]}...")

    # Verify sessions are registered
    registered_sessions = session_manager.get_registered_sessions()
    print(f"📋 Total registered sessions: {len(registered_sessions)}")

    # Define different system instructions for each session
    train1 = Message(
        content="You are a coding expert. Always provide detailed explanations for code.",
        role="system",
    )

    train2 = Message(
        content="You are a creative writer. Always respond with enthusiasm and creativity.",
        role="system",
    )

    print("\n💬 Starting conversations in isolated sessions:")
    print("=" * 60)

    # First interaction in Session 1
    print("\n👤 User (Session 1): Hello, I'm a developer. Can you help me?")

    # Get session-specific config and context
    session1 = session_manager.get_session_data(session1_id)
    session1_config = session1.config
    session1_context = session1.memory

    chat1 = ChatObject(
        context=session1_context,
        session_id=session1_id,
        user_input="Hello, I'm a developer. Can you help me?",
        train=train1.model_dump(),
        config=session1_config,
    )

    print("🤖 Assistant (Session 1): ", end="")
    async with chat1.begin():
        async for message in chat1.get_response_generator():
            content = message if isinstance(message, str) else message.get_content()
            print(content, end="")

    print()

    # First interaction in Session 2
    print("\n👤 User (Session 2): Hi there! I need some creative ideas.")

    # Get session-specific config and context
    session2 = session_manager.get_session_data(session2_id)
    session2_config = session2.config
    session2_context = session2.memory
    chat2 = ChatObject(
        context=session2_context,
        session_id=session2_id,
        user_input="Hi there! I need some creative ideas.",
        train=train2.model_dump(),
        config=session2_config,
    )

    print("🤖 Assistant (Session 2): ", end="")
    async with chat2.begin():
        async for message in chat2.get_response_generator():
            content = message if isinstance(message, str) else message.get_content()
            print(content, end="")

    print()

    # Follow-up in Session 1 to demonstrate context isolation
    print(
        "\n👤 User (Session 1): Can you give me a Python function to reverse a string?"
    )

    # Retrieve updated context for session 1
    session1_context = session1.memory

    chat1_followup = ChatObject(
        context=session1_context,
        session_id=session1_id,
        user_input="Can you give me a Python function to reverse a string?",
        train=train1.model_dump(),
        config=session1_config,
    )

    print("🤖 Assistant (Session 1): ", end="")
    async with chat1_followup.begin():
        async for message in chat1_followup.get_response_generator():
            content = message if isinstance(message, str) else message.get_content()
            print(content, end="")
    print()

    # Follow-up in Session 2 to demonstrate context isolation
    print(
        "\n👤 User (Session 2): Could you help me write a short poem about technology?"
    )

    # Retrieve updated context for session 2
    session2_context = session2.memory

    chat2_followup = ChatObject(
        context=session2_context,
        session_id=session2_id,
        user_input="Could you help me write a short poem about technology?",
        train=train2.model_dump(),
        config=session2_config,
    )

    print("🤖 Assistant (Session 2): ", end="")
    async with chat2_followup.begin():
        async for message in chat2_followup.get_response_generator():
            content = message if isinstance(message, str) else message.get_content()
            print(content, end="")
    print("\n")

    # Demonstrate session isolation by checking that contexts are different
    session1_memory = session1.memory
    session2_memory = session2.memory

    print("🔍 Verifying session isolation:")
    print(f"   Session 1 conversation count: {len(session1_memory.messages)}")
    print(f"   Session 2 conversation count: {len(session2_memory.messages)}")

    # Show that sessions have different configurations
    session1_config = session1.config
    session2_config = session2.config

    print(
        f"   Session 1 has unique config: {id(session1_config) != id(session2_config)}"
    )

    # Show that sessions have different tools managers
    session1_tools = session1.tools
    session2_tools = session2.tools

    print(
        f"   Session 1 and 2 have different tool managers: {id(session1_tools) != id(session2_tools)}"
    )

    print("\n✅ Session isolation demonstrated successfully!")
    print("-" * 60)
    print("💡 Key concepts demonstrated:")
    print("   • Creating multiple isolated sessions")
    print("   • Separate contexts for each session")
    print("   • Different system instructions per session")
    print("   • Independent configurations per session")
    print("   • Verification of data isolation")
    print("   • Session lifecycle management")


async def advanced_session_management_example():
    """
    Advanced example showing session management capabilities
    """
    print("\n⚙️  Advanced Session Management Example")
    print("-" * 50)

    session_manager = SessionsManager()

    # Create multiple sessions
    session_ids = [session_manager.new_session() for _ in range(3)]
    print(
        f"📋 Created {len(session_ids)} sessions: {[sid[:8] + '...' for sid in session_ids]}"
    )

    # Modify session-specific configurations
    for i, session_id in enumerate(session_ids):
        config = session_manager.get_session_data(session_id).config
        config.llm.enable_memory_abstract = i % 2 == 0  # Alternate memory abstraction
        # The same object reference, so there are no need to re-assign
        print(f"⚙️  Configured session {i + 1} (ID: {session_id[:8]}...)")

    # Verify registered sessions
    registered = session_manager.get_registered_sessions()
    print(f"📋 Total registered sessions: {len(registered)}")

    # Drop one session
    dropped_session = session_ids[0]
    session_manager.drop_session(dropped_session)
    print(f"🗑️  Dropped session: {dropped_session[:8]}...")

    # Verify session was removed
    remaining = session_manager.get_registered_sessions()
    print(f"📋 Remaining registered sessions: {len(remaining)}")

    print("✅ Advanced session management completed!")


if __name__ == "__main__":
    # Initialize AmritaCore
    init()

    # Run examples
    asyncio.run(basic_with_sessions_example())
    asyncio.run(advanced_session_management_example())

    print("\n✨ All session isolation examples completed!")
