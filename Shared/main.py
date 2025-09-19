"""Obsidian MCP server using FastMCP."""
from fastmcp import FastMCP
import tools

# Create FastMCP instance
mcp = FastMCP(
    name="Obsidian MCP",
    instructions="""FastMCP server for Obsidian vault integration via Local REST API.

File Types: .md (markdown notes), .canvas (visual mind maps as JSON), .js/.css/.png/etc (any file type supported)
Known Issues: patch_content prepend acts like append, replace only works on H1 headings, frontmatter targeting fails
Reliable Operations: append_content, get_file_contents, search, delete_file, batch operations
Target Format: heading targets use plain text (no # symbols), block targets use ID only (no ^ symbols)

Security: Local-only (127.0.0.1:27124), Bearer token auth, input validation, comprehensive error handling."""
)

# Register all tools
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