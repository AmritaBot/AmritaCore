from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from jinja2 import Template

from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.agent import ReActAgentStrategy
from amrita_core.builtins.backends import LegacyBackend
from amrita_core.chatmanager import ChatObject
from amrita_core.config import get_config
from amrita_core.consts import DEFAULT_INSTRUCTIONS, DEFAULT_TEMPLATE
from amrita_core.types import USER_INPUT, Message, ModelConfig, ModelPreset

if TYPE_CHECKING:
    from amrita_core.config import AmritaConfig

    from .strategy import AgentStrategy


class AgentRuntime:
    """
    AgentRuntime is a high-level wrapper around ChatObject that provides a reusable
    agent operation interface.

    This class encapsulates the complexity of ChatObject and provides a simplified
    API for agent interactions. It maintains session state, configuration, and
    strategy settings, making it a reusable object for multiple agent operations
    within the same context.

    Session and memory management is delegated to the Backend mechanism
    (:class:`BackendSlots`), which handles memory loading, committing, and
    ability resolution transparently.  AgentRuntime itself only holds a
    ``session_id`` string and a ``slot`` reference — the actual state lives
    inside the Backend and is lazily resolved by :class:`ChatObject` at
    runtime.
    """

    strategy: type[AgentStrategy]
    session_id: str
    slot: BackendSlots
    preset: ModelPreset
    config: AmritaConfig
    train: Message[str]
    template: Template

    def __init__(
        self,
        config: AmritaConfig,
        preset: ModelPreset,
        train: dict[str, str] | Message[str],
        strategy: type[AgentStrategy] = ReActAgentStrategy,
        template: Template | str = DEFAULT_TEMPLATE,
        session_id: str | None = None,
        backend: BackendSlots | None = None,
    ):
        """
        Initialize an AgentRuntime instance.

        Args:
            config: Amrita configuration object containing global configuration settings.
            preset: Model preset configuration defining basic model parameters and settings.
            train: System prompt for the agent (dict or Message).
            strategy: Agent strategy class, defaults to ReActAgentStrategy.
            template: Jinja2 template (or template string) used to render the system prompt.
            session_id: Session identifier string. If None, a new UUID-based ID is generated.
                The session_id is passed to every ChatObject created by this runtime,
                allowing the Backend to isolate memory and abilities per session.
            backend: Backend slots providing memory and ability backends. If None, a
                :class:`LegacyBackend` is used for both slots, which stores data in
                global in-process containers.
        """
        self.session_id = session_id or uuid4().hex
        bkd = LegacyBackend()
        self.slot = backend or BackendSlots(bkd, bkd)
        self.template = Template(template) if isinstance(template, str) else template
        self.strategy = strategy
        self.preset = preset
        self.config = config
        self.train = (
            train if isinstance(train, Message) else Message[str].model_validate(train)
        )

    def set_strategy(self, strategy: type[AgentStrategy]) -> None:
        """
        Set the agent strategy to be used for execution.

        Args:
            strategy: The agent strategy class to be used for execution.
        """
        self.strategy = strategy

    def get_chatobject(self, user_input: USER_INPUT, **kwargs) -> ChatObject:
        """Create a :class:`ChatObject` bound to this runtime's configuration.

        The returned ChatObject reuses the runtime's preset, config, strategy,
        system prompt template, session_id and backend slots.  Memory and
        ability resolution is handled lazily by ChatObject via the backend.

        Args:
            user_input: The user's input message.
            **kwargs: Additional keyword arguments forwarded to :class:`ChatObject`
                (e.g. ``io_stream``, ``hook_args``, ``middleware``, etc.).

        Returns:
            A fully configured ChatObject ready for execution.
        """
        return ChatObject(
            train=self.train,
            user_input=user_input,
            context=None,
            session_id=self.session_id,
            backend=self.slot,
            config=self.config,
            preset=self.preset,
            agent_strategy=self.strategy,
            train_template=self.template,
            **kwargs,
        )


def create_agent(
    base_url: str,
    api_key: str,
    model: str = "auto",
    *,
    train: str | None = None,
    model_config: ModelConfig | dict | None = None,
    config: AmritaConfig | None = None,
    **kwargs,
) -> AgentRuntime:
    """
    Create an agent with minimal parameters by automatically creating a temporary preset.

    This factory function simplifies agent creation by only requiring essential
    parameters like URL and API key, automatically creating a temporary preset.

    Args:
        base_url: The API endpoint URL.
        api_key: The API key for authentication.
        model: The model to use. Defaults to "auto".
        model_config: Optional model configuration (dict or ModelConfig).
        config: Configuration for the agent. Defaults to global config.
        **kwargs: Additional keyword arguments forwarded to :class:`AgentRuntime`
            (e.g. ``strategy``, ``template``, ``session_id``, ``backend``).

    Returns:
        A configured :class:`AgentRuntime` instance.

    Example:
        ```python
        agent = create_agent(
            "https://api.example.com",
            "your-api-key",
            model="gpt-4",
            model_config={"temperature": 0.7},
        )
        ```
    """
    if train is None:
        train = DEFAULT_INSTRUCTIONS
    final_config = config or get_config()
    if isinstance(model_config, dict):
        model_config = ModelConfig(**model_config)
    elif not model_config:
        model_config = ModelConfig()

    preset = ModelPreset(
        name=f"temp_{uuid4().hex[:8]}",
        base_url=base_url,
        api_key=api_key,
        config=model_config,
        model=model,
    )

    return AgentRuntime(
        config=final_config,
        preset=preset,
        train=Message(content=train, role="system"),
        **{k: v for k, v in kwargs.items() if k not in ["config", "model_config"]},
    )
