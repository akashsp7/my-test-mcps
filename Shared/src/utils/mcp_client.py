"""
MCP Client Utilities for AgentX Platform

Provides utilities to connect to local MCP servers via stdio transport
using langchain-mcp-adapters with proper session management.
"""

import asyncio
from typing import List, Dict, Optional
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools


async def _create_mcp_tools_async(
    server_name: str,
    command: Optional[str] = None,
    args: Optional[List[str]] = None,
    env: Optional[Dict[str, str]] = None,
    url: Optional[str] = None,
    transport: str = "stdio",
) -> List[StructuredTool]:
    """
    Create LangChain tools from an MCP server using proper session management.

    This function uses langchain-mcp-adapters which follows LangGraph best practices:
    - Proper session lifecycle management
    - Connection pooling ready for HTTP transport
    - Clean resource cleanup

    Args:
        server_name: Unique identifier for this MCP server
        command: Path to Python interpreter or executable (required for stdio)
        args: Command arguments to run the MCP server (required for stdio)
        env: Environment variables for the server process (stdio only)
        url: Server URL for HTTP/SSE transport (required for streamable_http/sse)
        transport: Transport type - "stdio", "streamable_http", or "sse" (default: "stdio")

    Returns:
        List of LangChain StructuredTool instances

    Example (stdio):
        >>> tools = await _create_mcp_tools_async(
        ...     server_name="sec-edgar",
        ...     command="/usr/bin/python",
        ...     args=["-m", "sec_edgar_mcp.server"],
        ...     env={"SEC_EDGAR_USER_AGENT": "..."},
        ...     transport="stdio"
        ... )

    Example (HTTP/SSE):
        >>> tools = await _create_mcp_tools_async(
        ...     server_name="daloopa",
        ...     url="https://mcp-dev.veritionfund.cloud/daloopa/mcp",
        ...     transport="sse"
        ... )
    """
    # Configure MCP client with server configuration
    # Format follows langchain-mcp-adapters MultiServerMCPClient spec
    if transport == "stdio":
        if not command or not args:
            raise ValueError("command and args are required for stdio transport")
        server_config = {
            server_name: {
                "transport": "stdio",
                "command": command,
                "args": args,
                "env": env or {}
            }
        }
    elif transport in ["streamable_http", "sse"]:
        if not url:
            raise ValueError("url is required for HTTP/SSE transport")
        server_config = {
            server_name: {
                "transport": transport,
                "url": url
            }
        }
    else:
        raise ValueError(f"Unsupported transport type: {transport}")

    # Create multi-server client (even though we have one server, this is the standard pattern)
    client = MultiServerMCPClient(server_config)

    # Use proper session management - this is the recommended pattern
    async with client.session(server_name) as session:
        # Load tools from the session
        # This properly initializes the session and discovers tools
        tools = await load_mcp_tools(session)
        return tools


def create_mcp_tools(
    server_name: str,
    command: Optional[str] = None,
    args: Optional[List[str]] = None,
    env: Optional[Dict[str, str]] = None,
    url: Optional[str] = None,
    transport: str = "stdio",
) -> List[StructuredTool]:
    """
    Create LangChain tools from an MCP server (synchronous wrapper).

    This is a convenience function that wraps the async session management
    in a synchronous interface for easier use in agent creation.

    Uses langchain-mcp-adapters for proper session lifecycle:
    - Session is created and initialized
    - Tools are discovered
    - Session is properly closed after tool loading

    Args:
        server_name: Unique identifier for this MCP server (e.g., "sec-edgar")
        command: Path to Python interpreter or executable (required for stdio)
        args: Command arguments to run the MCP server (required for stdio)
        env: Environment variables for the server process (stdio only)
        url: Server URL for HTTP/SSE transport (required for streamable_http/sse)
        transport: Transport type - "stdio", "streamable_http", or "sse" (default: "stdio")

    Returns:
        List of LangChain StructuredTool instances

    Example (stdio):
        >>> tools = create_mcp_tools(
        ...     server_name="sec-edgar",
        ...     command="/usr/bin/python",
        ...     args=["-m", "sec_edgar_mcp.server"],
        ...     env={"SEC_EDGAR_USER_AGENT": "Akash Pawar akashpawar9619@gmail.com"},
        ...     transport="stdio"
        ... )

    Example (HTTP/SSE):
        >>> tools = create_mcp_tools(
        ...     server_name="daloopa",
        ...     url="https://mcp-dev.veritionfund.cloud/daloopa/mcp",
        ...     transport="sse"
        ... )
    """
    return asyncio.run(_create_mcp_tools_async(server_name, command, args, env, url, transport))
