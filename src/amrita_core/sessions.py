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
        """Check if a session is registered"""
        return session_id in self._session2DataMap

    def get_registered_sessions(self) -> dict[str, SessionData]:
        """
        Get the registered sessions.

        Returns:
            dict[str, SessionData]: A copy of the registered session IDs to prevent external modification
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
            session_id (str): The unique identifier for the session
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
        if session_id in self._session2DataMap:
            return self._session2DataMap[session_id]
        elif default is not self.__marker:
            return default
        else:
            raise KeyError(f"Session {session_id} not found")

    def new_session(self) -> str:
        session_id = uuid.uuid4().hex
        self.init_session(session_id)
        return session_id

    def drop_session(self, session_id: str) -> None:
        self._session2DataMap.pop(session_id, None)
        from .chatmanager import chat_manager

        for obj in chat_manager.running_chat_object[session_id]:
            with contextlib.suppress(Exception):
                obj.terminate()
            chat_manager.running_chat_object_id2map.pop(obj.stream_id, None)
