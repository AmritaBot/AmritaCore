from amrita_core.chatmanager import ChatObject
from amrita_core.config import AmritaConfig
from amrita_core.sessions import SessionsManager
from amrita_core.types import (
    MemoryModel,
    ModelPreset,
)


def test_chatobject_uses_session_memory_config_and_default_preset():
    """
    Building a ChatObject with context=None and no config/preset should cause it
    to use the session's memory, config, and default preset.
    """
    session_id = "session-defaults-test"

    # Prepare session-backed memory/config/preset
    session_memory = MemoryModel()
    session_config = AmritaConfig()
    default_preset = ModelPreset(
        model="gpt-3.5-turbo",
        name="session-default",
        api_key="fake-key",
    )

    # this follows the same conventions as the rest of the test suite.
    sessions_manager = SessionsManager()
    sessions_manager.init_session(session_id)
    data = sessions_manager.get_session_data(session_id)
    data.config = session_config
    data.memory = session_memory
    data.presets.set_default_preset(default_preset)

    # No explicit context/config/preset passed in – ChatObject should derive
    # these from the session.
    train = {"role": "system", "content": "system message"}
    user_input = "hello from user"

    chat_obj = ChatObject(
        train=train,
        user_input=user_input,
        context=None,
        session_id=session_id,
        config=None,
        preset=None,
    )

    # ChatObject should be using the session's memory/config/preset
    assert (
        chat_obj.data is session_memory
        or getattr(chat_obj, "memory", None) is session_memory
    )
    assert getattr(chat_obj, "config", None) is session_config
    assert getattr(chat_obj, "preset", None) == default_preset


def test_chatobject_auto_create_session_for_unknown_session_id():
    """
    When auto_create_session=True and the session_id is not registered, the
    ChatObject should trigger session creation and wire itself to that session.
    """
    session_id = "auto-create-session-test"

    # Start with a fresh SessionsManager that does not know about this session_id.
    sessions_manager = SessionsManager()

    train = {"role": "system", "content": "system message"}
    user_input = "hello auto create"
    default_preset = ModelPreset(
        model="gpt-3.5-turbo",
        name="session-default",
        api_key="fake-key",
    )

    # No context/config/preset, unknown session_id, but auto_create_session=True.
    chat_obj = ChatObject(
        train=train,
        user_input=user_input,
        context=None,
        session_id=session_id,
        config=None,
        preset=default_preset,
        auto_create_session=True,
    )

    # The session should have been created
    session = sessions_manager.get_session_data(session_id)
    assert session is not None

    # ChatObject should be wired to the session's memory (and config/preset if present)
    assert isinstance(chat_obj.data, MemoryModel) or isinstance(
        getattr(chat_obj, "memory", None), MemoryModel
    )

    # If the session exposes config/preset defaults, verify ChatObject picked them up.
    session_config = getattr(session, "config", None)
    if session_config is not None:
        assert getattr(chat_obj, "config", None) is session_config
