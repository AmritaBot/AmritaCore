import json
import os
import typing
import warnings
from collections.abc import Awaitable, Callable
from copy import deepcopy
from typing import Any

from amrita_core.config import get_config
from amrita_core.hook.event import CompletionEvent, PreCompletionEvent
from amrita_core.hook.exception import MatcherException as ChatException
from amrita_core.hook.on import on_completion, on_precompletion
from amrita_core.libchat import (
    tools_caller,
)
from amrita_core.logging import debug_log
from amrita_core.tools.manager import ToolsManager, on_tools
from amrita_core.tools.models import ToolContext
from amrita_core.types import CONTENT_LIST_TYPE as SEND_MESSAGES
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

prehook = on_precompletion(block=False, priority=2)
posthook = on_completion(block=False, priority=1)


BUILTIN_TOOLS_NAME = {
    STOP_TOOL.function.name,
    REASONING_TOOL.function.name,
    PROCESS_MESSAGE.function.name,
}

AGENT_PROCESS_TOOLS = (
    REASONING_TOOL,
    STOP_TOOL,
    PROCESS_MESSAGE,
)


class Continue(BaseException): ...


@on_tools(
    data=PROCESS_MESSAGE_TOOL,
    custom_run=True,
    enable_if=lambda: get_config().function_config.agent_middle_message,
)
async def _(ctx: ToolContext) -> str | None:
    msg: str = ctx.data["content"]
    debug_log(f"[LLM-ProcessMessage] {msg}")
    await ctx.event.chat_object.yield_response(msg)
    return f"Sent a message to user:\n\n```text\n{msg}\n```\n"


