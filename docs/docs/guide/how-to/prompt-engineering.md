# Prompt Engineering

Prompt engineering is the practice of designing and refining the inputs (prompts) given to large language models (LLMs) to produce accurate, relevant, and well-structured outputs. As LLMs become more capable, the quality of your prompts increasingly determines the quality of your results.

## What is Prompt Engineering?

A **prompt** is the text you feed into an LLM — it can be a simple question, a set of instructions, or a complex template with multiple variables. Prompt engineering is the process of iteratively crafting these inputs to:

- Improve response accuracy and relevance
- Reduce hallucinations and off-topic answers
- Control output format, tone, and style
- Guide the model through multi-step reasoning tasks via structured frameworks
- Enforce safety and content boundaries
- **Never** substitute for security enforcement — LLMs are inherently uncontrollable

> **Key insight**: Modern LLMs are incredibly capable, but they are also impressionable. A well-designed prompt can make a mediocre model perform well; a poorly-designed prompt can make a great model produce nonsense.

## Core Principles

### Two Scenarios: Task Agent vs. Chat Agent

Prompt engineering strategies differ fundamentally based on what you are building:

|                  | **Task Agent**                                                     | **Chat Agent**                                   |
| ---------------- | ------------------------------------------------------------------ | ------------------------------------------------ |
| **Goal**         | Execute a structured workflow (tool calls, RAG, data processing)   | Natural conversation with the user               |
| **Prompt style** | Protocol-driven: modes, phases, strict output format               | Conversational: tone, brevity, personality hints |
| **Key concern**  | Reliability — the model must follow the protocol                   | Engagement — the model should feel natural       |
| **Example**      | Code review bot, data extraction pipeline, customer support triage | AI companion, creative writing assistant         |

**Temperature guidance**:

- **Task Agent**: `temperature = 0.0 – 0.3`. Low temperature maximizes deterministic behavior — critical when the model must follow a protocol or produce structured output (JSON, tool calls).
- **Chat Agent**: `temperature = 0.5 – 0.9`. Higher temperature introduces variability for natural, engaging conversation. Avoid >1.0 unless you explicitly want chaotic outputs.

The principles below (§2.1–§2.7) apply to both scenarios, but their relative importance shifts: **task agents** prioritize structure constraints (§2.2, §2.6) and execution frameworks (§2.4); **chat agents** prioritize clarity (§2.1), examples (§2.5), and tone control (§2.3).

### Be Clear and Specific

Vague prompts produce vague answers. Replace "Tell me about AI" with "Explain the difference between supervised and unsupervised learning, with two real-world examples for each."

```text
# ❌ Vague
Tell me about Python.

# ✅ Specific
Explain Python's async/await syntax with three code examples, covering:
1. Basic coroutine definition and execution
2. Concurrent HTTP requests with asyncio.gather
3. Common pitfalls and how to avoid them
```

### Use Structured Instructions

Break complex tasks into numbered steps or bullet points. The model follows explicit structure much better than implicit expectations.

```text
You are a code reviewer. For each code snippet provided:

1. Identify potential bugs and edge cases
2. Suggest performance improvements
3. Check adherence to PEP 8 style guidelines
4. Provide a refactored version if applicable

Format your response as:
- **Issues Found**: (list)
- **Improvements**: (list)
- **Refactored Code**: (code block, if needed)
```

### Understand Personas: Language Style, Not Knowledge Injection

Role-playing ("You are a senior Python developer") is a **language style constraint** — it shapes tone, vocabulary, and output conventions. It does **not** inject domain knowledge or transform a general-purpose LLM into a subject-matter expert.

Modern LLMs are already optimized for domain knowledge at the model level (via pre-training and post-training). Telling the model to "act like an expert" adds little beyond stylistic framing. For task agents, prefer **behavioral rules and modes** over personas:

```text
# ❌ Persona as fake expertise (unnecessary on modern LLMs)
You are a world-class security researcher with 20 years of experience.

# ✅ Persona as style constraint (legitimate use)
Use a professional, concise tone. Prefer bullet points. Avoid markdown.

# ✅ Behavioral rules (for task agents)
## Information Processing Mode
<rule>Only use tools explicitly provided in the current session.</rule>
<rule>Output must be strict JSON tool call format.</rule>

## Daily Conversation Mode
<rule>Output must use natural, lively language.</rule>
<rule>Keep responses concise, within four to six sentences.</rule>
```

