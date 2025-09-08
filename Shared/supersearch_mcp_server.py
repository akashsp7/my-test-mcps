"""
Supersearch MCP Server - Intelligent Transcript Search
Enables smart exploration of transcript folders without loading entire files into context
"""

import os
import json
import glob
from datetime import datetime
from typing import Dict, Any, List, Union, Optional
from pathlib import Path
from fastmcp import FastMCP

# Configuration - all configurable via environment variables
TRANSCRIPTS_PATH = os.getenv("TRANSCRIPTS_PATH", "/Users/akash/Documents/transcripts")
CACHE_PATH = os.getenv("SUPERSEARCH_CACHE_PATH", ".supersearch_cache.json")
MAX_SEARCH_RESULTS = int(os.getenv("SUPERSEARCH_MAX_RESULTS", "50"))
MAX_MATCHES_PER_FILE = int(os.getenv("SUPERSEARCH_MAX_MATCHES_PER_FILE", "10"))
PREVIEW_CONTEXT_LINES = int(os.getenv("SUPERSEARCH_PREVIEW_CONTEXT", "20"))

# Initialize FastMCP server
mcp = FastMCP(
    name="Supersearch Transcript MCP",
    instructions="""
        Model Context Protocol (MCP) for intelligent transcript search and exploration.
        Designed for progressive discovery through targeted searches without loading entire files.

        CAPABILITIES:
        1. Auto-index transcript folders with smart caching
        2. Search filenames by keywords with partial matching
        3. Search content within files with precise line number locations
        4. Preview specific file sections with context

        WORKFLOW:
        1. System auto-indexes transcripts on startup
        2. Use filename search to identify relevant files
        3. Use content search to find specific topics/phrases
        4. Use preview tool to examine specific sections

        FEATURES:
        - Context-efficient: Only loads relevant content
        - Language/structure agnostic: Works with any MD transcript format
        - Scalable: Handles hundreds of files efficiently
        - Progressive discovery: Find → Explore → Focus workflow
    """
)

def get_cache_path() -> str:
    """Get the full path to the cache file"""
    if os.path.isabs(CACHE_PATH):
        return CACHE_PATH
    return os.path.join(TRANSCRIPTS_PATH, CACHE_PATH)

def load_cache() -> Dict[str, Any]:
    """Load the transcript cache from disk"""
    cache_file = get_cache_path()
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache_data: Dict[str, Any]) -> None:
    """Save the transcript cache to disk"""
    cache_file = get_cache_path()
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
    except Exception:
        pass

