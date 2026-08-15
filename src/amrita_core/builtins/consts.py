from jinja2 import Template

from amrita_core.builtins.tools import (
    PROCESS_MESSAGE,
    REASONING_TOOL,
    REFLECTION_TOOL,
    STOP_TOOL,
    UPDATE_STEP_TOOL,
)

BUILTIN_TOOLS_NAME = {
    STOP_TOOL.function.name,
    REASONING_TOOL.function.name,
    PROCESS_MESSAGE.function.name,
    REFLECTION_TOOL.function.name,
    UPDATE_STEP_TOOL.function.name,
}

AGENT_PROCESS_TOOLS = (
    REASONING_TOOL,
    STOP_TOOL,
    PROCESS_MESSAGE,
    REFLECTION_TOOL,
    UPDATE_STEP_TOOL,
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


STRUCTURED_REASONING_TEMPLATE = Template("""# Structured Reasoning Instructions

## Task
Analyze the user input and produce a structured, step-by-step internal reasoning.
Decompose the problem into at most {{ depth }} sub-problems, and walk through each one
using the four reasoning phases: **analyze -> plan -> execute -> verify**.

## Message Role Clarification
- The actual user input is located in the **conversation's `user` message**.
- This system prompt provides instructions, metadata, and contextual background.
- The `<think_step>` tag indicates the current iteration count.

## Metadata
<think_step called_times="{{ stg.reasoning_pc }}"/>

## Global Agent Instructions
The following defines the agent's overall role and tone. Align your reasoning style with these instructions.

<original_instructions>
{{ stg.ctx.get_original_context().train.content | safe }}
</original_instructions>

## Structured Reasoning Format

Output your reasoning using this exact structure for each step:

```
[Step 1/{{ depth }}] [analyze]
Understanding: <what is the user asking?>
Goal: <what must be achieved in this step?>

[Step 2/{{ depth }}] [plan]
Strategy: <how should I approach this?>
Tools needed: <which tools will help, if any?>

[Step 3/{{ depth }}] [execute]
Action: <what action to take or tool to call?>

[Step N/{{ depth }}] [verify]
Check: <did the result match the goal?>
```

### Phase Descriptions
- **[analyze]**: Understand the user input, identify key requirements, constraints, and sub-problems
- **[plan]**: Devise a strategy, choose approaches, decide which tools or knowledge to use
- **[execute]**: Carry out the planned actions, call tools, compute results
- **[verify]**: Validate the results against the goal; check for errors, missing pieces, or inconsistencies

## Requirements
- Use **at least 2 steps** and at most {{ depth }} steps
- Each step must have exactly **one phase** tag
- Each step should advance the reasoning toward a solution
- Stay grounded in the user input and the conversation context

## Language Requirement
Use the EXACT same language as the user input (the `user` message).
If the user input is in Chinese, reason in Chinese. If English, reason in English.

## Additional Context
- Last step taken:
  <last_step>{{ last_step | escape }}</last_step>
- Current reasoning focus summary:
  <summary>{{ summary | escape }}</summary>

## Available Tools
{% for tool in tools %}
- {{ tool["name"] }}: {{ tool["description"] }}
{% endfor %}

{% if predict_tools %}
## Tool Prediction
After your reasoning steps, append a brief tool prediction section:

```
[TOOL_PREDICTION]
tools: <comma-separated list of tool names you expect to need>
next_action: <one-sentence description of what you will do next>
```
{% endif %}

## Your Output
Now generate the structured reasoning. Remember to include the step numbers and phase tags.
""")


REFLECTION_TEMPLATE = Template("""# Reflection and Verification Instructions

## Task
You have just completed a chain of reasoning and tool calls. Before delivering the final
answer, carefully review your work for correctness, consistency, and completeness.

## Checks to Perform

### 1. Self-Check (Logical Soundness)
- Do your conclusions logically follow from the evidence?
- Are there any unsupported assumptions or leaps in logic?
- Is every claim backed by tool results or the conversation context?

### 2. Contradiction Check (Internal Consistency)
- Is any step in your reasoning inconsistent with another?
- Did you change your answer without acknowledging it?
- Are tool results interpreted correctly without contradiction?

### 3. Completeness Check (Coverage)
- Have you addressed ALL aspects of the user's original request?
- Did you overlook any sub-problems or edge cases?
- Is the final answer comprehensive enough?

## Output Format

You MUST output your reflection in this exact format:
```
[REFLECTION_RESULT]
type: <self_check|contradiction_check|completeness_check>
result: <pass|warning|fail>
detail: <one or two sentences explaining your finding>
```

### Result Definitions
- **pass**: No issues found. The reasoning is sound.
- **warning**: Minor issue found, but it does not materially affect the answer.
- **fail**: Significant problem detected. The answer may be unreliable.

## Additional Context
- Original user query:
  <user_query>{{ original_msg | escape }}</user_query>
- Last step taken:
  <last_step>{{ last_step | escape }}</last_step>

## Your Output
Now perform all three checks (self_check, contradiction_check, completeness_check)
and output one [REFLECTION_RESULT] block per check.
""")
