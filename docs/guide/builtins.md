# Built-in Capabilities of AmritaCore

## 9.1 Built-in Tools

AmritaCore provides several built-in tools to support core behaviors of intelligent agents. These tools are internally defined in the framework to implement specific functions.

### 9.1.1 STOP_TOOL (Stop Tool)

`STOP_TOOL` is a built-in tool used to indicate that the agent has collected sufficient information and is ready to form the final answer. When this tool is called, the agent should not call any other tools but directly provide the completion.

- **Name**: `agent_stop`
- **Description**: Indicates that information collection is complete and the final answer is ready to be generated
- **Parameters**:
  - `result` (optional): Briefly explains what was accomplished during the chat task

### 9.1.2 REASONING_TOOL (Reasoning Tool)

`REASONING_TOOL` is used to think about what should be done next, typically called after completing a tool call to reflect on the next steps. This tool is crucial for implementing autonomous decision-making in intelligent agents.

- **Name**: `think_and_reason`
- **Description**: Think about what should be done next
- **Parameters**:
  - `content`: Describe what needs to be done next

### 9.1.3 PROCESS_MESSAGE (Process Message Tool)

`PROCESS_MESSAGE` is used to describe what the agent is currently doing and express the agent's internal thoughts to the user. Use this tool when you need to communicate current operations or internal reasoning to the user, not for general completion.

- **Name**: `processing_message`
- **Description**: Describe what the agent is currently doing and express internal thoughts to the user
- **Parameters**:
  - `content`: Message content, described in the tone of system instructions what is being done or how the user is being interacted with

## 9.2 Built-in Adapters

AmritaCore provides a built-in OpenAI adapter for interacting with the OpenAI API.

### 9.2.1 OpenAIAdapter

`OpenAIAdapter` is a model adapter that implements communication protocols with the OpenAI API. The adapter supports:

- **API Calls**: Asynchronous calls to the OpenAI API to get chat responses
- **Streaming Responses**: Supports streaming responses for real-time content output
- **Tool Calling**: Supports OpenAI's function calling capabilities
- **Usage Statistics**: Tracks API call usage information

The adapter's main functions include:
1. Creating asynchronous OpenAI client connections
2. Processing streaming or non-streaming responses based on configuration
3. Parsing and validating API responses
4. Handling tool call requests

## 9.3 Built-in Agent System

AmritaCore includes an intelligent agent system capable of autonomously using tools to complete tasks.

### 9.3.1 Agent Workflow

The agent system follows this workflow:

1. **Reasoning Phase**: The agent first analyzes task requirements and determines the next action
2. **Tool Selection**: Selects appropriate tools based on the current situation
3. **Tool Execution**: Executes the selected tools
4. **Result Evaluation**: Evaluates the results of tool execution
5. **Iterative Execution**: Repeats the above steps until the goal is achieved
6. **Completion**: Uses `STOP_TOOL` to end the task

### 9.3.2 Agent Configuration Options

Agent behavior can be adjusted through configuration:

- **Thought Mode**: Configurable whether the agent uses the reasoning tool for thinking
- **Tool Call Limit**: Limits the number of consecutive tool calls to prevent infinite loops
- **Intermediate Messages**: Controls whether intermediate processing messages from the agent are displayed
- **Error Handling**: Defines strategies for handling tool execution failures