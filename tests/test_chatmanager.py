import asyncio

import pytest

from amrita_core.chatmanager import ChatObject, MemoryLimiter, chat_manager
from amrita_core.config import AmritaConfig
from amrita_core.sessions import SessionsManager
from amrita_core.types import (
    CONTENT_LIST_TYPE_ITEM,
    MemoryModel,
    Message,
    ModelPreset,
)


class TestChatObject:
    """Test ChatObject class functionality"""

    def setup_method(self):
        """Clean up state before each test method"""
        # Reset SessionsManager
        SessionsManager._instance = None

    @pytest.mark.asyncio
    async def test_chat_object_initialization(self):
        """Test ChatObject initialization"""
        session_id = "test-session-123"
        sm = SessionsManager()
        sm.init_session(session_id)

        train = {"role": "system", "content": "system message"}
        user_input = "hello"
        context = MemoryModel()

        # Create a default preset to avoid the random choice error
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=context,
            session_id=session_id,
            preset=default_preset,  # Pass a preset to avoid the error
        )

        assert chat_obj.session_id == session_id
        assert chat_obj.user_input == user_input
        assert chat_obj.train == train

    @pytest.mark.asyncio
    async def test_chat_object_run_flow(self):
        """Test ChatObject run flow"""
        session_id = "test-session-456"
        sm = SessionsManager()
        sm.init_session(session_id)

        train = {"role": "system", "content": "system message"}
        user_input = "test input"
        context = MemoryModel()

        # Create a Mock configuration to avoid actual LLM calls
        config = AmritaConfig()
        config.llm.enable_tokens_limit = False
        config.llm.enable_memory_abstract = False

        # Create a default preset to avoid the random choice error
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=context,
            session_id=session_id,
            config=config,
            preset=default_preset,  # Pass a preset to avoid the error
        )

        # Test if it can start running
        chat_obj.begin()
        assert chat_obj.is_running() or not chat_obj.is_done()

        # Terminate object
        chat_obj.terminate()

    @pytest.mark.asyncio
    async def test_response_generator(self):
        """Test response generator"""
        session_id = "test-session-789"
        sm = SessionsManager()
        sm.init_session(session_id)

        train = {"role": "system", "content": "system message"}
        user_input = "test input"
        context = MemoryModel()

        config = AmritaConfig()
        config.llm.enable_tokens_limit = False

        # Create a default preset to avoid the random choice error
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=context,
            session_id=session_id,
            config=config,
            preset=default_preset,  # Pass a preset to avoid the error
        )

        # Add some mock responses to queue
        await chat_obj._put_to_queue("Hello")
        await chat_obj._put_to_queue("World")
        await chat_obj.set_queue_done()

        # Get response generator and verify
        gen = chat_obj.get_response_generator()
        responses = [resp async for resp in gen]

        assert len(responses) == 2
        assert "Hello" in responses
        assert "World" in responses


class TestMemoryLimiter:
    """Test MemoryLimiter class functionality"""

    @pytest.mark.asyncio
    async def test_memory_limiter_initialization(self):
        """Test MemoryLimiter initialization"""
        memory = MemoryModel()
        train = {"role": "system", "content": "system prompt"}
        config = AmritaConfig()

        limiter = MemoryLimiter(memory, train, config)

        assert limiter.memory == memory
        assert limiter.config == config
        assert limiter._train == train

    @pytest.mark.asyncio
    async def test_memory_limiter_context_manager(self):
        """Test MemoryLimiter context manager"""
        memory = MemoryModel()
        train = {"role": "system", "content": "system prompt"}
        config = AmritaConfig()

        async with MemoryLimiter(memory, train, config) as lim:
            # Verify internal attributes are initialized after entering context manager
            assert hasattr(lim, "_dropped_messages")
            assert hasattr(lim, "_copied_messages")
            assert isinstance(lim._dropped_messages, list)
            assert lim._copied_messages == memory

    @pytest.mark.asyncio
    async def test_memory_length_limit(self):
        """Test memory length limit functionality"""
        # Create memory with multiple messages
        messages: list[CONTENT_LIST_TYPE_ITEM] = [
            Message(role="user", content=f"message {i}")
            for i in range(20)  # Create enough messages to trigger limit
        ]
        memory = MemoryModel(messages=messages)
        train = {"role": "system", "content": "system prompt"}

        # Set a small memory limit
        config = AmritaConfig()
        config.llm.memory_lenth_limit = 5  # Limit to max 5 messages

        async with MemoryLimiter(memory, train, config) as lim:
            await lim._limit_length()

            # Verify message count is limited to the configured limit
            assert len(lim.memory.messages) <= config.llm.memory_lenth_limit


