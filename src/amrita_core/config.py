# TODO:分实例的配置
from __future__ import annotations

import random
import string
from typing import Literal

from pydantic import Field
from typing_extensions import LiteralString

from amrita_core.types import BaseModel


def random_alnum_string(length: int) -> str:
    if length < 0:
        raise ValueError("Length can't be smaller than zero!")

    chars: LiteralString = string.ascii_letters + string.digits

    return "".join(random.choice(chars) for _ in range(length))


class CookieConfig(BaseModel):
    """Amrita Core's cookie config"""

    enable_cookie: bool = Field(
        default=True, description="Whether to enable Cookie leak detection mechanism"
    )
    cookie: str = Field(
        default_factory=lambda: random_alnum_string(16),
        description="Cookie string for security detection",
    )


class FunctionConfig(BaseModel):
    use_minimal_context: bool = Field(
        default=True,
        description="Whether to use minimal context, i.e. system prompt + user's last message (disabling this option will use all context from the message list, which may consume a large amount of Tokens during Agent workflow execution; enabling this option may effectively reduce token usage)",
    )

    tool_calling_mode: Literal["agent", "rag", "none"] = Field(
        default="agent",
        description="Tool calling mode, i.e. whether to use Agent or RAG to call tools",
    )
    agent_tool_call_limit: int = Field(
        default=10, description="Tool call limit in agent mode"
    )
    agent_tool_call_notice: Literal["hide", "notify"] = Field(
        default="hide",
        description="Method of showing tool call status in agent mode, hide to conceal, notify to inform",
    )
    agent_thought_mode: Literal[
        "reasoning", "chat", "reasoning-required", "reasoning-optional"
    ] = Field(
        default="chat",
        description="Thinking mode in agent mode, reasoning mode will first perform reasoning process, then execute tasks; "
        "reasoning-required requires task analysis for each Tool Calling; "
        "reasoning-optional does not require reasoning but allows it; "
        "chat mode executes tasks directly",
    )
    agent_reasoning_hide: bool = Field(
        default=False, description="Whether to hide the thought process in agent mode"
    )
    agent_middle_message: bool = Field(
        default=True,
        description="Whether to allow Agent to send intermediate messages to users in agent mode",
    )
    agent_mcp_client_enable: bool = Field(
        default=False, description="Whether to enable MCP client"
    )
    agent_mcp_server_scripts: list[str] = Field(
        default=[], description="List of MCP server scripts"
    )


class LLMConfig(BaseModel):
    require_tools: bool = Field(
        default=False,
        description="Whether to force at least one tool to be used per call",
    )
    memory_length_limit: int = Field(
        default=50, description="Maximum number of messages in memory context"
    )
    max_tokens: int = Field(
        default=100,
        description="Maximum number of tokens generated in a single response",
    )
    tokens_count_mode: Literal["word", "bpe", "char"] = Field(
        default="bpe",
        description="Token counting mode: bpe(subwords)/word(words)/char(characters)",
    )
    enable_tokens_limit: bool = Field(
        default=True, description="Whether to enable context length limits"
    )
    session_tokens_windows: int = Field(
        default=5000, description="Session tokens window size"
    )
    llm_timeout: int = Field(
        default=60, description="API request timeout duration (seconds)"
    )
    auto_retry: bool = Field(
        default=True, description="Automatically retry on request failure"
    )
    max_retries: int = Field(default=3, description="Maximum number of retries")
    max_fallbacks: int = Field(
        default=5, description="Maximum number of preset fallbacks"
    )
    enable_memory_abstract: bool = Field(
        default=True,
        description="Whether to enable context memory summarization (will delete context and insert a summary into system instruction)",
    )
    memory_abstract_proportion: float = Field(
        default=15e-2, description="Context summarization proportion (0.15=15%)"
    )
    enable_multi_modal: bool = Field(
        default=True,
        description="Whether to enable multi-modal support (currently only supports image)",
    )


class AmritaConfig(BaseModel):
    function_config: FunctionConfig = Field(
        default_factory=FunctionConfig,
        description="Function configuration",
    )
    llm: LLMConfig = Field(
        default_factory=LLMConfig,
        description="LLM configuration",
    )
    cookie: CookieConfig = Field(
        default_factory=CookieConfig, description="Cookie configuration"
    )


__config = AmritaConfig()
__inited: bool = False


def get_config() -> AmritaConfig:
    """Get the global amrita config

    Raises:
        RuntimeError: Raise it if amrita core is not initialized.

    Returns:
        AmritaConfig: Amrita core config
    """
    if not __inited:
        raise RuntimeError(
            "Global AmritaConfig is not initialized. Please use `set_config` set config first."
        )
    return __config


def set_config(config: AmritaConfig):
    """Override the global config.

    Args:
        config (AmritaConfig): Configuration object to set
    """
    global __config, __inited
    if not __inited:
        __inited = True
    __config = config
