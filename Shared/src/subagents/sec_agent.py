"""
SEC Agent - SEC Edgar Filing Integration

Integrates with the sec-edgar-mcp server to fetch SEC filings and regulatory data.
"""

import os
from typing import Dict, Any, List
from langchain_core.tools import StructuredTool

# Import MCP client utility
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.mcp_client import create_mcp_tools


def _get_sec_tools() -> List[StructuredTool]:
    """
    Connect to local SEC Edgar MCP server and get tools.

    Uses langchain-mcp-adapters for proper session management.

    Returns:
        List of LangChain tools from SEC Edgar MCP server
    """
    # MCP server configuration (matches your Claude Desktop config)
    server_name = "sec-edgar"
    command = "/Users/akash/miniforge3/envs/mcp/bin/python"
    args = ["-m", "sec_edgar_mcp.server"]
    env = {
        "SEC_EDGAR_USER_AGENT": "Akash Pawar akashpawar9619@gmail.com"
    }

    # Create tools from MCP server with proper session management
    try:
        tools = create_mcp_tools(
            server_name=server_name,
            command=command,
            args=args,
            env=env
        )
        return tools
    except Exception as e:
        print(f"Warning: Could not connect to SEC Edgar MCP server: {e}")
        return []


def create_sec_subagent(tools_dict: Dict[str, StructuredTool]) -> Dict[str, Any]:
    """
    Create the SEC Edgar subagent configuration with MCP tools.

    This agent connects to the local sec-edgar-mcp server via stdio transport
    and provides access to SEC filing tools.

    Args:
        tools_dict: Dictionary to populate with SEC tools (key: tool_name, value: tool)

    Returns:
        Dict containing subagent configuration with:
        - name: Unique identifier for the subagent
        - description: When the orchestrator should use this agent
        - instructions: How to use SEC Edgar tools effectively
        - tools: List of tool names (tools themselves added to tools_dict)
    """
    # Get SEC tools from MCP server
    sec_tools = _get_sec_tools()

    # Add tools to the shared tools dictionary
    tool_names = []
    for tool in sec_tools:
        tools_dict[tool.name] = tool
        tool_names.append(tool.name)

    return {
        "name": "sec-agent",
        "description": """Fetches SEC Edgar filings and regulatory data.

        Use this agent when you need:
        - SEC filings (10-K, 10-Q, 8-K, proxy statements)
        - Information from annual/quarterly reports
        - Insider transaction data (Form 4)
        - Institutional ownership data (13F filings)
        - Registration statements and prospectuses
        - Full text search across filings
        - Risk factors, MD&A, and business descriptions
        """,
        "prompt": """You are the SEC Edgar Filing Agent with access to official SEC regulatory data.

        You have tools to:
        - Search for company filings by ticker or CIK
        - Retrieve specific filings (10-K, 10-Q, 8-K, etc.)
        - Extract filing metadata and URLs
        - Access full filing text and exhibits

        When given a query:
        1. Identify the company (ticker or name)
        2. Determine which filing types are relevant
        3. Use your tools to fetch the data
        4. Extract the most relevant information
        5. Cite specific filings and sections

        Best Practices:
        - Always cite which filing you retrieved data from (e.g., "10-K filed 2024-02-15")
        - For recent data, use 10-Q (quarterly) or 8-K (current events)
        - For annual data, use 10-K (annual report)
        - Include filing dates to show how current the data is
        - Extract specific sections when asked (Risk Factors, MD&A, etc.)
        """,
        "tools": tool_names
    }
