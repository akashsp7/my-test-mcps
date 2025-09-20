"""Obsidian MCP server using FastMCP."""
import os
from fastmcp import FastMCP
import tools
from config import MultiVaultConfig

# Initialize multi-vault configuration
config_path = os.getenv("OBSIDIAN_CONFIG_PATH", "obsidian_vaults.yaml")
vault_config = MultiVaultConfig(config_path)

# Create FastMCP instance
mcp = FastMCP(
    name="Obsidian Multi-Vault MCP",
    instructions="""FastMCP server for Obsidian vault integration via Local REST API.

Multi-Vault Support: Access multiple Obsidian vaults simultaneously by specifying vault parameter in tools.
File Types: .md (markdown notes), .canvas (visual mind maps as JSON), .js/.css/.png/etc (any file type supported)
Known Issues: patch_content prepend acts like append, replace only works on H1 headings, frontmatter targeting fails
Reliable Operations: append_content, get_file_contents, search, delete_file, batch operations
Target Format: heading targets use plain text (no # symbols), block targets use ID only (no ^ symbols)

Security: Local-only connections, Bearer token auth per vault, input validation, comprehensive error handling."""
)

# Make vault_config available to tools
tools.vault_config = vault_config

# Register vault management tools
mcp.tool()(tools.list_vaults)

# Register all existing tools (now with vault parameter support)
mcp.tool()(tools.list_files_in_vault)
mcp.tool()(tools.get_file_contents)
mcp.tool()(tools.search)
mcp.tool()(tools.append_content)
mcp.tool()(tools.patch_content)
mcp.tool()(tools.delete_file)
mcp.tool()(tools.batch_get_file_contents)
mcp.tool()(tools.get_periodic_note)
mcp.tool()(tools.get_recent_periodic_notes)
mcp.tool()(tools.complex_search)
mcp.tool()(tools.get_recent_changes)

if __name__ == "__main__":
    mcp.run()