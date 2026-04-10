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

REASONING_TEMPLATE = Template(""""
Please analyze the task requirements based on the user input above,summarize the current step's purpose and reasons, and execute accordingly.
If no task needs to be performed, no description is needed;
please analyze according to the character tone set in <ROLE_SETTINGS> (if present).
{% if last_step %}
Your previous task was:

```text
{{last_step}}
```
{% endif %}
{% if original_msg %}
<INPUT>
{{original_msg|escape}}
</INPUT>
{% endif %}
<ROLE_SETTINGS>
{{stg.ctx.get_original_context().train.content}}
</ROLE_SETTINGS>
""")
