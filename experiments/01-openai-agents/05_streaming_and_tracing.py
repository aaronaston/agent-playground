#!/usr/bin/env python3
"""
05_streaming_and_tracing.py - Streaming events and observability.

This script demonstrates:
1. Stream events as the agent executes (real-time feedback)
2. Inspect trace information (thoughts, tool calls, results)
3. Understand event types and timing

Key concepts:
- Streaming: run_streamed() yields events instead of blocking
- Events: Represent steps in the agent's execution (thought, tool call, result, etc.)
- Tracing: Built-in logging of prompts, responses, tools, and state
- Observability: Tools to understand what the agent is doing and debug issues

Event types (typical):
- message_start: Agent begins processing
- content_block_start/delta: Streaming token output
- content_block_stop: Content block complete
- tool_use: Agent calls a tool
- tool_result: Tool returns a result
- message_stop: Agent completes a turn
"""

import os
import sys
from dotenv import load_dotenv
from openai_agents import Agent, Runner, function_tool

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL", "gpt-4o")

if not api_key:
    print("Error: OPENAI_API_KEY not set.")
    sys.exit(1)

# Simple tool for demonstration
@function_tool
def search(query: str) -> str:
    """
    Simulate a search (mock implementation).
    Returns a mock search result.
    """
    results = {
        "python": "Python is a high-level programming language.",
        "agent": "An agent is an autonomous entity that acts in an environment.",
        "openai": "OpenAI is an AI research company.",
    }
    return results.get(query.lower(), f"No results for '{query}'")

def main():
    # Create agent with a tool
    agent = Agent(
        model=model,
        instruction="You are a helpful research assistant. Use tools to find information.",
        tools=[search],
    )
    
    # Define a task that will involve multiple steps
    task = "Tell me about Python and agents. Use the search tool."
    
    print(f"Task: {task}")
    print("\n" + "="*60)
    print("Streaming Events (Real-time Execution):")
    print("="*60 + "\n")
    
    # Use run_streamed to get events as they occur
    # (Note: run_streamed may not be available in all SDK versions;
    #  fallback to run_sync and inspect final_state.trace if needed)
    runner = Runner(agent=agent)
    
    # Attempt streaming; fall back to sync if not available
    try:
        event_count = 0
        for event in runner.run_streamed(task=task):
            event_count += 1
            print(f"[Event {event_count}] {format_event(event)}")
            print()
    except AttributeError:
        # run_streamed not available; use run_sync and trace
        print("(run_streamed not available in this SDK version)")
        print("Falling back to synchronous execution with trace inspection.\n")
        
        final_state = runner.run_sync(task=task)
        print_sync_trace(final_state)

def format_event(event):
    """
    Format an event for readable output.
    Events are typically dicts with type, content, tool_use, etc.
    """
    if isinstance(event, dict):
        event_type = event.get("type", "unknown")
        content = event.get("content", "")
        
        if event_type == "content_block_start":
            return f"Content Block Started (type: {event.get('content_block', {}).get('type', '?')})"
        elif event_type == "content_block_delta":
            delta = event.get("delta", {})
            text = delta.get("text", "")
            return f"Content Block Delta: {text[:50]}..."
        elif event_type == "tool_use":
            tool_use = event.get("tool_use", {})
            return f"Tool Use: {tool_use.get('name')}({tool_use.get('input', {})})"
        elif event_type == "tool_result":
            return f"Tool Result: {event.get('result', '')[:60]}..."
        elif event_type == "message_start":
            return "Message Started"
        elif event_type == "message_stop":
            return "Message Completed"
        else:
            return f"Event [{event_type}]: {content[:50] if content else '(no content)'}..."
    else:
        return f"Event: {str(event)[:60]}..."

def print_sync_trace(final_state):
    """
    Print trace information from a synchronous run.
    This gives visibility into the execution even without streaming.
    """
    print("Final State Summary:")
    print("-" * 60)
    
    if hasattr(final_state, "messages"):
        print(f"\nTotal messages: {len(final_state.messages)}")
        for i, msg in enumerate(final_state.messages):
            role = msg.get("role", "unknown") if isinstance(msg, dict) else "message"
            content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
            print(f"\n[{i}] {role.upper()}:")
            print(f"    {content[:100]}..." if len(str(content)) > 100 else f"    {content}")
    
    # Check for additional trace info
    if hasattr(final_state, "trace"):
        print("\n" + "-" * 60)
        print("Trace Info Available:")
        print(final_state.trace)

def demo_tracing_dashboard():
    """
    Note about the built-in tracing dashboard.
    """
    print("\n" + "="*60)
    print("Tracing Dashboard")
    print("="*60)
    print("""
The OpenAI Agents SDK provides a built-in tracing dashboard:

1. Access the dashboard at: [SDK docs or localhost:PORT]
2. View:
   - Prompts sent to LLM
   - Tool calls and results
   - Agent reasoning/thoughts
   - Latency and performance

3. Enable with environment variables or configuration
   (see SDK docs for exact setup)

This is useful for:
- Debugging agent behavior
- Understanding tool call patterns
- Identifying bottlenecks
- Learning how the agent reasons
    """)

if __name__ == "__main__":
    main()
    demo_tracing_dashboard()