class TestChatManager:
    """Test ChatManager class functionality"""

    def setup_method(self):
        """Clean up chat_manager state before each test method"""
        chat_manager.running_chat_object.clear()
        chat_manager.running_chat_object_id2map.clear()

    @pytest.mark.asyncio
    async def test_add_and_get_chat_objects(self):
        """Test add and get chat objects"""
        session_id = "test-session-add-get"
        sm = SessionsManager()
        sm.init_session(session_id)

        train = {"role": "system", "content": "system message"}
        user_input = "test input"
        context = MemoryModel()

        # Create a default preset to avoid the random choice error
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        # Create chat object
        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=context,
            session_id=session_id,
            preset=default_preset,  # Pass a preset to avoid the error
        )

        # Add to manager
        await chat_manager.add_chat_object(chat_obj)

        # Verify object is added
        objs = chat_manager.get_objs(session_id)
        assert len(objs) == 1
        assert objs[0] == chat_obj

    @pytest.mark.asyncio
    async def test_get_all_objs(self):
        """Test get all objects metadata"""
        session_id = "test-session-all-objs"
        sm = SessionsManager()
        sm.init_session(session_id)

        train = {"role": "system", "content": "system message"}
        user_input = "test input"
        context = MemoryModel()

        # Create a default preset to avoid the random choice error
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        # Create and add chat object
        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=context,
            session_id=session_id,
            preset=default_preset,  # Pass a preset to avoid the error
        )

        await chat_manager.add_chat_object(chat_obj)

        # Get all object metadata
        all_objs = chat_manager.get_all_objs()

        # Verify at least one object metadata exists
        assert len(all_objs) >= 1
        assert chat_obj.stream_id in [meta.stream_id for meta in all_objs]

    @pytest.mark.asyncio
    async def test_clean_chat_objects(self):
        """Test clean all chat objects"""
        session_id = "test-session-clean-all"
        sm = SessionsManager()
        sm.init_session(session_id)

        # Add multiple objects
        for i in range(3):
            train = {"role": "system", "content": f"system message {i}"}
            user_input = f"test input {i}"
            context = MemoryModel()

            # Create a default preset to avoid the random choice error
            default_preset = ModelPreset(
                model="gpt-3.5-turbo", name=f"test-{i}", api_key="fake-key"
            )

            chat_obj = ChatObject(
                train=train,
                user_input=user_input,
                context=context,
                session_id=session_id,
                preset=default_preset,  # Pass a preset to avoid the error
            )
            chat_obj.terminate()

            await chat_manager.add_chat_object(chat_obj)

        # Clean all chat objects
        await chat_manager.clean_chat_objects(maxitems=2)

        # Verify object count is limited
        objs = chat_manager.get_objs(session_id)
        assert len(objs) <= 2


@pytest.mark.asyncio
async def test_concurrent_chat_objects():
    """Test concurrent chat objects"""
    sm = SessionsManager()

    # Create multiple sessions
    session_ids = []
    for i in range(3):
        session_id = sm.new_session()
        session_ids.append(session_id)

    # Concurrently create multiple chat objects
    async def create_chat_obj(session_id):
        train = {"role": "system", "content": f"system message for {session_id}"}
        user_input = f"test input for {session_id}"
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
        )

        await chat_manager.add_chat_object(chat_obj)
        return chat_obj

    # Concurrently create chat objects
    chat_objects = await asyncio.gather(*[create_chat_obj(sid) for sid in session_ids])

    # Verify all objects are created and added
    for i, sid in enumerate(session_ids):
        objs = chat_manager.get_objs(sid)
        assert len(objs) >= 1

        # Check if corresponding chat object exists
        assert any(obj.session_id == sid for obj in objs)

    # Clean up all objects
    for obj in chat_objects:
        obj.terminate()
