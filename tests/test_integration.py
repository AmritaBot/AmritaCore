import asyncio

import pytest

from amrita_core import init
from amrita_core.chatmanager import ChatObject, chat_manager
from amrita_core.config import AmritaConfig
from amrita_core.sessions import SessionsManager
from amrita_core.types import MemoryModel, Message, ModelPreset


class TestIntegration:
    """Test integration between various modules"""

    def setup_method(self):
        """Reset state before each test method"""
        SessionsManager._instance = None
        chat_manager.running_chat_object.clear()
        chat_manager.running_chat_object_id2map.clear()

    @pytest.mark.asyncio
    async def test_session_creation_and_chat_flow(self):
        """Test session creation and chat flow integration"""
        # Initialize AmritaCore
        init()

        # Create a new session
        sm = SessionsManager()
        session_id = sm.new_session()

        # Verify session is created
        assert sm.is_session_registered(session_id)

        # Get session data
        session_data = sm.get_session_data(session_id)
        config = session_data.config
        tools = session_data.tools
        presets = session_data.presets

        assert isinstance(config, AmritaConfig)
        assert tools is not None
        assert presets is not None

        # Create a default preset to avoid the random choice error
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )
        presets.set_default_preset(default_preset)

        # Create a simple chat object
        train = {"role": "system", "content": "You are a helpful assistant."}
        user_input = "Hello, how are you?"
        context = MemoryModel()

        # Create chat object using session config
        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=context,
            session_id=session_id,
            config=config,
            preset=default_preset,  # Pass a preset to avoid the error
        )

        # Add to chat manager
        await chat_manager.add_chat_object(chat_obj)

        # Verify chat object is added
        session_objects = chat_manager.get_objs(session_id)
        assert len(session_objects) >= 1

        # Get all running object metadata
        all_objs = chat_manager.get_all_objs()
        assert len([obj for obj in all_objs if obj.session_id == session_id]) >= 1

    @pytest.mark.asyncio
    async def test_multiple_sessions_with_different_configs(self):
        """Test multiple sessions with different configurations"""
        # Create multiple sessions
        sm = SessionsManager()

        configs = []
        session_ids = []

        for i in range(3):
            # Create custom config
            config = AmritaConfig()
            config.llm.max_retries = 3 + i  # Different retry settings

            # Create session
            session_id = sm.new_session()
            session_ids.append(session_id)

            # Get session data and set config
            session_data = sm.get_session_data(session_id)
            session_data.config = config

            # Save config reference for later verification
            configs.append(config)

        # Verify all sessions are registered
        assert len(sm.get_registered_sessions()) == 3

        # Verify each session has the correct config
        for i, sid in enumerate(session_ids):
            session_data = sm.get_session_data(sid)
            session_config = session_data.config
            assert session_config.llm.max_retries == configs[i].llm.max_retries

    @pytest.mark.asyncio
    async def test_memory_interaction_with_chat_object(self):
        """Test memory interaction with chat object"""
        # Create session
        sm = SessionsManager()
        session_id = sm.new_session()

        # Create memory with initial messages
        initial_memory = MemoryModel()
        initial_message = Message(role="assistant", content="Previous conversation")
        initial_memory.messages.append(initial_message)

        # Create a default preset to avoid the random choice error
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        # Create chat object
        train = {"role": "system", "content": "You are a helpful assistant."}
        user_input = "What did we talk about before?"

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=initial_memory,
            session_id=session_id,
            preset=default_preset,  # Pass a preset to avoid the error
        )

        # Verify chat object's user input
        assert chat_obj.user_input == user_input

        # Verify chat object's memory
        assert len(chat_obj.data.messages) == 1  # Should contain initial message
        assert chat_obj.data.messages[0].content == "Previous conversation"

    @pytest.mark.asyncio
    async def test_preset_integration(self):
        """Test preset integration with chat object"""
        # Create session
        sm = SessionsManager()
        session_id = sm.new_session()

        # Get session's preset manager
        session_data = sm.get_session_data(session_id)
        presets_manager = session_data.presets

        # Create a custom preset
        custom_preset = ModelPreset(
            model="gpt-4-test",
            name="integration-test-preset",
            base_url="https://api.openai.com/v1",  # Using a valid field
        )

        # Set preset as default
        presets_manager.set_default_preset(custom_preset)

        # Create chat object using this preset
        train = {"role": "system", "content": "You are a helpful assistant."}
        user_input = "Test preset integration"
        context = MemoryModel()

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=context,
            session_id=session_id,
            preset=custom_preset,
        )

        # Verify chat object uses correct preset
        assert chat_obj.preset.name == "integration-test-preset"
        assert chat_obj.preset.model == "gpt-4-test"


@pytest.mark.asyncio
async def test_full_workflow():
    """Test full workflow"""
    # Initialize
    init()

    # Create session
    sm = SessionsManager()
    session_id = sm.new_session()

    # Prepare chat parameters
    train = {"role": "system", "content": "You are a helpful assistant."}
    user_input = "Hello, let's test the full workflow!"
    context = MemoryModel()

    # Create a default preset to avoid the random choice error
    default_preset = ModelPreset(
        model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
    )

    # Create and start chat object
    chat_obj = ChatObject(
        train=train,
        user_input=user_input,
        context=context,
        session_id=session_id,
        preset=default_preset,  # Pass a preset to avoid the error
    ).begin()

    # Add to manager
    await chat_manager.add_chat_object(chat_obj)

    # Wait a bit for object processing
    await asyncio.sleep(0.05)

    # Verify object status
    assert chat_obj.session_id == session_id

    # Verify manager has object
    session_objects = chat_manager.get_objs(session_id)
    assert len(session_objects) >= 1

    # Cleanup
    chat_obj.terminate()


@pytest.mark.asyncio
async def test_concurrent_sessions_and_objects():
    """Test concurrent sessions and objects"""
    # Initialize
    init()

    # Create multiple sessions
    sm = SessionsManager()
    session_ids = [sm.new_session() for _ in range(3)]

    # Concurrently create chat objects
    async def create_and_manage_chat(session_id):
        train = {"role": "system", "content": f"System for session {session_id}"}
        user_input = f"Test message for {session_id}"
        context = MemoryModel()

        # Create a default preset to avoid the random choice error
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name=f"test-{session_id[:8]}", api_key="fake-key"
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=context,
            session_id=session_id,
            preset=default_preset,  # Pass a preset to avoid the error
        ).begin()

        await chat_manager.add_chat_object(chat_obj)
        return chat_obj

    # Concurrently create multiple chat objects
    chat_objects = await asyncio.gather(
        *[create_and_manage_chat(sid) for sid in session_ids]
    )

    # Verify all objects are correctly created and managed
    for i, sid in enumerate(session_ids):
        session_objects = chat_manager.get_objs(sid)
        assert len(session_objects) >= 1

        # Check if corresponding chat object exists
        assert any(obj.session_id == sid for obj in session_objects)

    # Clean up all objects
    for obj in chat_objects:
        obj.terminate()
