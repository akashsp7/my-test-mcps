"""Configuration management for Obsidian MCP server."""
import os
import yaml
from dataclasses import dataclass
from typing import Optional, Dict

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


@dataclass
class VaultConfig:
    """Configuration for a single vault."""
    name: str
    api_key: str
    host: str = "127.0.0.1"
    port: int = 27124
    protocol: str = "https"
    verify_ssl: bool = False
    timeout: int = 10

    def to_obsidian_config(self) -> ObsidianConfig:
        """Convert to ObsidianConfig for client usage."""
        return ObsidianConfig(
            api_key=self.api_key,
            host=self.host,
            port=self.port,
            protocol=self.protocol,
            verify_ssl=self.verify_ssl,
            timeout=self.timeout
        )


class MultiVaultConfig:
    """Configuration manager for multiple Obsidian vaults."""

    def __init__(self, config_path: str = None):
        self.vaults: Dict[str, VaultConfig] = {}
        self.default_vault: Optional[str] = None

        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
        else:
            # Fallback to single vault from environment
            self._load_from_env()

    def load_config(self, config_path: str):
        """Load vault configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)

            self.vaults.clear()
            for vault_id, vault_data in data.get('vaults', {}).items():
                self.vaults[vault_id] = VaultConfig(
                    name=vault_data.get('name', vault_id),
                    api_key=vault_data['api_key'],
                    host=vault_data.get('host', '127.0.0.1'),
                    port=vault_data.get('port', 27124),
                    protocol=vault_data.get('protocol', 'https'),
                    verify_ssl=vault_data.get('verify_ssl', False),
                    timeout=vault_data.get('timeout', 10)
                )

            self.default_vault = data.get('default_vault')
            if self.default_vault and self.default_vault not in self.vaults:
                raise ValueError(f"Default vault '{self.default_vault}' not found in vaults")

        except Exception as e:
            raise ValueError(f"Failed to load config from {config_path}: {str(e)}")

    def _load_from_env(self):
        """Fallback: load single vault from environment variables."""
        try:
            env_config = ObsidianConfig.from_env()
            vault_config = VaultConfig(
                name="default",
                api_key=env_config.api_key,
                host=env_config.host,
                port=env_config.port,
                protocol=env_config.protocol,
                verify_ssl=env_config.verify_ssl,
                timeout=env_config.timeout
            )
            self.vaults["default"] = vault_config
            self.default_vault = "default"
        except Exception as e:
            # No environment config available
            pass

    def get_vault_config(self, vault_name: str = None) -> VaultConfig:
        """Get configuration for specified vault or default vault."""
        if not self.vaults:
            raise ValueError("No vaults configured")

        target = vault_name or self.default_vault
        if not target:
            # No default set, use first available
            target = next(iter(self.vaults.keys()))

        if target not in self.vaults:
            available = list(self.vaults.keys())
            raise ValueError(f"Vault '{target}' not found. Available vaults: {available}")

        return self.vaults[target]

    def list_vaults(self) -> Dict[str, Dict]:
        """List all configured vaults with their details."""
        return {
            vault_id: {
                "name": config.name,
                "host": config.host,
                "port": config.port,
                "is_default": vault_id == self.default_vault
            }
            for vault_id, config in self.vaults.items()
        }