import json
import typing
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from amrita_core.agent.context import StrategyContext
from amrita_core.agent.strategy import AgentStrategy
from amrita_core.builtins.consts import BUILTIN_TOOLS_NAME
from amrita_core.config import AmritaConfig, get_config
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.exception import MatcherException as ProcEXC
from amrita_core.hook.on import on_completion
from amrita_core.libchat import (
    tools_caller,
)
from amrita_core.logging import debug_log, logger
from amrita_core.protocol import MessageWithMetadata
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import ToolContext
from amrita_core.types import (
    Message,
    TextContent,
    ToolCall,
    ToolResult,
    UniResponse,
)

from .tools import (
    PROCESS_MESSAGE,
    PROCESS_MESSAGE_TOOL,
    REASONING_TOOL,
    STOP_TOOL,
)

posthook = on_completion(block=False, priority=10)


class Continue(BaseException): ...


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


class AmritaAgentStrategy(AgentStrategy):
    """
    Amrita Agent Strategy is a strategy for executing an agent in RAG and Agent mode.

    This strategy implements the 'agent-mixed' category, allowing it to dynamically handle
    both retrieval-augmented generation scenarios and standard iterative tool calling agents
    within the same execution framework.
    """

    agent_last_step: str | None = None
    call_count = 1
    tools: list[Any]
    origin_msg = ""

    def __init__(self, ctx: StrategyContext) -> None:
        super().__init__(ctx)
        config = self.chat_object.config
        self.tools = []
        if config.builtin.tool_calling_mode == "agent":
            self.tools.append(STOP_TOOL.model_dump())
            if config.builtin.agent_thought_mode.startswith("reasoning"):
                self.tools.append(REASONING_TOOL.model_dump())
        self.tools.extend(self.tools_manager.tools_meta_dict().values())
        self.origin_msg = (
            "".join(
                chunk.text
                for chunk in ctx.original_context.user_query.content
                if isinstance(chunk, TextContent)
            )
            if isinstance(ctx.original_context.user_query.content, list)
            else ctx.original_context.user_query.content
        )

    async def _generate_reasoning_msg(
        self,
        original_msg: str = "",
        tools_ctx: list[dict[str, Any]] = [],
    ):
        last_step = self.agent_last_step
        reasoning_msg = [
            Message(
                role="system",
                content="Please analyze the task requirements based on the user input above,"
                + " summarize the current step's purpose and reasons, and execute accordingly."
                + " If no task needs to be performed, no description is needed;"
                + " please analyze according to the character tone set in <ROLE_SETTINGS> (if present)."
                + (
                    f"\nYour previous task was:\n```text\n{last_step}\n```\n"
                    if last_step
                    else ""
                )
                + (f"\n<INPUT>\n{original_msg}\n</INPUT>\n" if original_msg else "")
                + (
                    f"<ROLE_SETTINGS>\n{self.ctx.get_original_context().train.content!s}\n</ROLE_SETTINGS>"
                ),
            ),
            *self.ctx.original_context.unwrap(exclude_system=True),
        ]
        response: UniResponse[None, list[ToolCall] | None] = await tools_caller(
            reasoning_msg,
            [REASONING_TOOL.model_dump(), *tools_ctx],
            tool_choice=REASONING_TOOL,
            preset=self.ctx.chat_object.preset,
        )
        await self._append_reasoning(response)

    async def _append_reasoning(
        self, response: UniResponse[None, list[ToolCall] | None]
    ):
        msg = self.ctx.get_original_context()

        tool_calls: list[ToolCall] | None = response.tool_calls
        if tool_calls:
            for tool in tool_calls:
                if tool.function.name == REASONING_TOOL.function.name:
                    break
            else:
                raise ValueError(f"No reasoning tool found in response \n\n{response}")
            if reasoning := json.loads(tool.function.arguments).get("content"):
                msg.append(Message.model_validate(response, from_attributes=True))
                msg.append(
                    ToolResult(
                        role="tool",
                        name=tool.function.name,
                        content=reasoning,
                        tool_call_id=tool.id,
                    )
                )
                self.agent_last_step = reasoning
                logger.debug(f"[AmritaAgent] {reasoning}")
                if not self.chat_object.config.builtin.agent_reasoning_hide:
                    await self.chat_object.yield_response(
                        response=MessageWithMetadata(
                            content=f"<think>\n{reasoning}\n</think>",
                            metadata={"type": "reasoning", "content": reasoning},
                        )
                    )
            else:
                raise ValueError("Reasoning tool has no content!")

    async def single_execute(
        self,
    ) -> bool:
        suggested_stop: bool = False
        config = self.chat_object.config
        msg_list = self.ctx.original_context
        if not self.tools:
            return False

        def stop_running():
            """Mark agent workflow as completed."""
            nonlocal suggested_stop
            suggested_stop = True

        logger.info(
            f"Starting round {self.call_count} tool call, current message count: {len(msg_list)}"
        )
        if config.builtin.tool_calling_mode == "agent" and (
            (self.call_count == 1 and config.builtin.agent_thought_mode == "reasoning")
            or config.builtin.agent_thought_mode == "reasoning-required"
        ):
            await self._generate_reasoning_msg(self.origin_msg, tools_ctx=self.tools)
        elif config.builtin.tool_calling_mode == "none":
            return False
        response_msg = await tools_caller(
            msg_list.unwrap(),
            self.tools,
            tool_choice=(
                "required"
                if (config.llm.require_tools and not suggested_stop)
                else "auto"
            ),
            preset=self.chat_object.preset,
        )

        if tool_calls := response_msg.tool_calls:
            result_msg_list: list[ToolResult] = []
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args: dict[str, Any] = json.loads(tool_call.function.arguments)
                debug_log(f"Function arguments are {tool_call.function.arguments}")
                logger.info(f"Calling function {function_name}")
                await self.chat_object.yield_response(
                    MessageWithMetadata(
                        content=f"Calling function {function_name}\n",
                        metadata={
                            "type": "function_call",
                            "function_name": function_name,
                            "is_done": False,
                            "tool_id": tool_call.id,
                        },
                    )
                )
                err: Exception | None = None
                try:
                    match function_name:
                        case REASONING_TOOL.function.name:
                            logger.debug("Generating task summary and reason.")
                            await self._append_reasoning(response=response_msg)
                            raise Continue()
                        case STOP_TOOL.function.name:
                            logger.info("Agent work has been terminated.")
                            func_response = (
                                "You have indicated readiness to provide the final answer."
                                + "Please now generate the final, comprehensive response for the user."
                            )
                            if "result" in function_args:
                                debug_log(f"[Done] {function_args['result']}")
                                func_response += (
                                    f"\nWork summary :\n{function_args['result']}"
                                )
                            msg_list.append(
                                Message.model_validate(
                                    response_msg, from_attributes=True
                                )
                            )

                            stop_running()
                        case _:
                            if (
                                tool_data := self.tools_manager.get_tool(function_name)
                            ) is not None:
                                if not tool_data.custom_run:
                                    msg_list.append(
                                        Message.model_validate(
                                            response_msg, from_attributes=True
                                        )
                                    )
                                    func_response: str = await typing.cast(
                                        Callable[[dict[str, Any]], Awaitable[str]],
                                        tool_data.func,
                                    )(function_args)
                                elif (
                                    tool_response := await typing.cast(
                                        Callable[[ToolContext], Awaitable[str | None]],
                                        tool_data.func,
                                    )(
                                        ToolContext(
                                            data=function_args,
                                            ctx=self.ctx,
                                        )
                                    )
                                ) is None:
                                    func_response = "(this tool returned no content)"
                                else:
                                    msg_list.append(
                                        Message.model_validate(
                                            response_msg, from_attributes=True
                                        )
                                    )
                                    func_response = tool_response
                            else:
                                raise RuntimeError("Received unexpected response type")

                except Continue:
                    continue
                except Exception as e:
                    err = e
                    if isinstance(e, ProcEXC):
                        raise
                    logger.error(f"Function {function_name} execution failed: {e}")
                    if (
                        config.builtin.tool_calling_mode == "agent"
                        and function_name not in BUILTIN_TOOLS_NAME
                        and config.builtin.agent_tool_call_notice
                    ):
                        await self.chat_object.yield_response(
                            MessageWithMetadata(
                                content=f"Error: {function_name} failed.",
                                metadata={
                                    "type": "function_call",
                                    "function_name": function_name,
                                    "is_done": True,
                                    "tool_id": tool_call.id,
                                    "err": err,
                                },
                            )
                        )
                    msg_list.append(
                        ToolResult(
                            role="tool",
                            name=function_name,
                            content=f"ERR: Tool {function_name} execution failed\n{e!s}",
                            tool_call_id=tool_call.id,
                        )
                    )
                    continue
                else:
                    logger.debug(f"Function {function_name} returned: {func_response}")

                    msg: ToolResult = ToolResult(
                        role="tool",
                        content=func_response,
                        name=function_name,
                        tool_call_id=tool_call.id,
                    )
                    msg_list.append(msg)
                    result_msg_list.append(msg)
                finally:
                    self.call_count += 1

                # Send tool call info to user
                if config.builtin.agent_tool_call_notice == "notify":
                    for rslt in result_msg_list:
                        await self.chat_object.yield_response(
                            MessageWithMetadata(
                                content=f"Called tool {rslt.name}\n",
                                metadata={
                                    "type": "function_call",
                                    "function_name": function_name,
                                    "is_done": True,
                                    "tool_id": tool_call.id,
                                    "err": None,
                                },
                            )
                        )
            return True
        return False

    @classmethod
    def get_category(cls) -> Literal["agent-mixed"]:
        """
        Get the category of the agent strategy.

        Returns:
            The strategy category as a literal string indicating execution pattern.
        """
        return "agent-mixed"


@posthook.handle()
async def cookie(event: CompletionEvent, config: AmritaConfig):
    response = event.get_model_response()
    if config.cookie.enable_cookie:
        if cookie := config.cookie.cookie:
            if cookie in response:
                await event.chat_object.yield_response(
                    response=MessageWithMetadata(
                        "Some error occurred, please try again later.",
                        metadata={
                            "type": "error",
                            "extra_type": "cookie",
                            "content": "Some error occurred, please try again later.",
                        },
                    )
                )
                await event.chat_object.set_queue_done()


__all__ = ["PROCESS_MESSAGE"]