Key distinction:

- **Style personas** (tone, length, formatting) — legitimate, testable
- **Expertise personas** ("you are an expert in X") — unnecessary; the model already knows X if it's in its training data
- **Behavioral rules** (modes, protocols, constraints) — more reliable than either for task agents

```text
# ❌ Persona-based (unreliable on modern LLMs)
You are a senior backend engineer. Explain everything with analogies.

# ✅ Rule-based (mode-driven)
## Information Processing Mode
<rule>Only use tools explicitly provided in the current session.</rule>
<rule>Output must be strict JSON tool call format: {"name": "...", "arguments": {...}}</rule>

## Daily Conversation Mode
<rule>Output must use natural, lively language.</rule>
<rule>Keep responses concise, within four to six sentences.</rule>
```

Key principles:

- **Modes over personas** — define "what to do when" rather than "who you are"
- **Rules over suggestions** — use `<rule>` tags or bullet lists, not polite requests
- **Constraints over character** — specify format, length, and forbidden behaviors explicitly

### Design Execution Frameworks, Not Surface-Level Triggers

Modern LLMs are already well-optimized for internal reasoning — simply adding "think step by step" yields diminishing marginal returns, not because the model is worse at reasoning but because it already reasons well without the nudge.

Instead, **decompose the task into an explicit execution framework**: named stages with clear input/output contracts for each stage. This gives the model a protocol to follow rather than a vague nudge:

```text
# ❌ Vague trigger
Think step by step and solve the problem.

# ✅ Explicit execution framework with named stages
Process this task in three stages:

STAGE 1 — UNDERSTAND: Restate the problem in your own words.
  Output: a single paragraph.

STAGE 2 — SOLVE: Work through the solution, showing each step.
  Output: numbered steps with intermediate results.

STAGE 3 — VERIFY: Check your answer. Does it satisfy all constraints?
  Output: confirmation or correction.
```

**Why this works**: Chain-of-Thought is an LLM-inherent capability, not something you add via prompting. What you _can_ control is the **execution protocol** — the sequence of named stages, their expected outputs, and the format the model must follow. The model uses its native reasoning within that structure. You define _what stages to follow_; the model decides _how to think within each stage_.

### Provide Examples (Few-Shot Prompting)

Show the model what you want by providing input-output examples. Even one or two examples can dramatically improve output quality and format consistency.

```text
Classify the sentiment of each review as positive, negative, or neutral.

Review: "The product arrived broken and customer service was unhelpful."
Sentiment: negative

Review: "Works exactly as described. Fast shipping too!"
Sentiment: positive

Review: "It's a laptop. Does laptop things."
Sentiment: neutral

Review: "Best purchase I've made all year. Highly recommend!"
Sentiment:
```

### Set Constraints and Boundaries

Explicitly state what the model should NOT do, what format to use, and any word/token limits. Constraints prevent unwanted behavior and keep outputs focused.

```text
Summarize the following article in exactly 3 bullet points.
- Each bullet must be no more than 20 words
- Do NOT include your own opinions or commentary
- Do NOT use the words "the article says" or "according to"
```

### LLMs Are Uncontrollable — Never Delegate Security

> **Critical principle**: LLMs are stochastic, non-deterministic systems. No prompt — no matter how carefully crafted — can **guarantee** the model will follow your instructions. Prompt engineering reduces error rates; it does not eliminate them.

**What this means in practice:**

- 🔴 **Never trust an LLM to make security decisions.** Any operation involving authentication, authorization, data access control, code execution, or financial transactions must be gated by a **manual approval step** — not by a prompt.
- 🔴 **Prompt-based "guardrails" are not security.** "Don't generate harmful content" in a prompt is a suggestion, not an enforcement mechanism. Use output validation, content filters, and sandboxes.
- 🔴 **Tool calls from LLMs are untrusted input.** Always validate tool arguments server-side before execution. Never pass LLM-generated SQL, shell commands, or file paths directly to system APIs.
- 🟡 **Assume the model will sometimes ignore instructions.** Design your system so that a single bad response does not cause catastrophic failure.

