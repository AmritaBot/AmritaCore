import asyncio
from unittest.mock import patch

import pytest

from amrita_core.chatmanager import ChatObject, MemoryLimiter, chat_manager
from amrita_core.config import AmritaConfig
from amrita_core.sessions import SessionsManager
from amrita_core.types import (
    CONTENT_LIST_TYPE,
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
        assert chat_obj.train.model_dump() == train

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
        train = {
            "content": "system prompt",
            "role": "system",
        }
        config = AmritaConfig()

        limiter = MemoryLimiter(memory, train, config)

        assert limiter.memory == memory
        assert limiter.config == config
        assert limiter._train.model_dump() == train

    @pytest.mark.asyncio
    async def test_memory_limiter_context_manager(self):
        """Test MemoryLimiter context manager"""
        memory = MemoryModel()
        train = {
            "content": "system prompt",
            "role": "system",
        }
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
        config.llm.memory_length_limit = 5  # Limit to max 5 messages

        async with MemoryLimiter(memory, train, config) as lim:
            await lim._limit_length()

            # Verify message count is limited to the configured limit
            assert len(lim.memory.messages) <= config.llm.memory_length_limit


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


class TestMemoryLimiterAdvanced:
    """Test advanced MemoryLimiter functionality"""

    @pytest.mark.asyncio
    async def test_make_abstract_with_llm_call(self):
        """Test _make_abstract method with mocked LLM call"""
        from amrita_core.types import UniResponse, UniResponseUsage

        messages: CONTENT_LIST_TYPE = [
            Message(role="user", content=f"Message {i}") for i in range(10)
        ]
        memory = MemoryModel(messages=messages)
        train = {"role": "system", "content": "system prompt"}
        config = AmritaConfig()
        config.llm.memory_abstract_proportion = 0.5  # Abstract first 50% of messages

        # Mock the LLM calls
        mock_response = UniResponse(
            content="This is a summary of the dropped messages",
            tool_calls=[],
            usage=UniResponseUsage(
                prompt_tokens=10, completion_tokens=5, total_tokens=15
            ),
        )

        with (
            patch(
                "amrita_core.chatmanager.get_last_response", return_value=mock_response
            ),
            patch("amrita_core.chatmanager.call_completion") as mock_call_completion,
        ):
            # Create async generator mock
            async def mock_generator():
                yield mock_response

            mock_call_completion.return_value = mock_generator()

            async with MemoryLimiter(memory, train, config) as lim:
                # Manually add some dropped messages
                lim._dropped_messages = messages[:5]  # First 5 messages
                await lim._make_abstract()

                # Should have set abstract content and usage
                assert (
                    lim.memory.abstract == "This is a summary of the dropped messages"
                )
                assert lim.usage is not None
                assert lim.usage.completion_tokens == 5

    @pytest.mark.asyncio
    async def test_make_abstract_no_dropped_messages(self):
        """Test _make_abstract when no messages are dropped"""
        memory = MemoryModel()
        train = {"role": "system", "content": "system prompt"}
        config = AmritaConfig()

        async with MemoryLimiter(memory, train, config) as lim:
            lim._dropped_messages = []  # No dropped messages
            await lim._make_abstract()

            # Should not change abstract (remains None/empty)
            assert lim.memory.abstract == ""

    @pytest.mark.asyncio
    async def test_drop_message_with_tool_messages(self):
        """Test dropping messages including tool messages"""
        from amrita_core.types import ToolResult

        # Create messages where the first message is followed by tool messages
        messages = [
            Message(role="user", content="First message"),
            ToolResult(
                role="tool", content="Tool result 1", tool_call_id="1", name="test1"
            ),
            ToolResult(
                role="tool", content="Tool result 2", tool_call_id="2", name="test2"
            ),
            Message(role="user", content="Second message"),
            Message(role="assistant", content="Final response"),
        ]
        memory = MemoryModel(messages=messages)
        train = {"role": "system", "content": "system prompt"}
        config = AmritaConfig()

        limiter = MemoryLimiter(memory, train, config)
        limiter._dropped_messages = []

        # Drop first message and associated tool messages
        limiter._drop_message()

        # Should have dropped the first user message and both tool results
        assert len(limiter._dropped_messages) == 3
        assert (
            len(limiter.memory.messages) == 2
        )  # Remaining: second user message and final response

    @pytest.mark.asyncio
    async def test_limit_tokens_exceeds_window(self):
        """Test token limitation when exceeding window size"""
        messages: CONTENT_LIST_TYPE = [
            Message(
                role="user",
                content="This is a very long message that will exceed token limits "
                * 20,
            ),
            Message(role="assistant", content="Response"),
        ]
        memory = MemoryModel(messages=messages)
        train = {"role": "system", "content": "Short system prompt"}
        config = AmritaConfig()
        config.llm.enable_tokens_limit = True
        config.llm.session_tokens_windows = 50  # Very small window

        async with MemoryLimiter(memory, train, config) as lim:
            await lim._limit_tokens()

            # Should have removed messages to fit within token window
            assert len(lim.memory.messages) <= len(messages)

    @pytest.mark.asyncio
    async def test_run_enforce_without_context_manager(self):
        """Test run_enforce without proper context manager initialization"""
        memory = MemoryModel()
        train = {"role": "system", "content": "system prompt"}
        config = AmritaConfig()

        limiter = MemoryLimiter(memory, train, config)

        with pytest.raises(RuntimeError, match="MemoryLimiter is not initialized"):
            await limiter.run_enforce()

    @pytest.mark.asyncio
    async def test_aexit_with_exception(self):
        """Test context manager exit with exception - should rollback messages"""
        original_messages: CONTENT_LIST_TYPE = [
            Message(role="user", content="Original message 1"),
            Message(role="user", content="Original message 2"),
        ]
        memory = MemoryModel(messages=original_messages.copy())
        train = {"role": "system", "content": "system prompt"}
        config = AmritaConfig()

        try:
            async with MemoryLimiter(memory, train, config) as lim:
                # Modify messages
                lim.memory.messages.append(Message(role="user", content="New message"))
                # Simulate an exception
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Messages should be rolled back to original state
        assert len(memory.messages) == len(original_messages)
        assert memory.messages == original_messages


class TestChatObjectAdvanced:
    """Test advanced ChatObject functionality"""

    def setup_method(self):
        """Clean up state before each test method"""
        SessionsManager._instance = None

    @pytest.mark.asyncio
    async def test_put_to_queue_overflow(self):
        """Test putting items to queue with overflow mechanism"""
        session_id = "test-session-overflow"
        sm = SessionsManager()
        sm.init_session(session_id)

        train = {"role": "system", "content": "system message"}
        user_input = "test input"
        context = MemoryModel()

        config = AmritaConfig()
        # Small queue sizes to trigger overflow
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=context,
            session_id=session_id,
            config=config,
            preset=default_preset,
            queue_size=2,  # Very small primary queue
            overflow_queue_size=2,  # Very small overflow queue
        )

        # Fill both queues
        await chat_obj._put_to_queue("item1")
        await chat_obj._put_to_queue("item2")
        await chat_obj._put_to_queue("item3")  # Should go to overflow
        await chat_obj._put_to_queue("item4")  # Should go to overflow

        # Try to add one more item - should wait and eventually raise exception after timeout
        with pytest.raises(
            RuntimeError,
            match="Both primary and overflow queues are full after waiting",
        ):
            await chat_obj._put_to_queue("item5")

    @pytest.mark.asyncio
    async def test_yield_response_with_callback(self):
        """Test yield_response with callback function"""
        session_id = "test-session-callback"
        sm = SessionsManager()
        sm.init_session(session_id)

        train = {"role": "system", "content": "system message"}
        user_input = "test input"
        context = MemoryModel()

        config = AmritaConfig()
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        received_responses = []

        async def callback_func(response):
            received_responses.append(response)

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=context,
            session_id=session_id,
            config=config,
            preset=default_preset,
            callback=callback_func,
        )

        await chat_obj.yield_response("test response")

        assert len(received_responses) == 1
        assert received_responses[0] == "test response"

    @pytest.mark.asyncio
    async def test_full_response(self):
        """Test full_response method"""
        session_id = "test-session-full-response"
        sm = SessionsManager()
        sm.init_session(session_id)

        train = {"role": "system", "content": "system message"}
        user_input = "test input"
        context = MemoryModel()

        config = AmritaConfig()
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=context,
            session_id=session_id,
            config=config,
            preset=default_preset,
        )

        await chat_obj._put_to_queue("Hello")
        await chat_obj._put_to_queue(" ")
        await chat_obj._put_to_queue("World!")
        await chat_obj.set_queue_done()

        full_resp = await chat_obj.full_response()
        assert full_resp == "Hello World!"

    @pytest.mark.asyncio
    async def test_prepare_send_messages(self):
        """Test _prepare_send_messages method"""
        session_id = "test-session-prepare"
        sm = SessionsManager()
        sm.init_session(session_id)

        train = {"role": "system", "content": "system message"}
        user_input = "test input"
        context = MemoryModel(
            messages=[
                Message(role="user", content="previous message"),
                Message(role="assistant", content="previous response"),
            ]
        )

        config = AmritaConfig()
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=context,
            session_id=session_id,
            config=config,
            preset=default_preset,
        )

        # Add user message to context
        chat_obj.data.messages.append(Message(role="user", content=user_input))

        send_messages = chat_obj._prepare_send_messages()

        assert (
            len(send_messages) == 4
        )  # system + previous user + previous assistant + current user
        assert send_messages[0].role == "system"
        assert send_messages[0].content == "system message"
        assert send_messages[-1].content == user_input

    @pytest.mark.asyncio
    async def test_set_callback_func_already_set(self):
        """Test setting callback function when already set"""
        session_id = "test-session-callback-error"
        sm = SessionsManager()
        sm.init_session(session_id)

        train = {"role": "system", "content": "system message"}
        user_input = "test input"
        context = MemoryModel()

        config = AmritaConfig()
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        async def callback1(response):
            pass

        async def callback2(response):
            pass

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=context,
            session_id=session_id,
            config=config,
            preset=default_preset,
            callback=callback1,
        )

        with pytest.raises(
            RuntimeError,
            match="The callback function of this chat object has already been set!",
        ):
            chat_obj.set_callback_func(callback2)


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
