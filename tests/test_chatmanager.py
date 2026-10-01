import asyncio

import pytest
from amrita_sense import StreamStateError

from amrita_core.chatmanager import ChatObject, chat_manager
from amrita_core.types import (
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
    async def test_chat_object_requires_session_id(self):
        """Test that session_id must be provided"""
        train = {"role": "system", "content": "system message"}

        with pytest.raises(ValueError, match="session_id must be provided"):
            ChatObject(
                train=train,
                user_input="hello",
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

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            session_id=session_id,
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

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            session_id=session_id,
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
            chat_obj = ChatObject(
                train=train,
                user_input=user_input,
                session_id=session_id,
                preset=default_preset,
            )
            chat_obj.terminate()
            await chat_manager.add_chat_object(chat_obj)

        await chat_manager.clean_chat_objects(maxitems=2)

        objs = chat_manager.get_objs(session_id)
        assert len(objs) <= 2


class TestChatObjectAdvanced:
    """Test advanced ChatObject functionality"""

    @pytest.mark.asyncio
    async def test_yield_response_with_callback(self):
        """Test yield_response with callback function"""
        session_id = "test-session-callback"
        train = {"role": "system", "content": "system message"}
        user_input = "test input"
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="test-default", api_key="fake-key"
        )

        received_responses = []

        async def callback_func(response):
            received_responses.append(response)

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            session_id=session_id,
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
        await chat_obj.io_stream._put_to_queue(" ")
        await chat_obj.io_stream._put_to_queue("World!")
        await chat_obj.io_stream.set_queue_done()

        full_resp = await chat_obj.full_response()
        assert full_resp == "Hello World!"

    @pytest.mark.asyncio
    async def test_prepare_send_messages(self):
        """Test _prepare_send_messages method"""
        session_id = "test-session-prepare"
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
        chat_obj.data = MemoryModel(
            messages=[
                Message(role="user", content="previous message"),
                Message(role="assistant", content="previous response"),
            ]
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
            session_id=session_id,
            preset=default_preset,
        )
        chat_obj.io_stream.set_callback_func(callback1)

        with pytest.raises(
            StreamStateError,
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
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name=f"test-{session_id[:8]}", api_key="fake-key"
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            session_id=session_id,
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