> AmritaCore provides **cookie security detection** and **content filtering hooks**, but these are defense-in-depth layers — not substitutes for manual approval of sensitive operations.

## Prompt Structure Patterns

### The Message Role System

Most LLM APIs use a multi-role message structure:

| Role        | Purpose                                                      |
| ----------- | ------------------------------------------------------------ |
| `system`    | Sets overall behavior, rules, and persona (highest priority) |
| `user`      | The actual query or instruction from the end user            |
| `assistant` | Previous model responses (used for conversation history)     |
| `tool`      | Results from tool/function calls                             |

**Best practice**: Put permanent instructions (persona, rules, output format) in the `system` message. Put task-specific queries in `user` messages.

### System Prompt Design

The system prompt is your most powerful tool — it persists across the entire conversation. A well-crafted system prompt should:

1. **Start with identity**: "You are an expert Python code reviewer..."
2. **Define behavior rules**: "Always explain why a change is needed..."
3. **Specify output format**: "Respond in JSON with keys: issues, suggestions..."
4. **Set boundaries**: "Never generate executable SQL without confirmation..."

### Context Window Management

LLMs have limited context windows. Plan your prompt structure accordingly:

- **Put the most important instructions first** — models pay more attention to early tokens
- **Trim conversation history** — remove irrelevant turns when approaching the limit
- **Summarize long documents** — don't pass raw 50-page PDFs; summarize or chunk them
- **Use tool calls** — for large datasets, provide tools rather than inline data

## Common Techniques

### Chain-of-Thought (CoT) and Execution Frameworks

**Chain-of-Thought is an LLM-inherent capability, not a prompt technique.** Some models are explicitly trained for it ("thinking" models like o1, DeepSeek-R1); others exhibit it naturally. You cannot "add" CoT to a model via prompting — you can only provide an **execution framework** that structures how the model applies its native reasoning.

The effective approach is to define explicit phases the model must work through, leveraging its built-in CoT to fill in each phase:

```text
Analyze this problem using four reasoning phases:

[analyze]  Restate the problem in your own words. Identify unknowns.
[plan]     List the steps needed to solve it, with formulas if applicable.
[execute]  Perform each step, showing calculations.
[verify]   Check your answer against the original problem.

Problem: A store has 120 apples. They sell 30% in the morning and 25%
of the remaining in the afternoon. How many apples are left?
```

> **Key distinction**: CoT is the model's internal process; the numbered phases are an **execution protocol** you impose. Don't conflate the two — "think step by step" is a language-style nudge, not CoT engineering.

### ReAct (Reasoning + Acting)

ReAct combines reasoning traces with action steps. The model alternates between thinking about what to do and executing tools to gather information.

```text
You have access to a search tool. For each question:
1. Think: What information do I need?
2. Act: Call the search tool
3. Observe: Analyze the search results
4. Think: Do I have enough to answer?
5. If yes, provide the answer. If no, search again.
```

### Self-Reflection

Ask the model to review and critique its own output. This catches errors and improves quality, especially useful for code generation and creative writing.

```text
After generating your answer, review it for:
1. Factual accuracy — are all claims supported?
2. Completeness — did I answer every part of the question?
3. Clarity — would a beginner understand this?

Then provide a revised version if needed.
```

### Tool-Use Prompts

When the model has access to tools/functions, your prompts should clearly specify when and how to use them:

```text
You have access to these tools:
- search_web(query: str) — Search the internet
- calculate(expression: str) — Evaluate a math expression

Rules:
- Use search_web for factual questions you're unsure about
- Use calculate for any math beyond basic arithmetic
- NEVER guess when a tool can give you the correct answer
```

## Prompt Engineering in AmritaCore

AmritaCore provides several mechanisms for prompt engineering at the framework level, enabling you to build prompts programmatically rather than manually.

### Jinja2 Template System

AmritaCore uses Jinja2 templates to render system prompts. The default template (`DEFAULT_TEMPLATE`) provides structure, but you can supply your own:

