from jinja2 import Template

from amrita_core.builtins.tools import PROCESS_MESSAGE, REASONING_TOOL, STOP_TOOL

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

HYBRID_TEMPLATE = Template("""<TOOL_CALL name="{{tool_name}}">
    <PARAMS>
        {% for key,value in params.items() %}
        <PARAM name="{{key}}">{{value}}</PARAM>
        {% endfor %}
    </PARAMS>
</TOOL_CALL>
<TOOL_RESULT name="{{tool_name}}">
    {{result}}
</TOOL_RESULT>""")

REASONING_TEMPLATE = Template("""
## Reasoning Summary Instructions

Generate a brief summary for the `think_and_reason` tool using this exact format:

```
In this step, I should thinking about: [one-sentence description]
```

### Requirements:
- Keep it concise - just **one sentence**
- Focus on your immediate thought or current focus
- Do not include detailed reasoning or action plans
- Do not describe tool calls or final actions
- User input will be included in `<input>` tags

{% if last_step %}
### Previous Step:
```text
{{last_step}}
```
{% endif %}

### User Input:
<input>
{{original_msg|escape}}
</input>

### System Instructions:
<amcore_instructions>
{{stg.ctx.get_original_context().train.content}}
</amcore_instructions>
""")

REASONING_CONTENT_TEMPLATE = Template("""# Thinking instructions
## Task
Analyze the user input and produce a complete internal reasoning paragraph.
The reasoning should describe: what the user provided, what it implies, and the appropriate direction for a response.
Write in plain text as if you are thinking to yourself.

## Message Role Clarification
- The actual user input is located in the **conversation's `user` message**.
- This system prompt provides instructions, metadata, and contextual background.
- The `<think_step>` tag below indicates the current iteration count. Use it only for implicit awareness; do NOT mention it in your output.

## Metadata
<think_step called_times="{{ stg.reasoning_pc }}"/>

## Global Agent Instructions
The following defines the agent's overall role and tone. Align your reasoning style with these instructions.

<original_instructions>
{{ stg.ctx.get_original_context().train.content | safe }}
</original_instructions>

## Step-by-Step Reasoning Structure
Follow this logical flow:
1. Identify what the user input contains (e.g., a greeting, a question, a request).
2. Assess the intent or need behind the input.
3. Determine the appropriate tone and direction for a helpful response.

## Language Requirement
Use the EXACT same language as the user input (the `user` message).
If the user input is in Chinese, reason in Chinese. If English, reason in English.

## Additional Context
- Last step taken:
  <last_step>{{ last_step | escape }}</last_step>
- Current reasoning focus summary:
  <summary>{{ summary | escape }}</summary>

## Output Rules
- Output exactly one paragraph of plain text. Do not use any formatting, XML tags, or markdown.
- Do NOT describe your own state or mention words like "reasoning", "stage", "phase", or "step".
- Focus entirely on the user's input and the appropriate response strategy.
- Expand your thinking step by step, and stop naturally once the reasoning is complete. Do not append any special symbols or markers.

## Example
Assume the `user` message contains "Hello", and `<think_step>` shows `called_times="1"`.
Reasoning output:
The user opened with a simple greeting "Hello". This is a common way to start a conversation. I should respond warmly, introduce myself, and let the user know what I can help with. A friendly reply that offers assistance and invites further questions would be appropriate.

## Available Tools

Tools:
{% for tool in tools %}
- {{ tool["name"] }}: {{ tool["description"] }}
{% endfor %}

## Your Output
Now generate the complete reasoning paragraph based on the user input in the `user` message and the context above.
""")
