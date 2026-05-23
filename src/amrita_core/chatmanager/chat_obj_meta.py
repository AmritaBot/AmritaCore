from datetime import datetime

from pydantic import BaseModel, Field

from amrita_core.types import (
    ImageContent,
    TextContent,
)


class ChatObjectMeta(BaseModel):
    """Metadata model for chat object

    Used to store identification, events, and time information for the chat object.
    """

    stream_id: str  # Chat stream ID
    session_id: str  # Session ID
    user_input: list[TextContent | ImageContent] | str
    time: datetime = Field(default_factory=datetime.now)  # Creation time
    last_call: datetime = Field(default_factory=datetime.now)  # Last call time
