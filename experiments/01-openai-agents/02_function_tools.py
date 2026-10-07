#!/usr/bin/env python3
"""
02_function_tools.py - Agent with function-decorated tools.

This script demonstrates tool definition and invocation:
1. Define tools using @function_tool decorator
2. Agent automatically calls tools when needed
3. View the tool-calling loop and trace

Key concepts:
- @function_tool: Decorator that turns a Python function into an OpenAI tool
- Tool schema: Automatically generated from function signature and docstring
- Tool calling loop: Agent decides when to call tools based on the task
- Tool results: Fed back into the agent for next iteration

"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from openai_agents import Agent, Runner, function_tool

# Load environment variables
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL", "gpt-4o")

if not api_key:
    print("Error: OPENAI_API_KEY not set.")
    sys.exit(1)

# Define tools using @function_tool decorator
# The decorator extracts the function signature and docstring as tool schema

@function_tool
def get_time():
    """
    Get the current time.
    Returns a string with the current date and time.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@function_tool
def calculator(operation: str, a: float, b: float) -> float:
    """
    Perform a basic arithmetic operation.
    
    Args:
        operation: One of 'add', 'subtract', 'multiply', 'divide'
        a: First number
        b: Second number
    
    Returns:
        The result of the operation
    """
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            return "Error: Division by zero"
        return a / b
    else:
        return "Error: Unknown operation"

def main():
    # Create an Agent with access to our tools
    # The agent will automatically discover and use these tools
    agent = Agent(
        model=model,
        instruction="You are a helpful assistant. Use tools when needed to answer questions.",
        tools=[get_time, calculator],  # Pass tool functions here
    )
    
    # Define a task that requires using tools
    task = "What time is it now? Also, what is 15 * 3 + 8?"
    
    print(f"Task: {task}")
    print("\n" + "="*60)
    print("Running agent with tools...")
    print("="*60 + "\n")
    
    # Execute the agent
    runner = Runner(agent=agent)
    final_state = runner.run_sync(task=task)
    
    # Print the execution trace
    print("\n" + "="*60)
    print("Execution Trace:")
    print("="*60 + "\n")
    
    for i, message in enumerate(final_state.messages):
        role = message.get("role", "unknown")
        content = message.get("content", "")
        
        # Pretty-print different message types
        if role == "user":
            print(f"[User {i}]: {content}")
        elif role == "assistant":
            print(f"[Assistant {i}]: {content}")
        elif role == "tool":
            print(f"[Tool Result {i}]: {content}")
        else:
            print(f"[{role.upper()} {i}]: {content}")
        print()
    
    print("="*60)
    print("\nAgent completed successfully!")
    print(f"Total turns: {len(final_state.messages)}")

if __name__ == "__main__":
    main()
