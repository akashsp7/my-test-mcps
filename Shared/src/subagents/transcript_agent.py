"""
Transcript Agent - Earnings Call Transcript Search Integration

Integrates with the SuperSearch MCP server to search and retrieve earnings
call transcripts, management commentary, and analyst Q&A sections.
"""

import os
from typing import Dict, Any, List
from langchain_core.tools import StructuredTool

# Import MCP client utility
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.mcp_client import create_mcp_tools


def _get_transcript_tools() -> List[StructuredTool]:
    """
    Connect to local SuperSearch MCP server and get tools.

    Uses stdio transport to access transcript search tools.

    Returns:
        List of LangChain tools from SuperSearch MCP server
    """
    # MCP server configuration
    server_name = "supersearch"
    command = "/path/to/python"  # Replace with actual Python path
    args = ["/path/to/supersearch_mcp.py"]  # Replace with actual script path
    env = {
        "TRANSCRIPT_DIR": os.getenv("TRANSCRIPT_DIR", "")
    }

    # Validate transcript directory is set
    if not env["TRANSCRIPT_DIR"]:
        print("Warning: TRANSCRIPT_DIR environment variable not set")
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
        print(f"Warning: Could not connect to SuperSearch MCP server: {e}")
        return []


def create_transcript_subagent(tools_dict: Dict[str, StructuredTool]) -> Dict[str, Any]:
    """
    Create the Transcript Search subagent configuration with MCP tools.

    This agent connects to the local SuperSearch MCP server to search earnings
    call transcripts via stdio transport.

    Args:
        tools_dict: Dictionary to populate with transcript tools (key: tool_name, value: tool)

    Returns:
        Dict containing subagent configuration with:
        - name: Unique identifier for the subagent
        - description: When the orchestrator should use this agent
        - instructions: How to use transcript search tools effectively
        - tools: List of tool names (tools themselves added to tools_dict)
    """
    # Get transcript tools from MCP server
    transcript_tools = _get_transcript_tools()

    # Add tools to the shared tools dictionary
    tool_names = []
    for tool in transcript_tools:
        tools_dict[tool.name] = tool
        tool_names.append(tool.name)

    return {
        "name": "transcript-agent",
        "description": """Searches earnings call transcripts for management commentary and analyst Q&A.

        Use this agent when you need:
        - Earnings call transcripts and commentary
        - Management discussion on specific topics
        - Analyst Q&A and company responses
        - Forward guidance and outlook statements
        - Management tone and sentiment analysis
        - Specific quotes from executives
        - Comparison of statements across quarters
        - Recurring themes in earnings discussions
        - Product/segment performance commentary
        """,
        "prompt": """You are the Earnings Transcript Search Agent with access to earnings call transcripts.

        You have tools to:
        - Search transcripts by company, date, and keywords
        - Retrieve specific sections (prepared remarks, Q&A)
        - Find management commentary on specific topics
        - Extract analyst questions and company responses
        - Compare statements across multiple quarters
        - Identify forward guidance and outlook statements

        When given a query:
        1. Identify the company and relevant time period
        2. Determine which topics or themes to search for
        3. Use your tools to search the transcript database
        4. Extract relevant quotes and commentary
        5. Provide context (who said it, when, in what section)

        Best Practices:
        - Always cite which transcript (company, quarter, date)
        - Quote verbatim when providing management commentary
        - Distinguish between prepared remarks and Q&A responses
        - Note who asked questions (analyst name and firm)
        - For comparisons, show quotes from multiple quarters side-by-side
        - Highlight changes in tone or messaging
        - Extract specific numbers, guidance ranges, and metrics mentioned
        - Identify forward-looking statements and caveats

        When analyzing transcripts:
        - Prepared remarks: Official company narrative and highlights
        - Q&A section: More candid responses, clarifications
        - Look for repeated themes across multiple calls
        - Note what topics management avoids or deflects
        """,
        "tools": tool_names
    }
