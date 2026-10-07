#!/usr/bin/env python3
"""
04_handoffs_and_agents_as_tools.py - Agent composition patterns.

This script demonstrates two ways agents can delegate work:

1. HANDOFFS: One agent explicitly requests to hand off to another agent.
   Typical use: Triage agent routes to specialists
   Flow: Agent detects need → Calls handoff → Runner processes → Continues

2. AGENTS AS TOOLS: Wrap an agent as a tool and call it like a function.
   Typical use: One agent calls another as a subtask
   Flow: Agent calls agent.as_tool() → Treated like any tool → Returns result

Key concepts:
- Handoff: Built-in handoff mechanism; cleaner for sequential delegation
- Agents-as-tools: More flexible; agent becomes callable like any tool
- When to use each: Depends on whether you want sequential flow vs. composable tools
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

# Define some helper tools for specialists

@function_tool
def solve_math(problem: str) -> str:
    """
    Solve a math problem (simplified example).
    Args: problem description
    Returns: solution
    """
    # Simplified: just return a canned response
    return f"Solving math problem: {problem} → Answer: 42"

@function_tool
def answer_trivia(question: str) -> str:
    """
    Answer a trivia question.
    Args: question
    Returns: answer
    """
    return f"Trivia answer for '{question}': The answer is known!"

def create_math_specialist():
    """
    Create a specialist agent for math problems.
    """
    return Agent(
        model=model,
        instruction="You are a math expert. Solve math problems accurately.",
        tools=[solve_math],
    )

def create_trivia_specialist():
    """
    Create a specialist agent for trivia.
    """
    return Agent(
        model=model,
        instruction="You are a trivia expert. Answer questions with confidence.",
        tools=[answer_trivia],
    )

def demo_agents_as_tools():
    """
    Demonstrate wrapping agents as tools.
    """
    print("\n" + "="*60)
    print("PATTERN 1: Agents as Tools")
    print("="*60 + "\n")
    
    # Create specialist agents
    math_agent = create_math_specialist()
    trivia_agent = create_trivia_specialist()
    
    # Wrap agents as tools
    # agent.as_tool() returns a callable that can be passed to another agent
    math_tool = math_agent.as_tool(name="math_solver", description="Solves math problems")
    trivia_tool = trivia_agent.as_tool(name="trivia_answerer", description="Answers trivia questions")
    
    # Create a router agent that uses specialist agents as tools
    router = Agent(
        model=model,
        instruction="You are a helpful assistant. Route tasks to specialists.",
        tools=[math_tool, trivia_tool],
    )
    
    # Give the router a mixed task
    task = "I have two questions: What is 15 + 27? And: Who was the first president of the US?"
    
    print(f"Task: {task}\n")
    
    runner = Runner(agent=router)
    final_state = runner.run_sync(task=task)
    
    print("\nRouter's Response:")
    if final_state.messages:
        print(final_state.messages[-1].get("content", "No response"))

def demo_handoffs():
    """
    Demonstrate handoff pattern.
    Note: Actual handoff implementation may vary by SDK version.
    This shows the conceptual pattern.
    """
    print("\n" + "="*60)
    print("PATTERN 2: Handoffs (Conceptual Example)")
    print("="*60 + "\n")
    
    print("""
Handoffs are used when an agent explicitly transfers control to another:

    Triage Agent (receives user request)
           ↓
      Analyzes type
           ↓
    Hands off to → Math Specialist (if math)
              OR → Trivia Specialist (if trivia)
           ↓
      Specialist solves
           ↓
      Returns to Triage (if configured)

Implementation Notes:
- Agent can request a handoff when it determines another agent is needed
- Handoff is explicit in the agent's instruction/tool
- Runner detects handoff and routes to the appropriate agent
- May be sequential or can return to original agent

Example with SDK:
    @function_tool
    def handoff_to_math_specialist(problem: str) -> str:
        agent = create_math_specialist()
        return runner.run_sync(agent=agent, task=problem).final_message
    
    triage_agent = Agent(
        model=model,
        tools=[handoff_to_math_specialist],
        instruction="Route math problems to the specialist."
    )

Handoff vs. Agents-as-Tools:
- Handoff: Better for sequential workflows, clearer intent
- Agents-as-tools: More flexible, composable, agent-agnostic
    """)

def main():
    print("Agent Composition Patterns")
    print("\nDemonstrating two approaches to agent delegation.\n")
    
    # Demo agents-as-tools
    demo_agents_as_tools()
    
    # Demo handoffs concept
    demo_handoffs()
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print("""
Use agents-as-tools when:
  - You want a flexible, composable agent architecture
  - Specialists can work independently
  - You want to reuse agents across different contexts

Use handoffs when:
  - You have a clear sequential workflow
  - One agent explicitly needs to defer to another
  - You want clear routing/delegation semantics
    """)

if __name__ == "__main__":
    main()
