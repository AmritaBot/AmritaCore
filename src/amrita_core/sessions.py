from __future__ import annotations

import contextlib
import uuid
from dataclasses import dataclass
from typing import TypeVar, overload

from typing_extensions import Self

from amrita_core.config import AmritaConfig
from amrita_core.preset import MultiPresetManager
from amrita_core.tools.mcp import MultiClientManager as ClientManager
from amrita_core.types import MemoryModel

from .tools.manager import MultiToolsManager

T = TypeVar("T")


@dataclass
class SessionData:
    """Container for all session-specific data.

    Attributes:
        session_id: Unique identifier for the session
        memory: Memory model storing conversation history
        tools: Manager for tools available in the session
        presets: Manager for model presets in the session
        mcp: Client manager for MCP (Model Context Protocol) connections
        config: Configuration settings for the session
    """

    session_id: str
    memory: MemoryModel
    tools: MultiToolsManager
    presets: MultiPresetManager
    mcp: ClientManager
    config: AmritaConfig


class SessionsManager:
    """Session manager for managing tools, configurations, and presets for different sessions.

    This manager uses singleton pattern to ensure only one instance exists throughout the application,
    tracking all registered sessions and their associated tools, configurations, and preset managers.
    """

    _session2DataMap: dict[str, SessionData]
    _instance = None
    __marker = object()

    def __new__(cls) -> Self:
        """Implement singleton pattern, create new instance if none exists, otherwise return existing"""
        if cls._instance is None:
            cls._session2DataMap = {}
            cls._instance = super().__new__(cls)
        return cls._instance

    def is_session_registered(self, session_id: str) -> bool:
        """Check if a session is registered.

        Args:
            session_id: The unique identifier for the session

        Returns:
            True if the session is registered, False otherwise
        """
        return session_id in self._session2DataMap

    def get_registered_sessions(self) -> dict[str, SessionData]:
        """
        Get all registered sessions.

        Returns:
            dict[str, SessionData]: A copy of the registered sessions mapping to prevent external modification
        """
        return self._session2DataMap.copy()

    def init_session(self, session_id: str):
        """Initialize resources for a given session.

        Args:
            session_id (str): The unique identifier for the session
        """
        if session_id not in self._session2DataMap:
            self._session2DataMap[session_id] = SessionData(
                session_id,
                MemoryModel(),
                MultiToolsManager(),
                MultiPresetManager(),
                ClientManager(),
                config=AmritaConfig(),
            )

    def set_session(self, data: SessionData):
        """
        Set the session data for a given session ID

        Args:
            data (SessionData): The session data to set
        """
        self._session2DataMap[data.session_id] = data

    @overload
    def get_session_data(self, session_id: str, default: T) -> SessionData | T: ...
    @overload
    def get_session_data(self, session_id: str) -> SessionData: ...
    def get_session_data(
        self, session_id: str, default: T = __marker
    ) -> SessionData | T:
        """Get the session data for a given session ID.

        Args:
            session_id: The unique identifier for the session
            default: Default value to return if session is not found (optional)

        Returns:
            SessionData if session exists, or default value if provided

        Raises:
            KeyError: If session is not found and no default is provided
        """
        if session_id in self._session2DataMap:
            return self._session2DataMap[session_id]
        elif default is not self.__marker:
            return default
        else:
            raise KeyError(f"Session {session_id} not found")

    def new_session(self) -> str:
        """Create a new session with a unique ID and initialize its resources.

        Returns:
            str: The unique identifier for the newly created session
        """
        session_id = uuid.uuid4().hex
        self.init_session(session_id)
        return session_id

    def drop_session(self, session_id: str) -> None:
        """Remove a session and clean up its associated resources.

        Args:
            session_id: The unique identifier for the session to remove
        """
        self._session2DataMap.pop(session_id, None)
        from .chatmanager import chat_manager

        for obj in chat_manager.running_chat_object[session_id]:
            with contextlib.suppress(Exception):
                obj.terminate()
            chat_manager.running_chat_object_id2map.pop(obj.stream_id, None)
