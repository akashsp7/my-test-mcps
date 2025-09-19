"""Configuration management for Obsidian MCP server."""
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class ObsidianConfig:
    """Configuration for Obsidian Local REST API connection."""

    api_key: str
    host: str = "127.0.0.1"
    port: int = 27124
    protocol: str = "https"
    verify_ssl: bool = False
    timeout: int = 10

    def __post_init__(self):
        if not self.api_key:
            raise ValueError("OBSIDIAN_API_KEY environment variable is required")

    @property
    def base_url(self) -> str:
        """Get the base URL for Obsidian API."""
        return f"{self.protocol}://{self.host}:{self.port}"

    @classmethod
    def from_env(cls) -> "ObsidianConfig":
        """Create configuration from environment variables."""
        return cls(
            api_key=os.getenv("OBSIDIAN_API_KEY", ""),
            host=os.getenv("OBSIDIAN_HOST", "127.0.0.1"),
            port=int(os.getenv("OBSIDIAN_PORT", "27124")),
            protocol=os.getenv("OBSIDIAN_PROTOCOL", "https"),
            verify_ssl=os.getenv("OBSIDIAN_VERIFY_SSL", "false").lower() == "true",
            timeout=int(os.getenv("OBSIDIAN_TIMEOUT", "10")),
        )