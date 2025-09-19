"""Obsidian MCP Tools - All tool implementations."""
from typing import Any, Dict, List
from client import ObsidianClient, ObsidianAPIError
from config import ObsidianConfig

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

def get_file_contents(filepath: str) -> Dict[str, Any]:
    """
    Return the content of a single file in your vault.

    Args:
        filepath: Path to the relevant file (relative to your vault root)

    Returns:
        Dict containing file content or error information
    """
    try:
        config = ObsidianConfig.from_env()

        with ObsidianClient(config) as client:
            result = client.get_file_contents(filepath)

        return {
            "success": True,
            "data": result,
            "message": f"Successfully retrieved content from {filepath}"
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

def search(query: str, context_length: int = 100) -> Dict[str, Any]:
    """
    Simple search for documents matching a specified text query across all files in the vault.

    Args:
        query: Text to search for in the vault
        context_length: How much context to return around the matching string (default: 100)

    Returns:
        Dict containing search results or error information
    """
    try:
        config = ObsidianConfig.from_env()

        with ObsidianClient(config) as client:
            raw_results = client.search(query, context_length)

        # Format results similar to original implementation
        formatted_results = []
        for result in raw_results:
            formatted_matches = []
            for match in result.get('matches', []):
                context = match.get('context', '')
                match_pos = match.get('match', {})
                start = match_pos.get('start', 0)
                end = match_pos.get('end', 0)

                formatted_matches.append({
                    'context': context,
                    'match_position': {'start': start, 'end': end}
                })

            formatted_results.append({
                'filename': result.get('filename', ''),
                'score': result.get('score', 0),
                'matches': formatted_matches
            })

        return {
            "success": True,
            "data": formatted_results,
            "message": f"Search completed for query: {query}"
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

def append_content(filepath: str, content: str) -> Dict[str, Any]:
    """
    Append content to a new or existing file in the vault.

    Args:
        filepath: Path to the file (relative to vault root)
        content: Content to append to the file

    Returns:
        Dict containing success status or error information
    """
    try:
        config = ObsidianConfig.from_env()

        with ObsidianClient(config) as client:
            client.append_content(filepath, content)

        return {
            "success": True,
            "data": None,
            "message": f"Successfully appended content to {filepath}"
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

def patch_content(filepath: str, operation: str, target_type: str, target: str, content: str) -> Dict[str, Any]:
    """
    Insert content into an existing note relative to a heading, block reference, or frontmatter field.

    KNOWN ISSUES: prepend acts like append, replace only works on H1 headings, frontmatter targeting fails.
    RELIABLE: append+heading, append+block, replace+H1 only. Target format: plain text, no # or ^ symbols.

    Args:
        filepath: Path to the file (relative to vault root)
        operation: Operation to perform (append, prepend, or replace)
        target_type: Type of target to patch (heading, block, frontmatter)
        target: Target identifier (heading path, block reference, or frontmatter field)
        content: Content to insert

    Returns:
        Dict containing success status or error information
    """
    try:
        # Validate operation
        if operation not in ["append", "prepend", "replace"]:
            raise ValueError(f"Invalid operation: {operation}. Must be one of: append, prepend, replace")

        # Validate target_type
        if target_type not in ["heading", "block", "frontmatter"]:
            raise ValueError(f"Invalid target_type: {target_type}. Must be one of: heading, block, frontmatter")

        config = ObsidianConfig.from_env()

        with ObsidianClient(config) as client:
            client.patch_content(filepath, operation, target_type, target, content)

        return {
            "success": True,
            "data": None,
            "message": f"Successfully patched content in {filepath}"
        }

    except ValueError as e:
        return {
            "success": False,
            "error": f"Validation error: {str(e)}",
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

def delete_file(filepath: str, confirm: bool = False) -> Dict[str, Any]:
    """
    Delete a file or directory from the vault.

    Args:
        filepath: Path to the file or directory to delete (relative to vault root)
        confirm: Confirmation to delete the file (must be True)

    Returns:
        Dict containing success status or error information
    """
    try:
        if not confirm:
            raise ValueError("confirm must be set to True to delete a file")

        config = ObsidianConfig.from_env()

        with ObsidianClient(config) as client:
            client.delete_file(filepath)

        return {
            "success": True,
            "data": None,
            "message": f"Successfully deleted {filepath}"
        }

    except ValueError as e:
        return {
            "success": False,
            "error": f"Validation error: {str(e)}",
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

def batch_get_file_contents(filepaths: List[str]) -> Dict[str, Any]:
    """
    Return the contents of multiple files in your vault, concatenated with headers.

    Args:
        filepaths: List of file paths to read

    Returns:
        Dict containing concatenated file contents or error information
    """
    try:
        config = ObsidianConfig.from_env()

        with ObsidianClient(config) as client:
            result = client.get_batch_file_contents(filepaths)

        return {
            "success": True,
            "data": result,
            "message": f"Successfully retrieved {len(filepaths)} files"
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

def get_periodic_note(period: str) -> Dict[str, Any]:
    """
    Get current periodic note for the specified period.

    Args:
        period: The period type (daily, weekly, monthly, quarterly, yearly)

    Returns:
        Dict containing periodic note content or error information
    """
    try:
        valid_periods = ["daily", "weekly", "monthly", "quarterly", "yearly"]
        if period not in valid_periods:
            raise ValueError(f"Invalid period: {period}. Must be one of: {', '.join(valid_periods)}")

        config = ObsidianConfig.from_env()

        with ObsidianClient(config) as client:
            result = client.get_periodic_note(period)

        return {
            "success": True,
            "data": result,
            "message": f"Successfully retrieved {period} periodic note"
        }

    except ValueError as e:
        return {
            "success": False,
            "error": f"Validation error: {str(e)}",
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

def get_recent_periodic_notes(period: str, limit: int = 5, include_content: bool = False) -> Dict[str, Any]:
    """
    Get most recent periodic notes for the specified period type.

    Args:
        period: The period type (daily, weekly, monthly, quarterly, yearly)
        limit: Maximum number of notes to return (default: 5)
        include_content: Whether to include note content (default: False)

    Returns:
        Dict containing recent periodic notes or error information
    """
    try:
        valid_periods = ["daily", "weekly", "monthly", "quarterly", "yearly"]
        if period not in valid_periods:
            raise ValueError(f"Invalid period: {period}. Must be one of: {', '.join(valid_periods)}")

        if not isinstance(limit, int) or limit < 1 or limit > 50:
            raise ValueError(f"Invalid limit: {limit}. Must be an integer between 1 and 50")

        if not isinstance(include_content, bool):
            raise ValueError(f"Invalid include_content: {include_content}. Must be a boolean")

        config = ObsidianConfig.from_env()

        with ObsidianClient(config) as client:
            result = client.get_recent_periodic_notes(period, limit, include_content)

        return {
            "success": True,
            "data": result,
            "message": f"Successfully retrieved {limit} recent {period} notes"
        }

    except ValueError as e:
        return {
            "success": False,
            "error": f"Validation error: {str(e)}",
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

def complex_search(query: Dict[str, Any]) -> Dict[str, Any]:
    """
    Complex search for documents using a JsonLogic query.
    Supports standard JsonLogic operators plus 'glob' and 'regexp' for pattern matching.

    Args:
        query: JsonLogic query object

    Returns:
        Dict containing search results or error information
    """
    try:
        config = ObsidianConfig.from_env()

        with ObsidianClient(config) as client:
            result = client.search_json(query)

        return {
            "success": True,
            "data": result,
            "message": "Complex search completed successfully"
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

def get_recent_changes(limit: int = 10, days: int = 90) -> Dict[str, Any]:
    """
    Get recently modified files in the vault.

    Args:
        limit: Maximum number of files to return (default: 10)
        days: Only include files modified within this many days (default: 90)

    Returns:
        Dict containing recent changes or error information
    """
    try:
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            raise ValueError(f"Invalid limit: {limit}. Must be an integer between 1 and 100")

        if not isinstance(days, int) or days < 1:
            raise ValueError(f"Invalid days: {days}. Must be a positive integer")

        config = ObsidianConfig.from_env()

        with ObsidianClient(config) as client:
            result = client.get_recent_changes(limit, days)

        return {
            "success": True,
            "data": result,
            "message": f"Successfully retrieved {limit} recent changes from last {days} days"
        }

    except ValueError as e:
        return {
            "success": False,
            "error": f"Validation error: {str(e)}",
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