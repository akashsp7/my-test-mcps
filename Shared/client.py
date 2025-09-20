"""Minimal HTTP client for Obsidian Local REST API."""
from typing import Any, Dict
import httpx
from config import ObsidianConfig

class ObsidianAPIError(Exception):
    """Exception raised for Obsidian API errors."""
    pass

class ObsidianClient:
    """Minimal HTTP client for Obsidian Local REST API."""

    def __init__(self, config: ObsidianConfig):
        self.config = config
        self._client = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout,
            verify=config.verify_ssl,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            }
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._client.close()

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make HTTP request to Obsidian API."""
        try:
            response = self._client.request(method, endpoint, **kwargs)
            response.raise_for_status()

            # Handle different content types
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return response.json()
            else:
                return response.text

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            raise ObsidianAPIError(error_msg) from e
        except httpx.RequestError as e:
            raise ObsidianAPIError(f"Request failed: {str(e)}") from e

    def list_files_in_vault(self) -> Dict[str, Any]:
        """List all files in the vault root directory."""
        return self._make_request("GET", "/vault/")

    def get_file_contents(self, filepath: str) -> str:
        """Get the contents of a specific file."""
        return self._make_request("GET", f"/vault/{filepath}")

    def list_files_in_dir(self, dirpath: str) -> Dict[str, Any]:
        """List files in a specific directory."""
        return self._make_request("GET", f"/vault/{dirpath}/")

    def search(self, query: str, context_length: int = 100) -> Dict[str, Any]:
        """Simple text search across the vault."""
        return self._make_request("POST", "/search/simple/",
                                params={"query": query, "contextLength": context_length})

    def append_content(self, filepath: str, content: str) -> None:
        """Append content to a file (creates if doesn't exist)."""
        self._make_request("POST", f"/vault/{filepath}",
                          headers={"Content-Type": "text/markdown"},
                          data=content)

    def patch_content(self, filepath: str, operation: str, target_type: str,
                     target: str, content: str) -> None:
        """Patch content into a file at a specific target."""
        import urllib.parse
        headers = {
            "Content-Type": "text/markdown",
            "Operation": operation,
            "Target-Type": target_type,
            "Target": urllib.parse.quote(target)
        }
        self._make_request("PATCH", f"/vault/{filepath}",
                          headers=headers, data=content)

    def delete_file(self, filepath: str) -> None:
        """Delete a file or directory."""
        self._make_request("DELETE", f"/vault/{filepath}")

    def search_json(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Complex search using JsonLogic queries."""
        return self._make_request("POST", "/search/",
                                headers={"Content-Type": "application/vnd.olrapi.jsonlogic+json"},
                                json=query)

    def get_batch_file_contents(self, filepaths: list[str]) -> str:
        """Get contents of multiple files with headers."""
        result = []
        for filepath in filepaths:
            try:
                content = self.get_file_contents(filepath)
                result.append(f"# {filepath}\n\n{content}\n\n---\n\n")
            except Exception as e:
                result.append(f"# {filepath}\n\nError reading file: {str(e)}\n\n---\n\n")
        return "".join(result)

    def get_periodic_note(self, period: str) -> str:
        """Get current periodic note for the specified period."""
        return self._make_request("GET", f"/periodic/{period}/")

    def get_recent_periodic_notes(self, period: str, limit: int = 5,
                                 include_content: bool = False) -> Dict[str, Any]:
        """Get recent periodic notes."""
        params = {"limit": limit, "includeContent": include_content}
        return self._make_request("GET", f"/periodic/{period}/recent", params=params)

    def get_recent_changes(self, limit: int = 10, days: int = 90) -> Dict[str, Any]:
        """Get recently modified files using Dataview DQL."""
        dql_query = f"""TABLE file.mtime
WHERE file.mtime >= date(today) - dur({days} days)
SORT file.mtime DESC
LIMIT {limit}"""

        return self._make_request("POST", "/search/",
                                headers={"Content-Type": "application/vnd.olrapi.dataview.dql+txt"},
                                data=dql_query.encode('utf-8'))