@prehook.handle()
async def agent_core(event: PreCompletionEvent) -> None:
    agent_last_step: str = ""

    async def _append_reasoning(
        msg: SEND_MESSAGES, response: UniResponse[None, list[ToolCall] | None]
    ):
        nonlocal agent_last_step
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
                agent_last_step = reasoning
                debug_log(f"[AmritaAgent] {reasoning}")
                if not config.function_config.agent_reasoning_hide:
                    await event.chat_object.yield_response(
                        f"<think>\n\n{reasoning}\n\n</think>"
                    )
            else:
                raise ValueError("Reasoning tool has no content!")

    async def append_reasoning_msg(
        msg: SEND_MESSAGES,
        original_msg: str = "",
        last_step: str = "",
        tools_ctx: list[dict[str, Any]] = [],
    ):
        nonlocal agent_last_step
        reasoning_msg = [
            Message(
                role="system",
                content="Please analyze the task requirements based on the user input above,"
                + " summarize the current step's purpose and reasons, and execute accordingly."
                + " If no task needs to be performed, no description is needed;"
                + " please analyze according to the character tone set in <SYS_SETTINGS> (if present)."
                + (
                    f"\nYour previous task was:\n```text\n{last_step}\n```\n"
                    if last_step
                    else ""
                )
                + (f"\n<INPUT>\n{original_msg}\n</INPUT>\n" if original_msg else "")
                + (
                    f"<SYS_SETTINGS>\n{event.get_context_messages().train.content!s}\n</SYS_SETTINGS>"
                ),
            ),
            *deepcopy(msg),
        ]
        response: UniResponse[None, list[ToolCall] | None] = await tools_caller(
            reasoning_msg,
            [REASONING_TOOL.model_dump(), *tools_ctx],
            tool_choice=REASONING_TOOL,
        )
        await _append_reasoning(msg, response)

    async def run_tools(
        msg_list: list,
        call_count: int = 1,
        original_msg: str = "",
    ):
        suggested_stop: bool = False

        def stop_running():
            """Mark agent workflow as completed."""
            nonlocal suggested_stop
            suggested_stop = True

        debug_log(
            f"Starting round {call_count} tool call, current message count: {len(msg_list)}"
        )
        config = get_config()
        if config.function_config.tool_calling_mode == "agent" and (
            (
                call_count == 1
                and config.function_config.agent_thought_mode == "reasoning"
            )
            or config.function_config.agent_thought_mode == "reasoning-required"
        ):
            await append_reasoning_msg(msg_list, original_msg, tools_ctx=tools)

        if call_count > config.function_config.agent_tool_call_limit:
            await event.chat_object.yield_response(
                "[AmritaAgent] 过多次的工具调用！已中止Workflow！"
            )
            msg_list.append(
                Message(
                    role="user",
                    content="Too much tools called,please call later or follow user's instruction."
                    + "Now please continue to completion.",
                )
            )
            return
        response_msg = await tools_caller(
            msg_list,
            tools,
            tool_choice=(
                "required"
                if (config.llm.require_tools and not suggested_stop)
                else "auto"
            ),
        )

        if tool_calls := response_msg.tool_calls:
            result_msg_list: list[ToolResult] = []
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args: dict[str, Any] = json.loads(tool_call.function.arguments)
                debug_log(f"Function arguments are {tool_call.function.arguments}")
                debug_log(f"Calling function {function_name}")
                try:
                    match function_name:
                        case REASONING_TOOL.function.name:
                            debug_log("Generating task summary and reason.")
                            await _append_reasoning(msg_list, response=response_msg)
                            raise Continue()
                        case STOP_TOOL.function.name:
                            debug_log("Agent work has been terminated.")
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
                                tool_data := ToolsManager().get_tool(function_name)
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
                                            event=event,
                                            matcher=prehook,
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
                    if isinstance(e, ChatException):
                        raise
                    print(f"Function {function_name} execution failed: {e}")
                    if (
                        config.function_config.tool_calling_mode == "agent"
                        and function_name not in BUILTIN_TOOLS_NAME
                        and config.function_config.agent_tool_call_notice
                    ):
                        await event.chat_object.yield_response(
                            f"Error:{function_name} failed."
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
                    debug_log(f"Function {function_name} returned: {func_response}")

                    msg: ToolResult = ToolResult(
                        role="tool",
                        content=func_response,
                        name=function_name,
                        tool_call_id=tool_call.id,
                    )
                    msg_list.append(msg)
                    result_msg_list.append(msg)
                finally:
                    call_count += 1
            if config.function_config.tool_calling_mode == "agent":
                # 发送工具调用信息给用户
                if config.function_config.agent_tool_call_notice == "notify":
                    if message := (
                        "".join(
                            f"✅ 调用了工具 {i.name}\n"
                            for i in result_msg_list
                            if (
                                getattr(
                                    ToolsManager().get_tool(i.name), "on_call", None
                                )
                                == "show"
                                and i.name not in AGENT_PROCESS_TOOLS
                            )
                        )
                    ):
                        await event.chat_object.yield_response(message)
                await run_tools(msg_list, call_count, original_msg)

    config = get_config()
    if config.function_config.tool_calling_mode == "none":
        return
    msg_list: SEND_MESSAGES = (
        [
            deepcopy(event.message.train),
            deepcopy(event.message.user_query),
        ]
        if config.function_config.use_minimal_context
        else event.message.unwrap()
    )
    current_length = len(msg_list)
    chat_list_backup = event.message.copy()
    tools: list[dict[str, Any]] = []
    if config.function_config.tool_calling_mode == "agent":
        tools.append(STOP_TOOL.model_dump())
        if config.function_config.agent_thought_mode.startswith("reasoning"):
            tools.append(REASONING_TOOL.model_dump())
    tools.extend(ToolsManager().tools_meta_dict().values())
    debug_log(
        "工具列表："
        + "".join(
            f"{tool['function']['name']}: {tool['function']['description']}\n\n"
            for tool in tools
        )
    )
    debug_log(f"工具列表：{tools}")
    if not tools:
        warnings.warn("未定义任何有效工具！Tools Workflow已跳过。")
        return
    if str(os.getenv(key="AMRITA_IGNORE_AGENT_TOOLS")).lower() == "true" and (
        config.function_config.tool_calling_mode == "agent"
        and len(tools) == len(AGENT_PROCESS_TOOLS)
    ):
        warnings.warn(
            "注意：当前工具类型仅有Agent模式过程工具，而无其他有效工具定义，这通常不是使用Agent模式的最佳实践。配置环境变量AMRITA_IGNORE_AGENT_TOOLS=true可忽略此警告。"
        )

    try:
        await run_tools(
            msg_list,
            original_msg=event.original_context
            if isinstance(event.original_context, str)
            else "".join(
                [
                    i.content
                    for i in event.original_context
                    if isinstance(i, TextContent)
                ]
            ),
        )
        event._context_messages.extend(msg_list[current_length:])

    except Exception as e:
        if isinstance(e, ChatException):
            raise
        warnings.warn(
            f"ERROR\n{e!s}\n!Failed to call Tools! Continuing with old data..."
        )
        event._context_messages = chat_list_backup


@posthook.handle()
async def cookie(event: CompletionEvent):
    config = get_config()
    response = event.get_model_response()
    if config.cookie.enable_cookie:
        if cookie := config.cookie.cookie:
            if cookie in response:
                await event.chat_object.yield_response(
                    "Some error occurred, please try again later."
                )
                await event.chat_object.set_queue_done()
