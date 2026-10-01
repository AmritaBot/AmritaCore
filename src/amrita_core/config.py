from __future__ import annotations

import secrets
import string
from typing import Literal

from pydantic import Field
from typing_extensions import LiteralString

from amrita_core.types import BaseModel


def random_alnum_string(length: int) -> str:
    if length < 0:
        raise ValueError("Length can't be smaller than zero!")

    chars: LiteralString = string.ascii_letters + string.digits

    return "".join(secrets.choice(chars) for _ in range(length))


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
        default=False,
        description="Whether to use minimal context, i.e. system prompt + user's last message (disabling this option will use all context from the message list, which may consume a large amount of Tokens during Agent workflow execution; enabling this option may effectively reduce token usage)",
    )
    agent_tool_call_limit: int = Field(
        default=10,
        ge=1,
        description="Tool call limit in calling tools.",
    )
    validate_tool_arguments: bool = Field(
        default=True,
        description="Whether to check the arguments the model produced against "
        "each tool's parameter schema before the tool runs. A failed check is "
        "returned to the model as an `ERR:` tool result, which lets it correct "
        "the call; disable to pass arguments through untouched.",
    )

    agent_step_token_budget: int = Field(
        default=-1,
        ge=-1,
        description="Per-Step prompt-token budget for the built-in step loop. "
        "Set -1 (or 0) to disable (no budget limit). "
        "When the Step's accumulated prompt tokens reach this budget, the "
        "iteration loop stops (``TokenBudget.exhausted``).",
    )

    agent_middle_message: bool = Field(
        default=True,
        description="Whether to allow Agent to send intermediate messages to users in tools calling",
    )
    agent_mcp_client_enable: bool = Field(
        default=False, description="Whether to enable MCP client"
    )
    agent_mcp_server_scripts: list[str] = Field(
        default=[], description="List of MCP server scripts"
    )


class ReactConfig(BaseModel):
    """ReAct agent reasoning enhancement configuration.

    All options default to False/off for full backward compatibility.
    When enabled, these options progressively strengthen the ReAct agent's
    reasoning capabilities through structured chain-of-thought decomposition,
    post-reasoning self-reflection, and reasoning-aware tool selection.
    """

    structured_reasoning: bool = Field(
        default=False,
        description="Enable step-by-step structured reasoning with explicit "
        "phase markers (analyze/plan/execute/verify). When True, the reasoning "
        "template guides the model to decompose problems into numbered steps.",
    )
    reasoning_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum reasoning chain depth (number of sub-problems). "
        "Used as a soft hint in the structured reasoning template.",
    )

    enable_reflection: bool = Field(
        default=False,
        description="Enable post-reasoning self-reflection. When True, the agent "
        "will call a verify_reasoning tool after STOP_TOOL to check for "
        "contradictions, completeness, and alignment with user goals before "
        "generating the final answer.",
    )
    reflection_depth: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Maximum number of reflection rounds. Each round may produce "
        "a correction that is fed back into the reasoning loop.",
    )

    reasoning_aware_tools: bool = Field(
        default=False,
        description="Enable reasoning-aware tool prioritization. When True, tools "
        "predicted during structured reasoning are placed ahead of other tools in "
        "the tool list, nudging the model toward the most relevant tools first.",
    )
    tool_prediction: bool = Field(
        default=False,
        description="Enable explicit tool prediction during reasoning. When True, "
        "the structured reasoning template asks the model to list which tools it "
        "expects to need. Requires structured_reasoning=True to be effective.",
    )


class BuiltinAgentConfig(BaseModel):
    tool_calling_mode: Literal["agent", "rag", "none"] = Field(
        default="agent",
        description="Tool calling mode for amrita's built-in agent strategy",
    )
    agent_thought_mode: Literal[
        "reasoning", "chat", "reasoning-required", "reasoning-optional"
    ] = Field(
        default="chat",
        description="Thinking mode in built-in agent strategy, reasoning mode will first perform reasoning process, then execute tasks; "
        "reasoning-required requires task analysis for each Tool Calling; "
        "reasoning-optional does not require reasoning but allows it; "
        "chat mode executes tasks directly",
    )
    loop_reasoning_trigger: int = Field(
        default=5,
        ge=1,
        description="How many times to repeat reasoning before giving up",
    )
    react_config: ReactConfig = Field(
        default_factory=ReactConfig,
        description="ReAct agent reasoning enhancement configuration. "
        "Controls structured reasoning, self-reflection, and reasoning-aware "
        "tool selection. All options default to off for backward compatibility.",
    )


class LLMConfig(BaseModel):
    require_tools: bool = Field(
        default=False,
        description="Whether to force at least one tool to be used per call",
    )
    max_tokens: int = Field(
        default=10000,
        ge=1,
        description="Last-resort fallback for the response output budget. The "
        "number that actually reaches the provider comes from the preset's "
        "`max_output` (default 28000); this value is used only when a preset "
        "explicitly sets `max_output` to `None`.",
    )
    compaction_max_tokens: int = Field(
        default=2048,
        ge=0,
        description="Output-token ceiling for the history-compaction summary "
        "call. A reasoning model spends its output budget on thinking before "
        "it emits anything, so a summary that inherits a small `max_output` "
        "comes back empty and the fold silently does nothing. Set 0 to let "
        "the summary call use the preset's own value.",
    )
    session_tokens_windows: int = Field(
        default=65536,
        ge=1,
        description="Fallback attention window (default 64k) used when the "
        "active preset does not declare `max_context`. Presets that declare "
        "their own window take precedence, so a model's real limit follows the "
        "model rather than this global number.",
    )
    llm_timeout: int = Field(
        default=60,
        ge=1,
        description="API request timeout duration (seconds)",
    )
    auto_retry: bool = Field(
        default=True, description="Automatically retry on request failure"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retries",
    )
    max_fallbacks: int = Field(
        default=5,
        ge=1,
        description="Maximum number of preset fallbacks",
    )
    enable_compaction: bool = Field(
        default=True,
        description="Whether to fold long history into a summary. The summary "
        "is stored on `MemoryModel.abstract` and rendered into the system "
        "instruction by the train template.",
    )
    compaction_trigger_ratio: float = Field(
        default=0.9,
        gt=0,
        le=1,
        description="Fraction of the preset's `max_context` at which history "
        "compaction is forced. Kept below 1.0 to absorb the lag between the "
        "last measured prompt size and the next request's actual size.",
    )
    memory_length_limit: int = Field(
        default=200,
        ge=0,
        description="Message-count fallback that forces compaction regardless "
        "of token accounting. Needed because the token trigger relies on the "
        "provider reporting usage: a gateway that reports none would let "
        "history grow without bound. Set 0 to disable the fallback and rely "
        "on the token trigger alone.",
    )
    enable_overflow_recovery: bool = Field(
        default=True,
        description="Whether to compact and retry once when the provider "
        "rejects a request for exceeding the context window.",
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
    builtin: BuiltinAgentConfig = Field(
        default_factory=BuiltinAgentConfig,
        description="Built-in agent configuration",
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