def get_file_metadata(filepath: str) -> Dict[str, Any]:
    """Extract metadata from a transcript file"""
    try:
        stat = os.stat(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        return {
            'filepath': filepath,
            'filename': os.path.basename(filepath),
            'size_bytes': stat.st_size,
            'line_count': len(lines),
            'last_modified': stat.st_mtime,
            'last_modified_readable': datetime.fromtimestamp(stat.st_mtime).isoformat()
        }
    except Exception as e:
        return {
            'filepath': filepath,
            'filename': os.path.basename(filepath),
            'error': str(e)
        }

@mcp.tool
def index_transcripts() -> Dict[str, Any]:
    """
    Auto-index all transcript files in the configured directory.
    
    This tool automatically scans the transcript folder and extracts metadata for all .md files.
    It caches results locally and only re-indexes files that have been modified since the last scan.
    This tool runs automatically when the MCP server starts.
    
    Returns:
        Dict[str, Any]: Indexing results containing:
            - indexed_count (int): Number of files processed
            - cached_count (int): Number of files loaded from cache
            - total_files (int): Total transcript files found
            - transcripts_path (str): Path being monitored
            - cache_path (str): Location of cache file
            - files (List[Dict]): Metadata for all files
    """
    try:
        # Ensure transcripts directory exists
        if not os.path.exists(TRANSCRIPTS_PATH):
            return {
                "error": f"Transcripts directory not found: {TRANSCRIPTS_PATH}",
                "transcripts_path": TRANSCRIPTS_PATH
            }
        
        # Find all .md files
        md_pattern = os.path.join(TRANSCRIPTS_PATH, "**", "*.md")
        transcript_files = glob.glob(md_pattern, recursive=True)
        
        # Load existing cache
        cache = load_cache()
        
        indexed_count = 0
        cached_count = 0
        files_metadata = []
        
        for filepath in transcript_files:
            # Check if file needs re-indexing
            current_mtime = os.path.getmtime(filepath)
            cached_data = cache.get(filepath, {})
            
            if cached_data.get('last_modified') == current_mtime:
                # Use cached data
                files_metadata.append(cached_data)
                cached_count += 1
            else:
                # Re-index file
                metadata = get_file_metadata(filepath)
                files_metadata.append(metadata)
                cache[filepath] = metadata
                indexed_count += 1
        
        # Save updated cache
        save_cache(cache)
        
        return {
            "indexed_count": indexed_count,
            "cached_count": cached_count,
            "total_files": len(transcript_files),
            "transcripts_path": TRANSCRIPTS_PATH,
            "cache_path": get_cache_path(),
            "files": files_metadata[:MAX_SEARCH_RESULTS]  # Limit results
        }
        
    except Exception as e:
        return {"error": f"Error indexing transcripts: {str(e)}"}

@mcp.tool
def search_transcript_filenames(keywords: List[str]) -> Dict[str, Any]:
    """
    Search for transcript files by filename keywords.
    
    This tool searches through indexed transcript filenames using case-insensitive partial matching.
    It returns files whose names contain any of the specified keywords.
    
    Args:
        keywords (List[str]): List of keywords to search for in filenames
        
    Returns:
        Dict[str, Any]: Search results containing:
            - matched_files (List[Dict]): Files matching the keywords
            - keywords_used (List[str]): Keywords that were searched
            - total_matches (int): Number of matching files
            - search_path (str): Directory that was searched
    """
    try:
        if not keywords:
            return {"error": "Keywords list cannot be empty"}
        
        # Load cache to search through
        cache = load_cache()
        if not cache:
            # Try to index first
            index_result = index_transcripts()
            if "error" in index_result:
                return index_result
            cache = load_cache()
        
        matched_files = []
        keywords_lower = [k.lower() for k in keywords]
        
        for filepath, metadata in cache.items():
            if "error" in metadata:
                continue
                
            filename_lower = metadata['filename'].lower()
            
            # Check if any keyword matches
            if any(keyword in filename_lower for keyword in keywords_lower):
                matched_files.append(metadata)
        
        # Limit results
        matched_files = matched_files[:MAX_SEARCH_RESULTS]
        
        return {
            "matched_files": matched_files,
            "keywords_used": keywords,
            "total_matches": len(matched_files),
            "search_path": TRANSCRIPTS_PATH
        }
        
    except Exception as e:
        return {"error": f"Error searching filenames: {str(e)}"}

@mcp.tool
def search_transcript_content(search_term: str, max_results: Optional[int] = None, 
                            max_matches_per_file: Optional[int] = None,
                            preview_mode: bool = False) -> Dict[str, Any]:
    """
    Search for content within transcript files and return precise locations.
    
    This tool searches through the content of all indexed transcript files and returns
    the exact line numbers where the search term appears, without loading entire files.
    
    Args:
        search_term (str): The term or phrase to search for
        max_results (Optional[int]): Maximum number of files to return (default: configured limit)
        max_matches_per_file (Optional[int]): Maximum matches per file (default: configured limit)
        preview_mode (bool): If True, include line snippets around matches
        
    Returns:
        Dict[str, Any]: Search results containing:
            - search_term (str): The term that was searched
            - total_files_searched (int): Number of files searched
            - files_with_matches (int): Number of files containing the term
            - matches (List[Dict]): Files and their matching line numbers
            - search_summary (str): Human-readable summary of results
    """
    try:
        if not search_term.strip():
            return {"error": "Search term cannot be empty"}
        
        # Use provided limits or defaults
        max_results = max_results or MAX_SEARCH_RESULTS
        max_matches_per_file = max_matches_per_file or MAX_MATCHES_PER_FILE
        
        # Load cache to get file list
        cache = load_cache()
        if not cache:
            index_result = index_transcripts()
            if "error" in index_result:
                return index_result
            cache = load_cache()
        
        matches = []
        files_searched = 0
        search_term_lower = search_term.lower()
        
        for filepath, metadata in cache.items():
            if "error" in metadata:
                continue
                
            files_searched += 1
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                line_matches = []
                for line_num, line in enumerate(lines, 1):
                    if search_term_lower in line.lower():
                        match_info = {"line_number": line_num}
                        
                        if preview_mode:
                            # Add line preview
                            match_info["line_content"] = line.strip()
                        
                        line_matches.append(match_info)
                        
                        if len(line_matches) >= max_matches_per_file:
                            break
                
                if line_matches:
                    file_match = {
                        "filename": metadata['filename'],
                        "filepath": filepath,
                        "match_count": len(line_matches),
                        "line_matches": line_matches
                    }
                    matches.append(file_match)
                    
                    if len(matches) >= max_results:
                        break
                        
            except Exception:
                continue
        
        # Create human-readable summary
        if matches:
            line_numbers_summary = []
            for match in matches:
                lines = [str(m["line_number"]) for m in match["line_matches"]]
                line_numbers_summary.append(f"{match['filename']}: Line {', Line '.join(lines)}")
            search_summary = " | ".join(line_numbers_summary)
        else:
            search_summary = f"No matches found for '{search_term}'"
        
        return {
            "search_term": search_term,
            "total_files_searched": files_searched,
            "files_with_matches": len(matches),
            "matches": matches,
            "search_summary": search_summary
        }
        
    except Exception as e:
        return {"error": f"Error searching content: {str(e)}"}

@mcp.tool
def preview_transcript_section(filepath: str, line_number: int, 
                             context_lines: Optional[int] = None) -> Dict[str, Any]:
    """
    Preview a specific section of a transcript file around a given line number.
    
    This tool reads and returns a specific section of a transcript file with surrounding
    context lines, allowing focused examination of search results without loading entire files.
    
    Args:
        filepath (str): Path to the transcript file to preview
        line_number (int): The target line number to preview around
        context_lines (Optional[int]): Number of context lines before/after (default: configured)
        
    Returns:
        Dict[str, Any]: Preview results containing:
            - filename (str): Name of the file being previewed
            - filepath (str): Full path to the file
            - target_line_number (int): The requested line number
            - start_line (int): First line number in the preview
            - end_line (int): Last line number in the preview
            - total_lines (int): Total lines in the file
            - preview_lines (List[Dict]): Lines with numbers and content
    """
    try:
        context_lines = context_lines or PREVIEW_CONTEXT_LINES
        
        if not os.path.exists(filepath):
            return {"error": f"File not found: {filepath}"}
        
        with open(filepath, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        total_lines = len(all_lines)
        
        if line_number < 1 or line_number > total_lines:
            return {
                "error": f"Line number {line_number} is out of range (file has {total_lines} lines)",
                "filepath": filepath
            }
        
        # Calculate preview range
        start_line = max(1, line_number - context_lines)
        end_line = min(total_lines, line_number + context_lines)
        
        preview_lines = []
        for i in range(start_line - 1, end_line):
            preview_lines.append({
                "line_number": i + 1,
                "content": all_lines[i].rstrip('\n'),
                "is_target": (i + 1) == line_number
            })
        
        return {
            "filename": os.path.basename(filepath),
            "filepath": filepath,
            "target_line_number": line_number,
            "start_line": start_line,
            "end_line": end_line,
            "total_lines": total_lines,
            "preview_lines": preview_lines
        }
        
    except Exception as e:
        return {"error": f"Error previewing file: {str(e)}", "filepath": filepath}

# Auto-index on server startup
if __name__ == "__main__":
    # Auto-index transcripts when server starts
    try:
        index_result = index_transcripts()
        if "error" not in index_result:
            print(f"✓ Indexed {index_result['total_files']} transcript files")
    except Exception as e:
        print(f"Warning: Could not auto-index transcripts: {e}")
    
    # Run the MCP server
    mcp.run()
    
    
# "supersearch": {
#         "command": "/Users/akash/miniforge3/envs/mcp/bin/python",
#         "args": ["/Users/akash/Documents/WORK/MCProject/scripts/supersearch_mcp_server.py"],
#         "env": {
#           "TRANSCRIPTS_PATH": "/Users/akash/Documents/transcripts",
#           "SUPERSEARCH_CACHE_PATH": ".supersearch_cache.json",
#           "SUPERSEARCH_MAX_RESULTS": "50",
#           "SUPERSEARCH_MAX_MATCHES_PER_FILE": "10",
#           "SUPERSEARCH_PREVIEW_CONTEXT": "20"
#         }
#     }