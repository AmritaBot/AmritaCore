import asyncio

import pytest

from amrita_core.config import AmritaConfig
from amrita_core.sessions import SessionsManager


class TestSessionsManager:
    """Test SessionsManager class functionality"""

    def setup_method(self):
        """Reset SessionsManager singleton before each test method"""
        # Clear SessionsManager internal state
        SessionsManager._instance = None

    def test_singleton_pattern(self):
        """Test singleton pattern"""
        manager1 = SessionsManager()
        manager2 = SessionsManager()

        assert manager1 is manager2
        assert SessionsManager._instance is manager1

    def test_new_session_creation(self):
        """Test new session creation functionality"""
        manager = SessionsManager()

        # Create new session
        session_id = manager.new_session()

        # Verify session is registered
        assert manager.is_session_registered(session_id)
        assert session_id in [
            data.session_id for data in manager.get_registered_sessions().values()
        ]

        # Verify session resources are initialized
        session_data = manager.get_session_data(session_id)
        assert session_data.tools is not None
        assert session_data.config is not None
        assert session_data.presets is not None

    def test_session_config_operations(self):
        """Test session configuration operations"""
        manager = SessionsManager()

        # Create session
        session_id = manager.new_session()

        # Get initial configuration
        session_data = manager.get_session_data(session_id)
        initial_config = session_data.config
        assert isinstance(initial_config, AmritaConfig)

        # Set new configuration with a valid field
        new_config = AmritaConfig()
        new_config.llm.max_retries = 5  # Using a valid field from LLMConfig
        session_data.config = new_config

        # Verify configuration is updated
        updated_config = manager.get_session_data(session_id).config
        assert updated_config.llm.max_retries == 5

    def test_safe_getters(self):
        """Test safe getters"""
        manager = SessionsManager()

        # Try to get non-existent session
        non_existent_session = "non-existent-session-id"
        try:
            manager.get_session_data(non_existent_session)
            pytest.fail("Expected KeyError was not raised")
        except KeyError:
            pass  # Expected behavior

        # Create session and verify safe getters
        session_id = manager.new_session()
        session_data = manager.get_session_data(session_id)
        assert session_data.config is not None
        assert session_data.tools is not None
        assert session_data.memory is not None

    def test_session_drop(self):
        """Test session drop functionality"""
        manager = SessionsManager()

        # Create session
        session_id = manager.new_session()
        assert manager.is_session_registered(session_id)

        # Drop session
        manager.drop_session(session_id)

        # Verify session is removed
        assert not manager.is_session_registered(session_id)
        assert session_id not in [
            data.session_id for data in manager.get_registered_sessions().values()
        ]

    def test_multiple_sessions(self):
        """Test multiple sessions"""
        manager = SessionsManager()

        # Create multiple sessions
        session_ids = [manager.new_session() for _ in range(3)]

        # Verify all sessions are registered
        for sid in session_ids:
            assert manager.is_session_registered(sid)

        # Verify session count
        assert len(manager.get_registered_sessions()) == 3

        # Set different configurations for each session
        for i, sid in enumerate(session_ids):
            session_data = manager.get_session_data(sid)
            new_config = AmritaConfig()
            new_config.llm.max_retries = 3 + i  # Using a valid field from LLMConfig
            session_data.config = new_config

        # Verify each session has different configuration
        for i, sid in enumerate(session_ids):
            session_data = manager.get_session_data(sid)
            config = session_data.config
            assert config.llm.max_retries == 3 + i

    def test_session_presets(self):
        """Test session presets functionality"""
        manager = SessionsManager()

        # Create session
        session_id = manager.new_session()

        # Verify presets manager exists
        session_data = manager.get_session_data(session_id)
        presets = session_data.presets
        assert presets is not None  # Presets manager is created by default

    def test_session_memory(self):
        """Test session memory functionality"""
        manager = SessionsManager()

        # Create session
        session_id = manager.new_session()

        # Verify memory model exists
        session_data = manager.get_session_data(session_id)
        memory = session_data.memory
        assert memory is not None
        assert hasattr(memory, "messages")
        assert hasattr(memory, "abstract")


@pytest.mark.asyncio
async def test_async_session_operations():
    """Async session operations test"""
    # Simulate async operation
    await asyncio.sleep(0.01)

    manager = SessionsManager()
    session_id = manager.new_session()

    # Simulate operations during async wait
    await asyncio.sleep(0.01)

    # Verify session still exists
    assert manager.is_session_registered(session_id)
