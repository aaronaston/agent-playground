#!/usr/bin/env python3
"""
01_hello_agent.py - Minimal OpenAI Agents SDK example.

This script demonstrates the basic Agent and Runner lifecycle:
1. Create an Agent with a task/prompt
2. Use Runner.run_sync() to execute it
3. Retrieve and print the final result

Key concepts:
- Agent: The entity that takes a prompt and runs a tool-calling loop
- Runner: Executes the agent and returns the final state
- Synchronous execution: run_sync() blocks until complete
"""

import os
import sys
from dotenv import load_dotenv
from openai_agents import Agent, Runner

# Load environment variables from .env file
load_dotenv()

# Get configuration from environment
api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL", "gpt-4o")

if not api_key:
    print("Error: OPENAI_API_KEY not set. Please configure .env file.")
    sys.exit(1)

def main():
    # Define a simple task for the agent
    task = "What is 2 + 2? Just give me the final answer."
    
    # Create an Agent
    # - model: which OpenAI model to use
    # - instruction: system-level instruction for the agent (optional)
    agent = Agent(
        model=model,
        instruction="You are a helpful math assistant. Solve problems step by step.",
    )
    
    # Create a Runner to execute the agent
    # - run_sync() blocks until the agent finishes
    # - Returns the final RunState with results
    print(f"Running agent with task: {task}")
    print("-" * 60)
    
    runner = Runner(agent=agent)
    final_state = runner.run_sync(task=task)
    
    print("-" * 60)
    print("\n=== Final Result ===")
    
    # The final_state contains the agent's output
    # Access the last message or final output
    if final_state.messages:
        last_message = final_state.messages[-1]
        print(f"Agent response: {last_message.content}")
    else:
        print("No response from agent.")
    
    print(f"\nTotal messages exchanged: {len(final_state.messages)}")

if __name__ == "__main__":
    main()
