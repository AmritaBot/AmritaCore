from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import aiologic

if TYPE_CHECKING:
    from .chat_obj_meta import ChatObjectMeta
    from .chat_object import ChatObject


@dataclass
class ChatManager:
    running_chat_object: defaultdict[str, list[ChatObject]] = field(
        default_factory=lambda: defaultdict(list)
    )
    running_chat_object_id2map: dict[str, ChatObjectMeta] = field(default_factory=dict)
    _lock: aiologic.Lock = field(default_factory=aiologic.Lock)

    def clean_obj(self, k: str, maxitems: int = 10) -> bool:
        """
        Clean up running chat objects under the specified key, keeping only the first 10 objects,
        removing any excess unfinished parts

        Args:
            k (tuple[int, bool]): Key value, composed of instance ID and whether it's group chat
            maxitems (int, optional): Maximum number of objects. Defaults to 10.

        Returns:
            bool: Whether the cleanup was successful
        """
        objs = self.running_chat_object[k]
        if len(objs) > maxitems:
            dropped_obj = objs[maxitems:]
            objs = [obj for obj in dropped_obj if not obj.is_done()] + objs[:maxitems]
            dropped_obj = [obj for obj in dropped_obj if obj.is_done()]
            for obj in dropped_obj:
                self.running_chat_object_id2map.pop(obj.stream_id, None)
            self.running_chat_object[k] = objs
            return True
        return False

    def get_all_objs(self) -> list[ChatObjectMeta]:
        """
        Get all running chat object metadata

        Returns:
            list[ChatObjectMeta]: List of all running chat object metadata
        """
        return list(self.running_chat_object_id2map.values())

    def get_objs(self, session_id: str) -> list[ChatObject]:
        """
        Get the corresponding list of chat objects based on the session ID

        Args:
            session_id (str): User session ID

        Returns:
            list[ChatObject]: List of chat objects
        """
        return self.running_chat_object[session_id]

    async def clean_chat_objects(self, maxitems: int = 10) -> None:
        """
        Asynchronously clean up all running chat objects, limiting the number of objects for each key to no more than 10
        """
        async with self._lock:
            for key in self.running_chat_object.keys():
                self.clean_obj(key, maxitems)

    async def add_chat_object(self, chat_object: ChatObject) -> None:
        """
        Add a new chat object to the running list

        Args:
            chat_object (ChatObject): Chat object instance
        """
        async with self._lock:
            meta = chat_object.get_snapshot()
            self.running_chat_object_id2map[chat_object.stream_id] = meta
            key = chat_object.session_id
            self.running_chat_object[key].insert(0, chat_object)
            self.clean_obj(key)


chat_manager = ChatManager()
