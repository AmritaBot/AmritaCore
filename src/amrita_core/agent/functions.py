from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from jinja2 import Template

from amrita_core.builtins.agent import ReActAgentStrategy
from amrita_core.chatmanager import ChatObject
from amrita_core.config import get_config
from amrita_core.consts import DEFAULT_INSTRUCTIONS, DEFAULT_TEMPLATE
from amrita_core.sessions import SessionData, SessionsManager
from amrita_core.types import USER_INPUT, MemoryModel, Message, ModelConfig, ModelPreset

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
    """

    strategy: type[AgentStrategy]
    session_id: str
    session: SessionData | None = None
    preset: ModelPreset
    config: AmritaConfig
    train: Message[str]
    context: MemoryModel
    template: Template

    def __init__(
        self,
        config: AmritaConfig,
        preset: ModelPreset,
        train: dict[str, str] | Message[str],
        strategy: type[AgentStrategy] = ReActAgentStrategy,
        template: Template | str = DEFAULT_TEMPLATE,
        session: SessionData | str | None = None,
        no_session: bool = False,
    ):
        """
        Initialize an AgentRuntime instance.

        Args:
            config (AmritaConfig): Amrita configuration object containing global configuration settings.
            preset (ModelPreset): Model preset configuration defining basic model parameters and settings.
            train (Message[str] | dict[str,str]): System prompt for agent.
            strategy (type[AgentStrategy], optional): Agent strategy class, defaults to ReActAgentStrategy.
            template (Template | str, optional): Train template to render system role message.
            session (SessionData | str | None, optional): Session data or session ID string for restoring
                existing sessions. If None, a new session will be created.
            no_session (bool, optional): Whether to disable session functionality. If True, session
                management will be disabled but a temporary session ID will still be assigned.
        """

        if no_session:
            # Assign a temporary session ID even when session functionality is disabled
            self.session_id = (
                uuid4().hex
            )  # Actually we still need to assign a session id
        else:
            # Handle session initialization logic: determine session ID based on provided session parameter and initialize session
            if not session:
                session_id = SessionsManager().new_session()

            elif isinstance(session, str):
                session_id = session
            else:
                session_id = session.session_id
            SessionsManager().init_session(session_id)
            self.session = SessionsManager().get_session_data(session_id)
            self.session_id = session_id
        self.context = (
            self.session.memory
            if self.session and not self.no_session
            else MemoryModel()
        )
        self.template = Template(template) if isinstance(template, str) else template
        self.strategy = strategy
        self.preset = preset
        self.config = config
        self.train = (
            train if isinstance(train, Message) else Message[str].model_validate(train)
        )

    @property
    def no_session(self) -> bool:
        return self.session is None

    def set_strategy(self, strategy: type[AgentStrategy]) -> None:
        """
        Set the agent strategy to be used for execution.

        Args:
            strategy (type[AgentStrategy]): The agent strategy to be used for execution.
        """
        self.strategy = strategy

    def get_chatobject(self, user_input: USER_INPUT, **kwargs) -> ChatObject:
        """Get a chat object

        Args:
            train (dict[str, str] | Message[str]): Training data (system prompts)
            user_input (USER_INPUT): Input from the user
            context (Memory | None): Memory context for the session
            session_id (str): Unique identifier for the session
            callback (RESPONSE_CALLBACK_TYPE, optional): Callback function to be called when returning response. Defaults to None.
            config (AmritaConfig | None, optional): Config used for this call. Defaults to None.
            preset (ModelPreset | None, optional): Preset used for this call. Defaults to None.
            auto_create_session (bool, optional): Whether to automatically create a session if it does not exist. Defaults to False.
            jinja2_vars (dict[str, Any] | None, optional): Variables to be passed to the template system. Defaults to None.
            train_template (Template, optional): Jinja2 template used to format system message.
            agent_strategy (type[AgentStrategy], optional):  Agent strategy to be used for execution. Defaults to ReActAgentStrategy.
            hook_args (tuple[Any, ...], optional): Arguments could be passed to the Matcher function. Defaults to ().
            hook_kwargs (dict[str, Any] | None, optional): Keyword arguments could be passed to the Matcher function. Defaults to None.
            exception_ignored (tuple[type[BaseException], ...], optional): These exceptions will be raised again if they are raised in the Matcher function. Defaults to ().\n            queue_size (int, optional): Maximum number of message chunks to be stored in the queue. Defaults to 25.
            overflow_queue_size (int, optional): Maximum number of message chunks to be stored in the overflow queu. Defaults to 45.

        Returns:
            ChatObject: A chat object
        """
        return ChatObject(
            train=self.train,
            user_input=user_input,
            context=self.context,
            session_id=self.session_id,
            config=self.config,
            preset=self.preset,
            agent_strategy=self.strategy,
            train_template=self.template,
            auto_create_session=not self.no_session,
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
        url (str): The API endpoint URL
        key (str): The API key for authentication
        model (str, optional): The model to use. Defaults to "auto".
        model_config (ModelConfig | dict | None, optional): Optional model configuration. Defaults to None.
        config (AmritaConfig | None, optional): Configuration for the agent. Defaults to global config.
        **kwargs: Additional keyword arguments to pass to AgentRuntime

    Returns:
        AgentRuntime: Configured agent runtime instance

    Example:
        ```python
        agent = create_agent(
            "https://api.example.com", # Replace with your API URL
            "your-api-key", # Replace with your API key
            model="gpt-4", # Replace with your desired model
            model_config={"temperature": 0.7}
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
