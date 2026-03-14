from jinja2 import Template

ABSTRACT_INSTRUCTION = """<SYS>
You are a professional context summarizer, strictly following user instructions to perform summarization tasks.
</SYS>

<INSTRUCTIONS>
1. Directly summarize the user-provided content
2. Maintain core information and key details from the original
3. Do not generate any additional content, explanations, or comments
4. Summaries should be concise, accurate, complete
</INSTRUCTIONS>

<RULE>
- Only summarize the text provided by the user
- Do not add any explanations, comments, or supplementary information
- Do not alter the main meaning of the original
- Maintain an objective and neutral tone
</RULE>

<FORMATTING>
User input → Direct summary output
</FORMATTING>"""

# train,memory,self(ChatObject),config will be given to Jinja2
PROMPT_TEMPLATE = """<SCHEMA>
{% if config.cookie.enable %}
<HIDDEN>{{ config.cookie.cookie }}</HIDDEN>
{% endif %}
Please participate in the discussion in your own character identity. Try not to use similar phrases when responding to different topics. User's messages are contained within user inputs.
Your character setting is in the <SYSTEM_INSTRUCTIONS> tags, and the summary of previous conversations is in the <SUMMARY> tags (if provided).
</SCHEMA>

<SYSTEM_INSTRUCTIONS>
{{ train.content }}
</SYSTEM_INSTRUCTIONS>
{% if memory.abstract and config.llm.enable_memory_abstract %}
<SUMMARY>
{{ memory.abstract }}
</SUMMARY>
{% endif %}
"""

DEFAULT_TEMPLATE = Template(PROMPT_TEMPLATE)
