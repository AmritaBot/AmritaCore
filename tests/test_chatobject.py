import pytest

from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.backends import LegacyBackend
from amrita_core.chatmanager import ChatObject
from amrita_core.contexts import StateContext
from amrita_core.types import ModelPreset


class TestChatObjectNewAPI:
    """Test ChatObject using the new Backend/StateContext API"""

    def test_chatobject_with_session_id_uses_backend(self):
        """
        ChatObject with session_id (no context) should use backend to load
        state lazily, and fall back to LegacyBackend defaults.
        """
        session_id = "backend-defaults-test"
        train = {"role": "system", "content": "system message"}
        user_input = "hello from user"
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="session-default", api_key="fake-key"
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            session_id=session_id,
            preset=default_preset,
        )

        assert chat_obj._s_id == session_id
        # Backend defaults to LegacyBackend
        assert isinstance(chat_obj.slot.ability, LegacyBackend)
        assert isinstance(chat_obj.slot.memory, LegacyBackend)
        # Preset should be set explicitly
        assert chat_obj.preset is default_preset

    def test_chatobject_with_state_context_uses_provided_state(self):
        """
        ChatObject with a pre-built StateContext uses it directly
        instead of loading state from a backend.
        """
        session_id = "state-context-test"
        state = StateContext(session_id=session_id)
        train = {"role": "system", "content": "system message"}
        user_input = "hello from state"
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="session-default", api_key="fake-key"
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            context=state,
            preset=default_preset,
        )

        assert chat_obj.state is state
        assert chat_obj.session_id == session_id
        # Session_id computed from state, not stored in _s_id
        assert not hasattr(chat_obj, "_s_id") or chat_obj._s_id is None

    def test_chatobject_with_custom_backend(self):
        """
        A custom BackendSlots should be used when explicitly provided.
        """
        session_id = "custom-backend-test"
        bkd = LegacyBackend()
        slot = BackendSlots(ability=bkd, memory=bkd)
        train = {"role": "system", "content": "system message"}
        user_input = "hello"
        default_preset = ModelPreset(
            model="gpt-3.5-turbo", name="session-default", api_key="fake-key"
        )

        chat_obj = ChatObject(
            train=train,
            user_input=user_input,
            session_id=session_id,
            preset=default_preset,
            backend=slot,
        )

        assert chat_obj.slot is slot
        assert chat_obj.slot.ability is bkd
        assert chat_obj.slot.memory is bkd

    def test_chatobject_context_and_session_id_mutually_exclusive(self):
        """Providing both context and session_id must raise ValueError."""
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

    def test_chatobject_requires_either_context_or_session_id(self):
        """Providing neither context nor session_id must raise ValueError."""
        train = {"role": "system", "content": "system message"}

        with pytest.raises(ValueError, match="Either context or session_id"):
            ChatObject(
                train=train,
                user_input="hello",
                context=None,
                session_id=None,
                preset=ModelPreset(model="gpt-3.5-turbo", name="t", api_key="k"),
            )
