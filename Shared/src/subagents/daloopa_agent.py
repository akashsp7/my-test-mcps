"""
Daloopa Agent - Premium Financial Data Integration

Integrates with the Daloopa MCP server to fetch premium financial metrics and data.
Supports both HTTP/SSE and local stdio transports.
"""

import os
from typing import Dict, Any, List
from langchain_core.tools import StructuredTool

# Import MCP client utility
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.mcp_client import create_mcp_tools


def _get_daloopa_tools() -> List[StructuredTool]:
    """
    Connect to Daloopa MCP server and get tools.

    Supports two transport modes:
    1. HTTP/SSE (production) - Commented out by default
    2. Local stdio (development) - Active by default

    Returns:
        List of LangChain tools from Daloopa MCP server
    """
    # ===== HTTP/SSE TRANSPORT (Production) =====
    # Uncomment to use remote Daloopa MCP server via HTTP/SSE
    # try:
    #     tools = create_mcp_tools(
    #         server_name="daloopa",
    #         url="https://mcp-dev.veritionfund.cloud/daloopa/mcp",
    #         transport="sse"
    #     )
    #     return tools
    # except Exception as e:
    #     print(f"Warning: Could not connect to Daloopa HTTP MCP server: {e}")
    #     return []

    # ===== LOCAL STDIO TRANSPORT (Development) =====
    # Active by default - uses local Daloopa MCP server
    server_name = "daloopa"
    command = "/path/to/python"  # Replace with actual Python path
    args = ["/path/to/daloopa_mcp.py"]  # Replace with actual script path
    env = {
        "DALOOPA_API_KEY": os.getenv("DALOOPA_API_KEY", "")
    }

    # Validate API key is set
    if not env["DALOOPA_API_KEY"]:
        print("Warning: DALOOPA_API_KEY environment variable not set")
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
        print(f"Warning: Could not connect to Daloopa MCP server: {e}")
        return []


def create_daloopa_subagent(tools_dict: Dict[str, StructuredTool]) -> Dict[str, Any]:
    """
    Create the Daloopa subagent configuration with MCP tools.

    This agent connects to the Daloopa MCP server to access premium financial data.
    Supports both HTTP/SSE (production) and stdio (local development) transports.

    Args:
        tools_dict: Dictionary to populate with Daloopa tools (key: tool_name, value: tool)

    Returns:
        Dict containing subagent configuration with:
        - name: Unique identifier for the subagent
        - description: When the orchestrator should use this agent
        - instructions: How to use Daloopa tools effectively
        - tools: List of tool names (tools themselves added to tools_dict)
    """
    # Get Daloopa tools from MCP server
    daloopa_tools = _get_daloopa_tools()

    # Add tools to the shared tools dictionary
    tool_names = []
    for tool in daloopa_tools:
        tools_dict[tool.name] = tool
        tool_names.append(tool.name)

    return {
        "name": "daloopa-agent",
        "description": """Fetches premium financial metrics and data from Daloopa API.

        Use this agent when you need:
        - Detailed financial statements and metrics
        - Company fundamentals (revenue, EBITDA, margins, cash flow)
        - Historical financial data with high accuracy
        - Analyst estimates and consensus data
        - Industry-specific KPIs and metrics
        - Segment-level financial breakdowns
        """,
        "prompt": """You are the Daloopa Financial Data Agent with access to premium financial data.

        You have tools to:
        - Retrieve company financials (income statement, balance sheet, cash flow)
        - Access historical financial metrics and KPIs
        - Get analyst estimates and consensus data
        - Fetch segment-level financial breakdowns
        - Access industry-specific metrics

        When given a query:
        1. Identify the company (ticker or name)
        2. Determine which financial metrics are relevant
        3. Use your tools to fetch the data from Daloopa
        4. Present the data in a clear, structured format
        5. Cite data sources and time periods

        Best Practices:
        - Always specify the time period for financial data (annual/quarterly)
        - Include both absolute values and percentage changes
        - Provide context (e.g., YoY growth, vs. industry benchmarks)
        - Cite the source as "Daloopa Premium Data" with date ranges
        - For historical data, show trends over multiple periods
        """,
        "tools": tool_names
    }
