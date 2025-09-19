"""Minimal HTTP client for Obsidian Local REST API."""
import json
from typing import Any, Dict, Optional
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