```python
from jinja2 import Template
from amrita_core import ChatObject
from amrita_core.types import Message

custom_template = Template("""
You are {{ role }} at {{ company }}.
Your expertise: {{ expertise }}

Rules:
{% for rule in rules %}
- {{ rule }}
{% endfor %}

Current date: {{ chatobj.timestamp }}
""")

chat = ChatObject(
    train=Message(role="system", content="Template base"),  # fallback content
    user_input="Hello!",
    session_id="session_123",
    train_template=custom_template,
    jinja2_vars={
        "role": "Senior Architect",
        "company": "TechCorp",
        "expertise": "Cloud infrastructure and microservices",
        "rules": [
            "Always explain trade-offs",
            "Provide code examples when relevant",
            "Keep answers concise but complete"
        ]
    }
)
```

> **Important**: `train_template` must be a `jinja2.Template` object, not a bare string. Use `Template(your_string)` to construct it.

**Built-in template variables**: `train`, `memory`, `chatobj`, `config` are automatically available. Avoid overriding them in `jinja2_vars`.

### The `train` System Message

The `train` parameter sets the system-level instruction for the entire conversation. AmritaCore's built-in `DEFAULT_INSTRUCTIONS` uses a **mode-driven, rule-based** style — no persona, no \"you are an expert\" — just concrete behavioral rules for each mode:

```python
# AmritaCore's approach: mode-driven, rule-based
# (simplified from actual DEFAULT_INSTRUCTIONS in consts.py)
from amrita_core import ChatObject
from amrita_core.types import Message

train_message = Message(
    role="system",
    content="""## Information Processing Mode
Activated when a task requires tool use. In this mode:
<rule>Only use tools explicitly provided by the system.</rule>
<rule>All output must be strict JSON tool call format.</rule>

## Daily Conversation Mode
Activated after obtaining information, or when chatting directly.
<rule>Output must use natural, lively language.</rule>
<rule>Keep responses concise, within four to six sentences.</rule>

## Mode Choice
Call the agent_stop tool to switch from Information Processing
to Daily Conversation mode, then provide the final response."""
)

chat = ChatObject(
    train=train_message,
    user_input="What is the weather today?",
    session_id="session_456",
)
```

> **Design philosophy**: Define **what the model should do in each mode**, not **who the model should pretend to be**. Modes and rules produce more consistent behavior than personas.

### Structured Reasoning Templates

When using `ReActAgentStrategy` with structured reasoning enabled, the framework uses a Jinja2 template (`STRUCTURED_REASONING_TEMPLATE` in `builtins/consts.py`) that provides a **phase-based reasoning framework** — not a persona or a \"think step by step\" trigger:

The template guides the model through phases:

1. **[analyze]** — understand the user input, identify requirements
2. **[plan]** — devise a strategy, choose tools
3. **[execute]** — carry out actions, call tools
4. **[verify]** — validate results against the goal

Configuration controls:

```python
from amrita_core.config import AmritaConfig

config = AmritaConfig()
config.builtin.react_config.reasoning_depth = 3  # max reasoning steps
config.builtin.react_config.tool_prediction = True  # predict needed tools
```

> **CoT vs execution framework**: Chain-of-Thought is the model's own internal reasoning process — you don't control it via prompts. What `STRUCTURED_REASONING_TEMPLATE` provides is an **execution protocol**: named phases, explicit output format, and a fixed reasoning taxonomy. The framework defines _what structure to follow_; the model's native CoT handles _how to think within that structure_.

### Prompt Engineering Best Practices for AmritaCore

1. **Design modes, not personas** — follow `DEFAULT_INSTRUCTIONS`: define what to do in each mode, not who the model should pretend to be
2. **Use `jinja2_vars` for dynamic content** — inject variables rather than rebuilding templates
3. **Leverage hooks for cross-cutting concerns** — use `PreCompletionEvent` for context injection, not hardcoded prefixes
4. **Use `on_post_process()` for final instructions** — separate \"gathering\" from \"summarizing\" logic
5. **Test prompts with different models** — the same prompt may produce different results across providers
6. **Start simple, iterate** — begin with a minimal prompt and add complexity only when needed
7. **Never delegate security to prompts** — LLM output must always be validated; sensitive operations require manual approval gates
