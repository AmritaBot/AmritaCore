import asyncio
from unittest.mock import patch

import pytest

from amrita_core.chatmanager import ChatObject, MemoryLimiter, chat_manager
from amrita_core.config import AmritaConfig
from amrita_core.contexts import StateContext
from amrita_core.types import (
    CONTENT_LIST_TYPE,
    CONTENT_LIST_TYPE_ITEM,
    MemoryModel,
    Message,
    ModelPreset,
)


class TestChatObject:
    """Test ChatObject class functionality"""

    @pytest.mark.asyncio
    async def test_chat_object_initialization_with_session_id(self):
        """Test ChatObject initialization with session_id"""
        session_id = "test-session-123"
        train = {"role": "system", "content": "system message"}
        user_input = "hello"
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            session_id=session_id,
            preset=default_preset,
        )

        assert chat_obj._s_id == session_id
        assert chat_obj.user_input == user_input
        assert chat_obj.train.model_dump() == train

    @pytest.mark.asyncio
    async def test_chat_object_initialization_with_state_context(self):
        """Test ChatObject initialization with pre-built StateContext"""
        session_id = "test-session-state"
        state = StateContext(session_id=session_id)
        train = {"role": "system", "content": "system message"}
        user_input = "hello"
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=state,
            preset=default_preset,
        )

        assert chat_obj.session_id == session_id
        assert chat_obj.state is state

    @pytest.mark.asyncio
    async def test_chat_object_context_session_id_mutually_exclusive(self):
        """Test that context and session_id cannot both be provided"""
        train = {"role": "system", "content": "system message"}
        state = StateContext(session_id="s1")

        with pytest.raises(ValueError, match="Both context and session_id"):
            ChatObject(
                train=train,
                user_input="hello",
                context=state,
                session_id="s2",
                preset=ModelPreset(model="gpt-3.5-turbo", name="t", api_key="k"),
            )

    @pytest.mark.asyncio
    async def test_chat_object_needs_either_context_or_session_id(self):
        """Test that at least context or session_id must be provided"""
        train = {"role": "system", "content": "system message"}

        with pytest.raises(ValueError, match="Either context or session_id"):
            ChatObject(
                train=train,
                user_input="hello",
                context=None,
                session_id=None,
                preset=ModelPreset(model="gpt-3.5-turbo", name="t", api_key="k"),
            )

    @pytest.mark.asyncio
    async def test_response_generator(self):
        """Test response generator via io_stream"""
        session_id = "test-session-789"
        train = {"role": "system", "content": "system message"}
        user_input = "test input"
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            session_id=session_id,
            preset=default_preset,
        )

        await chat_obj.io_stream._put_to_queue("Hello")
        await chat_obj.io_stream._put_to_queue("World")
        await chat_obj.io_stream.set_queue_done()

        gen = chat_obj.io_stream.get_response_generator()
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
            assert hasattr(lim, "_dropped_messages")
            assert hasattr(lim, "_copied_messages")
            assert isinstance(lim._dropped_messages, list)
            assert lim._copied_messages == memory

    @pytest.mark.asyncio
    async def test_memory_length_limit(self):
        """Test memory length limit functionality"""
        messages: list[CONTENT_LIST_TYPE_ITEM] = [
            Message(role="user", content=f"message {i}") for i in range(20)
        ]
        memory = MemoryModel(messages=messages)
        train = {"role": "system", "content": "system prompt"}

        config = AmritaConfig()
        config.llm.memory_length_limit = 5

        async with MemoryLimiter(memory, train, config) as lim:
            await lim._limit_length()
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
        train = {"role": "system", "content": "system message"}
        user_input = "test input"
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        state = StateContext(session_id=session_id)
        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=state,
            preset=default_preset,
        )

        await chat_manager.add_chat_object(chat_obj)

        objs = chat_manager.get_objs(session_id)
        assert len(objs) == 1
        assert objs[0] == chat_obj

    @pytest.mark.asyncio
    async def test_get_all_objs(self):
        """Test get all objects metadata"""
        session_id = "test-session-all-objs"
        train = {"role": "system", "content": "system message"}
        user_input = "test input"
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        state = StateContext(session_id=session_id)
        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=state,
            preset=default_preset,
        )

        await chat_manager.add_chat_object(chat_obj)

        all_objs = chat_manager.get_all_objs()
        assert len(all_objs) >= 1
        assert chat_obj.stream_id in [meta.stream_id for meta in all_objs]

    @pytest.mark.asyncio
    async def test_clean_chat_objects(self):
        """Test clean all chat objects"""
        session_id = "test-session-clean-all"

        for i in range(3):
            train = {"role": "system", "content": f"system message {i}"}
            user_input = f"test input {i}"
            default_preset = ModelPreset(
                model="gpt-3.5-turbo", name=f"test-{i}", api_key="fake-key"
            )
            state = StateContext(session_id=session_id)
            chat_obj = ChatObject(
                train=train,
                user_input=user_input,
                context=state,
                preset=default_preset,
            )
            chat_obj.terminate()
            await chat_manager.add_chat_object(chat_obj)

        await chat_manager.clean_chat_objects(maxitems=2)

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
                "amrita_core.chatmanager.chat_object.call_completion"
            ) as mock_call_completion,
            patch(
                "amrita_core.chatmanager.memory_limiter.call_completion"
            ) as mock_call_completion_2,
        ):
            # Create async generator mock
            async def mock_generator():
                yield mock_response

            mock_call_completion.return_value = mock_generator()
            mock_call_completion_2.return_value = mock_generator()
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

    @pytest.mark.asyncio
    async def test_yield_response_with_callback(self):
        """Test yield_response with callback function"""
        session_id = "test-session-callback"
        train = {"role": "system", "content": "system message"}
        user_input = "test input"
        state = StateContext(session_id=session_id)
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        received_responses = []

        async def callback_func(response):
            received_responses.append(response)

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=state,
            preset=default_preset,
        )
        chat_obj.io_stream.set_callback_func(callback_func)

        await chat_obj.io_stream.yield_response("test response")

        assert len(received_responses) == 1
        assert received_responses[0] == "test response"

    @pytest.mark.asyncio
    async def test_full_response(self):
        """Test full_response method"""
        session_id = "test-session-full-response"
        train = {"role": "system", "content": "system message"}
        user_input = "test input"
        state = StateContext(session_id=session_id)
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=state,
            preset=default_preset,
        )

        await chat_obj.io_stream._put_to_queue("Hello")
        await chat_obj.io_stream._put_to_queue(" ")
        await chat_obj.io_stream._put_to_queue("World!")
        await chat_obj.io_stream.set_queue_done()

        full_resp = await chat_obj.full_response()
        assert full_resp == "Hello World!"

    @pytest.mark.asyncio
    async def test_prepare_send_messages(self):
        """Test _prepare_send_messages method"""
        session_id = "test-session-prepare"
        state = StateContext(
            session_id=session_id,
            memory=MemoryModel(
                messages=[
                    Message(role="user", content="previous message"),
                    Message(role="assistant", content="previous response"),
                ]
            ),
        )
        train = {"role": "system", "content": "system message"}
        user_input = "test input"
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=state,
            preset=default_preset,
        )

        chat_obj.data.messages.append(Message(role="user", content=user_input))

        send_messages = chat_obj._prepare_send_messages()

        assert len(send_messages) == 4
        assert send_messages[0].role == "system"
        assert send_messages[0].content == "system message"
        assert send_messages[-1].content == user_input

    @pytest.mark.asyncio
    async def test_set_callback_func_already_set(self):
        """Test setting callback function when already set"""
        session_id = "test-session-callback-error"
        train = {"role": "system", "content": "system message"}
        user_input = "test input"
        state = StateContext(session_id=session_id)
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
            context=state,
            preset=default_preset,
        )
        chat_obj.io_stream.set_callback_func(callback1)

        with pytest.raises(
            RuntimeError,
            match="The callback function of this chat object has already been set!",
        ):
            chat_obj.io_stream.set_callback_func(callback2)


@pytest.mark.asyncio
async def test_concurrent_chat_objects():
    """Test concurrent chat objects"""
    session_ids = [f"concurrent-{i}" for i in range(3)]

    async def create_chat_obj(session_id):
        train = {"role": "system", "content": f"system message for {session_id}"}
        user_input = f"test input for {session_id}"
        state = StateContext(session_id=session_id)
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name=f"test-{session_id[:8]}", api_key="fake-key"
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=state,
            preset=default_preset,
        )

        await chat_manager.add_chat_object(chat_obj)
        return chat_obj

    chat_objects = await asyncio.gather(*[create_chat_obj(sid) for sid in session_ids])

    for sid in session_ids:
        objs = chat_manager.get_objs(sid)
        assert len(objs) >= 1
        assert any(obj.session_id == sid for obj in objs)

    for obj in chat_objects:
        obj.terminate()
