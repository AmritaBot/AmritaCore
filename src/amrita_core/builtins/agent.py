import json
from typing import Any, Literal

from typing_extensions import override

from amrita_core.agent.context import StrategyContext
from amrita_core.agent.strategy import AgentStrategy
from amrita_core.builtins.consts import BUILTIN_TOOLS_NAME
from amrita_core.libchat import (
    tools_caller,
)
from amrita_core.logging import debug_log, logger
from amrita_core.protocol import MessageWithMetadata
from amrita_core.types import (
    Message,
    SendMessageWrap,
    TextContent,
    ToolCall,
    ToolResult,
    UniResponse,
)

from .tools import (
    PROCESS_MESSAGE,
    REASONING_TOOL,
    STOP_TOOL,
)


class ReActAgentStrategy(AgentStrategy):
    """
    ReAct Strategy is a strategy for executing an agent in RAG and Agent mode.

    This strategy implements the 'agent-mixed' category, allowing it to dynamically handle
    both retrieval-augmented generation scenarios and standard iterative tool calling agents
    within the same execution framework.
    """

    agent_last_step: str | None = None
    call_count = 1
    tools: list[Any]
    origin_msg = ""
    reasoning_pc = 0

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
        self.reasoning_pc += 1
        msg: SendMessageWrap = self.ctx.get_original_context()

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

    @override
    async def on_exception(self, exc: BaseException) -> None:
        """No action to do, because we had already handled the exception in the agent strategy"""
        return None

    async def single_execute(
        self,
    ) -> bool:
        suggested_stop: bool = False
        config = self.chat_object.config
        msg_list: SendMessageWrap = self.ctx.original_context
        if not self.tools:
            return False
        if config.builtin.tool_calling_mode == "rag" and self.call_count > 1:
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
        response_msg: UniResponse[None, list[ToolCall] | None] = await tools_caller(
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
                try:
                    match function_name:
                        case REASONING_TOOL.function.name:
                            logger.debug("Generating task summary and reason.")
                            await self._append_reasoning(response=response_msg)
                            return True
                        case STOP_TOOL.function.name:
                            self.agent_last_step = "Stopped"
                            self.reasoning_pc = 0
                            logger.info("Agent work has been terminated.")
                            func_response = (
                                "<BEGIN_OF_INSTRUCTIONS>\n"
                                + "You have indicated readiness to provide the final answer. "
                                + "Please now generate the final, comprehensive response for the user."
                                + "You must NOT to call any tools again."
                                + "\n<END_OF_INSTRUCTIONS>"
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
                            self.reasoning_pc = 0
                            func_response = await self.call_tool(tool_call)
                            msg_list.append(
                                Message.model_validate(
                                    response_msg, from_attributes=True
                                )
                            )
                except Exception as err:
                    logger.error(f"Function {function_name} execution failed: {err}")
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
                            content=f"ERR: Tool {function_name} execution failed\n{err!s}",
                            tool_call_id=tool_call.id,
                        )
                    )

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
                    if self.reasoning_pc > config.builtin.loop_reasoning_trigger:
                        prompt = f"Loop reasoning triggered. Trying to give up the tool call at ChatObject `{self.chat_object.stream_id}`."
                        logger.error(prompt)
                        self.ctx.original_context.append(
                            Message(
                                role="user",
                                content="<BEGIN_OF_EXTRA>\n\n"
                                + "You had called too many duplicate reasoning, which may indicate that you are stuck in a loop."
                                + "Please try to give up the current tool calling and directly answer the user query based on the information you have."
                                + "\n\n<END_OF_EXTRA>\n",
                            )
                        )
                        await self.chat_object.yield_response(
                            MessageWithMetadata(
                                content=prompt,
                                metadata={
                                    "type": "error",
                                    "extra_type": "loop_reasoning",
                                    "chat_object_id": self.chat_object.stream_id,
                                    "content": prompt,
                                },
                            )
                        )
                        return False
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


AmritaAgentStrategy = ReActAgentStrategy  # Alias for backward compatibility

__all__ = ["PROCESS_MESSAGE"]  # backward compatibility
