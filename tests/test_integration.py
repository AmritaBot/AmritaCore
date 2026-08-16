import asyncio

import pytest

from amrita_core.chatmanager import ChatObject, chat_manager
from amrita_core.types import MemoryModel, Message, ModelPreset


class TestIntegration:
    """Test integration between various modules using the new backend API"""

    def setup_method(self):
        """Reset state before each test method"""
        chat_manager.running_chat_object.clear()
        chat_manager.running_chat_object_id2map.clear()

    @pytest.mark.asyncio
    async def test_chat_creation_with_session_id(self):
        """Create a ChatObject with session_id and verify wiring"""
        session_id = "integration-session-id"

        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        train = {"role": "system", "content": "You are a helpful assistant."}
        user_input = "Hello, how are you?"

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            session_id=session_id,
            preset=default_preset,
        )

        assert chat_obj.session_id == session_id
        assert chat_obj.preset.name == "test-default"

        # Add to chat manager
        await chat_manager.add_chat_object(chat_obj)

        session_objects = chat_manager.get_objs(session_id)
        assert len(session_objects) >= 1

        all_objs = chat_manager.get_all_objs()
        assert len([obj for obj in all_objs if obj.session_id == session_id]) >= 1

    @pytest.mark.asyncio
    async def test_chat_with_session_id_default_backend(self):
        """Create a ChatObject with session_id and default LegacyBackend"""
        session_id = "integration-session-backend"

        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        train = {"role": "system", "content": "You are a helpful assistant."}
        user_input = "Test session backend"

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            session_id=session_id,
            preset=default_preset,
        )

        assert chat_obj._s_id == session_id
        assert isinstance(chat_obj.slot.ability, object)

        await chat_manager.add_chat_object(chat_obj)

        session_objects = chat_manager.get_objs(session_id)
        assert len(session_objects) >= 1

    @pytest.mark.asyncio
    async def test_memory_interaction_with_chat_object(self):
        """Test memory interaction with chat object via the data setter"""
        session_id = "memory-integration-test"

        initial_memory = MemoryModel()
        initial_message = Message(role="assistant", content="Previous conversation")
        initial_memory.messages.append(initial_message)

        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        train = {"role": "system", "content": "You are a helpful assistant."}
        user_input = "What did we talk about before?"

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            session_id=session_id,
            preset=default_preset,
        )
        chat_obj.data = initial_memory

        assert chat_obj.user_input == user_input
        assert len(chat_obj.data.messages) == 1
        assert chat_obj.data.messages[0].content == "Previous conversation"

    @pytest.mark.asyncio
    async def test_preset_integration(self):
        """Test preset integration with chat object"""
        session_id = "preset-integration-test"

        custom_preset = ModelPreset(
            model="gpt-4-test",
            name="integration-test-preset",
            base_url="https://api.openai.com/v1",
            api_key="fake-key",
        )

        train = {"role": "system", "content": "You are a helpful assistant."}
        user_input = "Test preset integration"

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            session_id=session_id,
            preset=custom_preset,
        )

        assert chat_obj.preset.name == "integration-test-preset"
        assert chat_obj.preset.model == "gpt-4-test"


@pytest.mark.asyncio
async def test_full_workflow():
    """Test full workflow using session_id"""
    session_id = "full-workflow-test"

    default_preset = ModelPreset(
        model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
    )

    train = {"role": "system", "content": "You are a helpful assistant."}
    user_input = "Hello, let's test the full workflow!"

    chat_obj = ChatObject(
        train=train,
        user_input=user_input,
        session_id=session_id,
        preset=default_preset,
    ).begin()

    await chat_manager.add_chat_object(chat_obj)
    await asyncio.sleep(0.05)

    assert chat_obj.session_id == session_id

    session_objects = chat_manager.get_objs(session_id)
    assert len(session_objects) >= 1

    chat_obj.terminate()


@pytest.mark.asyncio
async def test_concurrent_chat_objects():
    """Test concurrent chat objects with independent sessions"""
    session_ids = [f"concurrent-{i}" for i in range(3)]

    async def create_and_manage_chat(session_id):
        train = {"role": "system", "content": f"System for session {session_id}"}
        user_input = f"Test message for {session_id}"
        default_preset = ModelPreset(
            model="gpt-3.5-turbo",
            name=f"test-{session_id[:8]}",
            api_key="fake-key",
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            session_id=session_id,
            preset=default_preset,
        ).begin()

        await chat_manager.add_chat_object(chat_obj)
        return chat_obj

    chat_objects = await asyncio.gather(
        *[create_and_manage_chat(sid) for sid in session_ids]
    )

    for sid in session_ids:
        session_objects = chat_manager.get_objs(sid)
        assert len(session_objects) >= 1
        assert any(obj.session_id == sid for obj in session_objects)

    for obj in chat_objects:
        obj.terminate()
