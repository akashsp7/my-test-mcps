"""Secure Obsidian MCP server using FastMCP."""
import os
from typing import Any, Dict
from fastmcp import FastMCP
from client import ObsidianClient, ObsidianAPIError
from config import ObsidianConfig

# Create FastMCP instance
mcp = FastMCP("Obsidian MCP Secure")

@mcp.tool()
def list_files_in_vault() -> Dict[str, Any]:
    """
    List all files and directories in the root directory of your Obsidian vault.

    Returns:
        Dict containing list of files and directories
    """
    try:
        config = ObsidianConfig.from_env()

        with ObsidianClient(config) as client:
            result = client.list_files_in_vault()

        return {
            "success": True,
            "data": result,
            "message": "Successfully retrieved vault file list"
        }

    except ValueError as e:
        return {
            "success": False,
            "error": f"Configuration error: {str(e)}",
            "data": None
        }
    except ObsidianAPIError as e:
        return {
            "success": False,
            "error": f"Obsidian API error: {str(e)}",
            "data": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "data": None
        }

if __name__ == "__main__":
    mcp.run()