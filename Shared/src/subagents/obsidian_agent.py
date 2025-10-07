"""
Obsidian Agent - Personal Knowledge Base Integration

Integrates with the Obsidian MCP server to search and retrieve information
from the user's Obsidian vault (personal notes, research, meeting summaries).
"""

import os
from typing import Dict, Any, List
from langchain_core.tools import StructuredTool

# Import MCP client utility
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.mcp_client import create_mcp_tools


def _get_obsidian_tools() -> List[StructuredTool]:
    """
    Connect to local Obsidian MCP server and get tools.

    Uses stdio transport to access Obsidian vault search tools.

    Returns:
        List of LangChain tools from Obsidian MCP server
    """
    # MCP server configuration
    server_name = "obsidian"
    command = "/path/to/python"  # Replace with actual Python path
    args = ["/path/to/main.py"]  # Replace with actual main.py path
    env = {
        "OBSIDIAN_CONFIG_PATH": os.getenv("OBSIDIAN_CONFIG_PATH", "")
    }

    # Validate config path is set
    if not env["OBSIDIAN_CONFIG_PATH"]:
        print("Warning: OBSIDIAN_CONFIG_PATH environment variable not set")
        return []

    # Create tools from MCP server with proper session management
    try:
        tools = create_mcp_tools(
            server_name=server_name,
            command=command,
            args=args,
            env=env,
            transport="stdio"
        )
        return tools
    except Exception as e:
        print(f"Warning: Could not connect to Obsidian MCP server: {e}")
        return []


def create_obsidian_subagent(tools_dict: Dict[str, StructuredTool]) -> Dict[str, Any]:
    """
    Create the Obsidian vault subagent configuration with MCP tools.

    This agent connects to the local Obsidian MCP server to search the user's
    personal knowledge base via stdio transport.

    Args:
        tools_dict: Dictionary to populate with Obsidian tools (key: tool_name, value: tool)

    Returns:
        Dict containing subagent configuration with:
        - name: Unique identifier for the subagent
        - description: When the orchestrator should use this agent
        - instructions: How to use Obsidian search tools effectively
        - tools: List of tool names (tools themselves added to tools_dict)
    """
    # Get Obsidian tools from MCP server
    obsidian_tools = _get_obsidian_tools()

    # Add tools to the shared tools dictionary
    tool_names = []
    for tool in obsidian_tools:
        tools_dict[tool.name] = tool
        tool_names.append(tool.name)

    return {
        "name": "obsidian-agent",
        "description": """Searches user's Obsidian vault for personal notes and research.

        Use this agent when you need:
        - Personal meeting notes or summaries
        - Previously written company research notes
        - Newsletter archives and highlights
        - Transcript annotations and insights
        - Personal investment theses or opinions
        - Historical context from past work
        - Tagged notes on specific topics
        - Connections via backlinks and references
        """,
        "prompt": """You are the Obsidian Vault Search Agent with access to the user's personal knowledge base.

        You have tools to:
        - Search notes by keywords, tags, and content
        - Retrieve specific files from the vault
        - Find notes by date ranges
        - Access notes via backlinks and connections
        - Search across different note types (research, meetings, highlights)

        When given a query:
        1. Identify relevant search terms and topics
        2. Determine which note types would be most valuable
        3. Use your tools to search the Obsidian vault
        4. Extract and summarize relevant information
        5. Cite specific notes and their dates

        Best Practices:
        - Always cite which notes you retrieved (filename and date)
        - For company research, search by company name and ticker
        - For meeting notes, search by date ranges and participants
        - Use tags to find thematically related notes
        - Leverage backlinks to find connected information
        - When quoting from notes, preserve the user's original insights
        - Provide context about when notes were written

        Remember: These are the user's personal notes and opinions.
        Clearly attribute insights to the user when relevant.
        """,
        "tools": tool_names
    }
