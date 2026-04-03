from amrita_core.config import get_config
from amrita_core.logging import logger
from amrita_core.protocol import MessageWithMetadata
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
    ToolContext,
    ToolFunctionSchema,
)

PROCESS_MESSAGE_TOOL = FunctionDefinitionSchema(
    name="processing_message",
    description="Describe what the agent is currently doing and express the agent's internal thoughts to the user. Use this when you need to communicate your current actions or internal reasoning to the user, not for general completion.",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "content": FunctionPropertySchema(
                description="Message content, describe in the tone of system instructions what you are doing or interacting with the user.",
                type="string",
            ),
        },
        required=["content"],
    ),
)
PROCESS_MESSAGE = ToolFunctionSchema(
    type="function",
    function=PROCESS_MESSAGE_TOOL,
    strict=True,
)
STOP_TOOL = ToolFunctionSchema(
    type="function",
    function=FunctionDefinitionSchema(
        name="agent_stop",
        description="Call this tool to indicate that you have gathered enough information and are ready to formulate the final answer to the user.\n"
        + " After calling this, you should NOT call any other tools, but directly provide the completion",
        parameters=FunctionParametersSchema(
            type="object",
            properties={
                "result": FunctionPropertySchema(
                    type="string",
                    description="Simply illustrate what you did during the chat task.(Optional)",
                )
            },
            required=[],
        ),
    ),
    strict=True,
)

REASONING_TOOL = ToolFunctionSchema(
    type="function",
    function=FunctionDefinitionSchema(
        name="think_and_reason",
        description="Think about what you should do next, always call this tool to think when completing a tool call.",
        parameters=FunctionParametersSchema(
            type="object",
            properties={
                "content": FunctionPropertySchema(
                    description="What you should do next",
                    type="string",
                ),
            },
            required=["content"],
        ),
    ),
    strict=True,
)


@on_tools(
    data=PROCESS_MESSAGE_TOOL,
    custom_run=True,
    enable_if=lambda: get_config().function_config.agent_middle_message,
)
async def _(ctx: ToolContext) -> str | None:
    msg: str = ctx.data["content"]
    logger.debug(f"[LLM-ProcessMessage] {msg}")
    await ctx.ctx.chat_object.yield_response(
        MessageWithMetadata(
            content=msg, metadata={"type": "middle_message", "content": msg}
        )
    )
    return f"Sent a message to user:\n\n```text\n{msg}\n```\n"
