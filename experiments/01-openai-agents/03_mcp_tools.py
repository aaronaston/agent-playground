#!/usr/bin/env python3
"""
03_mcp_tools.py - Agent integrated with an MCP server.

This script demonstrates MCP (Model Context Protocol) integration:
1. Connect to an MCP server (stdio-based)
2. Agent discovers tools from the MCP server
3. Agent calls MCP tools like any other tool
4. View tool schema and execution traces

Key concepts:
- MCP Server: Exposes tools over a standardized protocol (stdio or HTTP)
- MCPServerStdio: Runs an MCP server as a subprocess (stdio transport)
- Tool Discovery: Agent fetches available tools from the MCP server at startup
- Tool Invocation: Same interface as function tools; SDK handles serialization/transport

MCP Server Examples:
- mcp-server-fetch: Web content fetching
- mcp-server-time: Time/timezone operations
- Filesystem server: Local file operations
- Custom servers: Implement your own using mcp library

Setup:
  For this example to work, you need an MCP server installed. Options:
  1. Install via uvx/npx (recommended for demos):
     - uvx mcp-server-fetch
     - uvx mcp-server-time
  
  2. Or install the Python package and uncomment dependencies in pyproject.toml

Common MCP transports:
- Stdio: Subprocess communication (mcp_server_command in env or code)
- HTTP: Remote/REST-based (url parameter)
- SSE: Server-sent events (url parameter with protocol)
"""

import os
import sys
from dotenv import load_dotenv

try:
    from openai_agents import Agent, Runner
    from openai_agents.mcp import MCPServerStdio
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure openai-agents is installed with MCP support.")
    sys.exit(1)

# Load environment
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL", "gpt-4o")
mcp_command = os.getenv("MCP_STDIO_COMMAND")  # e.g., "uvx mcp-server-time"

if not api_key:
    print("Error: OPENAI_API_KEY not set.")
    sys.exit(1)

def main():
    # If no MCP command in env, show usage
    if not mcp_command:
        print("MCP_STDIO_COMMAND not set in .env")
        print("\nExample configurations:")
        print("  MCP_STDIO_COMMAND=uvx mcp-server-time")
        print("  MCP_STDIO_COMMAND=uvx mcp-server-fetch")
        print("\nInstall via: pip install mcp-server-time, etc.")
        print("Or use uvx: uvx mcp-server-time")
        print("\nFor now, showing how the integration works...\n")
        demo_without_server()
        return
    
    print(f"Connecting to MCP server: {mcp_command}")
    print("="*60 + "\n")
    
    try:
        # Create an MCP server connection using stdio transport
        mcp_server = MCPServerStdio(
            command=mcp_command.split(),  # Shell command to start server
        )
        
        # Create agent with MCP tools
        agent = Agent(
            model=model,
            instruction="You are a helpful assistant with access to MCP tools.",
            tools=[mcp_server],  # Pass the MCP server as a tool provider
        )
        
        # Define a task
        task = "What time is it? Please use the time tool."
        
        print(f"Task: {task}\n")
        
        # Run the agent
        runner = Runner(agent=agent)
        final_state = runner.run_sync(task=task)
        
        # Print results
        print("\n" + "="*60)
        print("Execution Trace:")
        print("="*60 + "\n")
        
        for i, message in enumerate(final_state.messages):
            role = message.get("role", "unknown")
            content = message.get("content", "")
            print(f"[{role.upper()}]: {content}")
        
        print("\nMCP integration complete!")
        
    except Exception as e:
        print(f"Error connecting to MCP server: {e}")
        print("Make sure the MCP server is available and the command is correct.")
        print("\nTroubleshooting:")
        print("  1. Check MCP_STDIO_COMMAND in .env")
        print("  2. Verify the server binary is installed (uvx or pip)")
        print("  3. Try: uvx mcp-server-time --help")

def demo_without_server():
    """
    Show the structure without an actual MCP server.
    Useful for understanding the pattern when server isn't available.
    """
    print("Demo: MCP Server Integration Pattern")
    print("-" * 60)
    print("""
How MCP integration works:

1. Create an MCP server connection:
   mcp_server = MCPServerStdio(command=["uvx", "mcp-server-time"])
   
   Or HTTP-based:
   mcp_server = MCPServerHTTP(url="http://localhost:8000")

2. Pass to Agent:
   agent = Agent(
       model="gpt-4o",
       tools=[mcp_server],  # MCP servers are tool providers
   )

3. Agent discovers tools from the MCP server and calls them:
   runner = Runner(agent=agent)
   state = runner.run_sync(task="Use the time tool")

4. The SDK handles:
   - Stdio/HTTP transport
   - Tool schema discovery
   - Tool invocation and result handling
   - Error management

Key Differences from Function Tools:
- Function tools: Defined in Python, always available
- MCP tools: Fetched at runtime, server-defined, transport overhead
- Same interface to agent: Agent doesn't care about the source
    """)

if __name__ == "__main__":
    main()
