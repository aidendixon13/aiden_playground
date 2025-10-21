# Agentic Scratch Orchestrator

A test orchestrator for experimenting with agentic tool-calling behavior, modeled after the DataRetrievalOrchestrator pattern.

## Overview

This orchestrator demonstrates a complete agentic workflow where an LLM can:
1. Use tools iteratively to gather information
2. Make multiple tool calls as needed
3. Signal completion when the task is done

## Architecture

### Key Components

```
agentic_scratch/
├── state.py                           # State model with conversation & tool tracking
├── factory.py                         # Factory for creating tool nodes and states
├── agentic_scratch_orchestrator.py    # Main orchestrator
├── test_agentic_scratch.py           # Test runner
├── callers/
│   └── agentic_scratch_caller.py     # LLM caller config with system prompt
├── nodes/
│   ├── initial_node.py               # Sets up conversation
│   └── core_node.py                  # Agentic loop (like DataRetrievalOrchestrator)
└── tools/
    ├── search_tool.py                # Search tool definition
    ├── search_tool_node.py           # Search tool node implementation
    ├── process_tool.py               # Process/completion tool definition
    └── process_tool_node.py          # Process tool node implementation
```

### Graph Flow

```
StartNode
    ↓
InitialNode (setup conversation)
    ↓
CoreNode (agentic loop) ←──────────┐
    ↓                               │
  [Has tool calls?]                 │
    ↓                               │
PlaceHolderNode (routing)           │
    ↓                               │
  [Route to tool nodes]             │
    ├─→ SearchToolNode ─────────────┤
    └─→ ProcessToolNode ────────────┤
         (exits after this)
    ↓
EndNode
```

## Pattern Comparison

### Similar to DataRetrievalOrchestrator:
- ✅ State with `conversation`, `tool_calls`, `tool_results`
- ✅ `tool_results_reducer` for parallel tool execution
- ✅ `CoreNode` implements agentic loop with exit condition
- ✅ `PlaceHolderNode` for routing tool calls
- ✅ Factory pattern for tool nodes and states
- ✅ Parallel tool support via `Send`
- ✅ Tools return `ToolMessage` objects
- ✅ Conditional edges for flow control

### Simplified from DataRetrievalOrchestrator:
- Only 2 tools (SearchTool, ProcessTool) vs 5+ tools
- No HIL (Human-in-Loop) support
- No complex dependencies (no UOWs, index managers, etc.)
- Simpler state model

## Tools

### SearchTool
- **Purpose**: Search for information
- **Input**: `query` (str)
- **Output**: Mock search results
- **Can be called multiple times**: Yes

### ProcessTool
- **Purpose**: Complete the task with a summary
- **Input**: `summary` (str)
- **Output**: Completion message
- **Exits after calling**: Yes (like BuildReportTool)

## Exit Condition

The orchestrator exits when:
```python
if (
    graph_state.tool_calls
    and graph_state.tool_calls[0].content.name == ProcessTool.name
    and graph_state.tool_results
):
    return {"tool_calls": []}  # Exit the loop
```

This mirrors the DataRetrievalOrchestrator pattern where BuildReportTool signals completion.

## Usage

Run the test:
```bash
cd /wernicke
python3 experimentation/aiden_playground/agentic_scratch/test_agentic_scratch.py
```

### Reasoning Output

The orchestrator captures and displays reasoning from the LLM:
- Uses GPT-5 with reasoning mode enabled (`effort: "low"`, `summary: "auto"`)
- Prints reasoning summaries to console with `💭 REASONING:` prefix
- Shows the model's thought process before each tool call

### LangSmith Tracing

The test includes full LangSmith tracing support:
- Automatically detects if `LS_TRACING=true` is set in environment
- Creates a unique trace ID for each run
- Tags traces with `AgenticScratchOrchestrator`, `test`, and `agentic_scratch`
- Displays trace ID and project name after execution
- Reasoning traces are also captured in LangSmith

To enable tracing:
```bash
export LS_TRACING=true
export LANGCHAIN_PROJECT=your-project-name
```

Example queries to test:
- "Search for Python and then summarize what you found"
- "Search for AI tools, then search for coding best practices, then complete the task"
- "Find information about FastAPI and LangGraph"

## Key Patterns Demonstrated

1. **Tool Reducer**: Handles parallel tool results with append/rewrite modes
2. **Factory Pattern**: Dynamic tool routing based on tool name
3. **Conditional Routing**: `_finish_agent_conditional` and `_send_tools_conditional`
4. **Exit Signals**: Tools can signal task completion via specific tool calls
5. **Conversation Management**: Tools return `ToolMessage` objects that get added to conversation
6. **Parallel Execution**: Multiple tools can run in parallel via `Send`

## Extending

To add a new tool:
1. Create tool definition in `tools/your_tool.py` (inherit from `ITool`)
2. Create tool node in `tools/your_tool_node.py` (inherit from `INode`)
3. Create tool state model in the node file
4. Add to `factory.py`:
   - `tool_call_node_factory`
   - `tool_call_state_model_factory`
5. Register in orchestrator's `compile_graph`
6. Document in system prompt (`callers/agentic_scratch_caller.py`)

## Testing

The test file (`test_agentic_scratch.py`) demonstrates:
- Orchestrator initialization
- State setup
- Running the agentic loop
- Displaying tool results and final output

