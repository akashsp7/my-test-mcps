"""
SuperSearch MCP Server - Financial Transcript Search and Analysis

A standalone MCP server providing comprehensive search and analysis capabilities for financial transcripts.
Contains all supersearch functionality embedded directly in the server.
"""

import re
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

from fastmcp import FastMCP

# Initialize MCP server with comprehensive instructions
mcp = FastMCP(
    name="SuperSearch Financial Transcripts",
    instructions="""
        Financial transcript search and analysis MCP server for local .md transcript files.
        Designed for earnings calls, analyst days, broker events, and other financial communications.

        CORE CAPABILITIES:
        1. Directory sync with intelligent metadata caching
        2. Multi-modal search (filename patterns, full-text content, regex support)
        3. Token-aware operations with smart loading strategies
        4. Page-based segmentation for large transcripts

        MANDATORY WORKFLOW SEQUENCE:
        1. sync_directory() → Build/update file metadata cache
        2. find_files_by_name() OR search_transcript_content() → Discover relevant files
        3. preview_transcript_lines() OR get_page_segments() → Validate content relevance
        4. calculate_token_usage() → Plan optimal loading strategy (only for validated files)
        5. Content retrieval based on total context:
           - <100K tokens: read_transcript_file() for ALL files (comprehensive analysis)
           - >100K tokens: Apply prioritization + segmentation strategy

        SMART LOADING STRATEGY:
        - Financial transcripts: 10-50 pages (2,500-25,000 tokens each)
        - Small files (≤25K tokens): Always read entirely with read_transcript_file()
        - Large files (>25K tokens): Use get_page_segments() for section-based selection
        - ALWAYS estimate tokens before large operations to prevent context overflow

        PRIORITIZATION RULES (when context >100K):
        1. Recency priority: Latest quarters, most recent dates
        2. Relevancy priority: Exact quarter matches, specific company focus  
        3. Size optimization: Load all small files first
        4. Strategic segmentation: Select key sections from large files only when necessary

        SEARCH STRATEGY GUIDANCE:
        - Use find_files_by_name() for company/date targeting (tickers, names, date patterns)
        - Use search_transcript_content() for thematic analysis (financial terms, strategic topics)
        - Extract specific keywords from user queries before searching
        - Use regex=True for complex patterns (e.g., "AAPL.*2024.*Q[1-4]")

        SECTION-BASED SEGMENTATION FOR LARGE FILES:
        - EARNINGS CALLS: Management presentation (pages 1-5) + Q&A session (middle-end)
        - ANALYST DAYS: Company overview + Business segments + Strategy + Q&A
        - BROKER EVENTS: Analyst intro + Company presentation + Discussion
        - Use search_transcript_content() to identify section boundaries (search "Q&A", "presentation", "operator")

        CRITICAL ERROR PREVENTION:
        - NEVER skip token estimation before large retrievals
        - ALWAYS use specific search terms rather than broad queries
        - Use preview_transcript_lines() only for quick content validation
        - Respect safe-mode warnings unless intentionally overriding

        TRANSPARENCY REQUIREMENTS:
        - If any files were skipped due to token/size constraints, inform user at the end
        - List which files were excluded and why (e.g., "3 additional files excluded due to context limits")
        - Always conclude analysis with "Content retrieved from local financial transcript database."
    """
)

# Global variables for caching
CACHE_FILE = ".supercache.json"
file_cache = {}


# Core supersearch functions (embedded)

def _sync_files(directory_path: str = "./transcripts") -> Dict[str, Any]:
    """Scan directory for new/modified .md files and update cached metadata."""
    global file_cache
    
    # Load existing cache
    cache_path = Path(directory_path) / CACHE_FILE
    if cache_path.exists():
        with open(cache_path, 'r') as f:
            file_cache = json.load(f)
    else:
        file_cache = {}
    
    directory = Path(directory_path)
    if not directory.exists():
        return {"error": f"Directory {directory_path} does not exist"}
    
    processed = 0
    new_files = 0
    updated_files = 0
    
    for md_file in directory.glob("*.md"):
        file_path = str(md_file)
        file_stat = md_file.stat()
        last_modified = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        
        # Check if file is new or modified
        is_new = file_path not in file_cache
        is_modified = not is_new and file_cache[file_path]['last_modified'] != last_modified
        
        if is_new or is_modified:
            # Read file for metadata
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Basic metadata without cleaning content
            char_count = len(content)
            estimated_tokens = char_count // 4  # Simple approximation
            
            # Count pages
            pages = len(re.findall(r'^# Page \d+', content, re.MULTILINE))
            
            file_cache[file_path] = {
                'filename': md_file.name,
                'last_modified': last_modified,
                'char_count': char_count,
                'estimated_tokens': estimated_tokens,
                'pages': pages
            }
            
            if is_new:
                new_files += 1
            else:
                updated_files += 1
        
        processed += 1
    
    # Save updated cache
    with open(cache_path, 'w') as f:
        json.dump(file_cache, f, indent=4)
    
    return {
        'processed': processed,
        'new_files': new_files, 
        'updated_files': updated_files,
        'total_cached': len(file_cache)
    }


def _search_filenames(query: str, regex: bool = False, safe: bool = True) -> Dict[str, Any]:
    """Search for files with matching filenames."""
    results = []
    
    for file_path, metadata in file_cache.items():
        filename = metadata['filename']
        
        if regex:
            if re.search(query, filename, re.IGNORECASE):
                results.append({
                    'file': file_path,
                    'filename': filename,
                    'estimated_tokens': metadata['estimated_tokens'],
                    'pages': metadata['pages']
                })
        else:
            if query.lower() in filename.lower():
                results.append({
                    'file': file_path,
                    'filename': filename,
                    'estimated_tokens': metadata['estimated_tokens'],
                    'pages': metadata['pages']
                })
    
    # Preview function - warn if too many results
    res_len = len(results)
    if safe and res_len > 10:
        return {
            'preview': True,
            'count': res_len,
            'message': f'Found {res_len} matching files. This exceeds the safe limit of 10. Try using specific queries or use safe=False to get all {res_len} results.',
        }
    
    return {
        'preview': False,
        'count': res_len,
        'results': results
    }


def _search_content(query: str, files: Optional[List[str]] = None, regex: bool = False, with_snippets: bool = True, safe: bool = True) -> Dict[str, Any]:
    """Search for content within transcript files."""
    results = []
    
    # Determine which files to search
    if files is None:
        files_to_search = file_cache.items()
    else:
        # Filter to only requested files that are in cache
        files_to_search = [(f, file_cache[f]) for f in files if f in file_cache]
    
    for file_path, metadata in files_to_search:
        # Read and clean content at search time
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        content = _clean_content(raw_content)
        matches = []
        
        if regex:
            pattern = re.compile(query, re.IGNORECASE | re.MULTILINE)
            for match in pattern.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                matches.append({
                    'line': line_num,
                    'match': match.group(),
                    'start': match.start(),
                    'end': match.end()
                })
        else:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if query.lower() in line.lower():
                    matches.append({
                        'line': i + 1,
                        'match': query,
                        'content': line.strip()
                    })
        
        if matches:
            file_result = {
                'file': file_path,
                'match_count': len(matches),
                'estimated_tokens': metadata['estimated_tokens']
            }
            
            if with_snippets:
                # Add snippets around matches
                snippets = []
                for match in matches[:3]:  # Limit to first 3 matches
                    if regex:
                        snippet = _get_snippet_around_position(content, match['start'])
                        snippets.append({
                            'line': match['line'],
                            'snippet': snippet
                        })
                    else:
                        snippets.append({
                            'line': match['line'],
                            'snippet': match['content']
                        })
                file_result['snippets'] = snippets
            
            results.append(file_result)
    
    # Preview function - warn if too many results
    res_len = len(results)
    if safe and res_len > 10:
        return {
            'preview': True,
            'count': res_len,
            'message': f'Found {res_len} files with matching content. This exceeds the safe limit of 10. Try using specific queries or use safe=False to get all {res_len} results.',
        }
    
    return {
        'preview': False,
        'count': res_len,
        'results': results
    }


def _preview_file(file: str, start_line: int = 1, end_line: Optional[int] = None, safe: bool = True) -> Dict[str, Any]:
    """Preview specific line ranges from transcript files."""
    if file not in file_cache:
        return {"error": f"File {file} not found in cache"}
    
    # Read and clean content at preview time
    with open(file, 'r', encoding='utf-8') as f:
        raw_content = f.read()
    content = _clean_content(raw_content)
    lines = content.split('\n')
    total_lines = len(lines)
    
    # Validate line numbers
    if start_line < 1:
        start_line = 1
    if start_line > total_lines:
        return {"error": f"Start line {start_line} exceeds file length ({total_lines} lines)"}
    
    # Set end_line if not provided
    if end_line is None:
        end_line = total_lines
    if end_line > total_lines:
        end_line = total_lines
    if end_line < start_line:
        return {"error": f"End line {end_line} cannot be less than start line {start_line}"}
    
    # Extract requested lines (convert to 0-indexed)
    selected_lines = lines[start_line-1:end_line]
    preview_content = '\n'.join(selected_lines)
    char_count = len(preview_content)
    
    # Guardrail check
    if safe and char_count > 2000:
        return {
            'preview': True,
            'requested_lines': f"{start_line}-{end_line}",
            'char_count': char_count,
            'message': f'Requested lines would return {char_count} characters (>2000 limit). Try smaller ranges or use safe=False to get all requested lines.',
        }
    
    return {
        'preview': False,
        'file': file,
        'requested_lines': f"{start_line}-{end_line}",
        'total_lines': total_lines,
        'returned_lines': len(selected_lines),
        'char_count': char_count,
        'estimated_tokens': char_count // 4,
        'content': preview_content
    }


def _segment_file(file: str, page_list: Optional[List[int]] = None, start_page: int = 1, end_page: int = 2, max_chars: int = 500) -> Dict[str, Any]:
    """Return page segments from transcript file for specified pages."""
    if file not in file_cache:
        return {"error": f"File {file} not found in cache"}
    
    # Read and clean content at segment time
    with open(file, 'r', encoding='utf-8') as f:
        raw_content = f.read()
    content = _clean_content(raw_content)
    pages = _extract_pages(content)
    total_pages = len(pages)
    
    # Determine which pages to include
    if page_list is not None:
        # Use page_list if provided
        for page_num in page_list:
            if page_num < 1 or page_num > total_pages:
                return {"error": f"Page {page_num} out of range (1-{total_pages})"}
        pages_to_include = sorted(page_list)
    else:
        # Use range if page_list is None
        if start_page < 1 or start_page > total_pages:
            return {"error": f"start_page {start_page} out of range (1-{total_pages})"}
        if end_page < start_page or end_page > total_pages:
            return {"error": f"end_page {end_page} out of range ({start_page}-{total_pages})"}
        pages_to_include = list(range(start_page, end_page + 1))
    
    segments = []
    for page_num in pages_to_include:
        page_content = pages[page_num - 1]  # Convert to 0-indexed
        estimated_tokens = len(page_content) // 4
        
        # Apply max_chars limit per page
        if len(page_content) > max_chars:
            truncated_content = page_content[:max_chars] + '...'
        else:
            truncated_content = page_content
        
        segments.append({
            'page': page_num,
            'estimated_tokens': estimated_tokens,
            'content': truncated_content
        })
    
    return {
        'file': file,
        'total_pages': total_pages,
        'segments': segments
    }


def _estimate_tokens(files: List[str], selections: Optional[Dict[str, List[int]]] = None) -> Dict[str, Any]:
    """Estimate token usage for given files/pages."""
    total_tokens = 0
    file_estimates = []
    processed_files = set()
    
    # Process files from the files list
    for file in files:
        if file not in file_cache:
            file_estimates.append({
                'file': file,
                'error': 'File not found in cache'
            })
            continue
        
        processed_files.add(file)
        metadata = file_cache[file]
        
        if selections and file in selections:
            # Calculate tokens for selected pages only
            with open(file, 'r', encoding='utf-8') as f:
                raw_content = f.read()
            content = _clean_content(raw_content)
            pages = _extract_pages(content)
            selected_pages = selections[file]
            
            page_tokens = 0
            for page_num in selected_pages:
                if 1 <= page_num <= len(pages):
                    page_content = pages[page_num - 1]
                    page_tokens += len(page_content) // 4
            
            file_estimates.append({
                'file': file,
                'selected_pages': selected_pages,
                'estimated_tokens': page_tokens
            })
            total_tokens += page_tokens
        else:
            # Full file estimation
            file_tokens = metadata['estimated_tokens']
            file_estimates.append({
                'file': file,
                'estimated_tokens': file_tokens
            })
            total_tokens += file_tokens
    
    # Process additional files that are only in selections (not in files list)
    if selections:
        for file, selected_pages in selections.items():
            if file not in processed_files:  # Only process files not already handled
                if file not in file_cache:
                    file_estimates.append({
                        'file': file,
                        'error': 'File not found in cache'
                    })
                    continue
                
                # Calculate tokens for selected pages
                with open(file, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
                content = _clean_content(raw_content)
                pages = _extract_pages(content)
                
                page_tokens = 0
                for page_num in selected_pages:
                    if 1 <= page_num <= len(pages):
                        page_content = pages[page_num - 1]
                        page_tokens += len(page_content) // 4
                
                file_estimates.append({
                    'file': file,
                    'selected_pages': selected_pages,
                    'estimated_tokens': page_tokens
                })
                total_tokens += page_tokens
    
    return {
        'total_estimated_tokens': total_tokens,
        'files': file_estimates,
        'warning': 'Over 100k tokens' if total_tokens > 100000 else None
    }


def _read_file(file: str, page_list: Optional[List[int]] = None, start_page: Optional[int] = None, end_page: Optional[int] = None) -> Dict[str, Any]:
    """Read file content - full file, specific pages, or page ranges."""
    if file not in file_cache:
        return {"error": f"File {file} not found in cache"}
    
    metadata = file_cache[file]
    # Read and clean content at read time
    with open(file, 'r', encoding='utf-8') as f:
        raw_content = f.read()
    content = _clean_content(raw_content)
    
    # If no page parameters provided, return full file
    if page_list is None and start_page is None and end_page is None:
        return {
            'file': file,
            'mode': 'full',
            'char_count': metadata['char_count'],
            'estimated_tokens': metadata['estimated_tokens'],
            'content': content
        }
    
    # Extract pages
    page_contents = _extract_pages(content)
    total_pages = len(page_contents)
    
    # Determine which pages to include
    if page_list is not None:
        # Use page_list if provided
        for page_num in page_list:
            if page_num < 1 or page_num > total_pages:
                return {"error": f"Page {page_num} out of range (1-{total_pages})"}
        pages_to_include = sorted(page_list)
        mode_info = f"pages {page_list}"
    else:
        # Use range if page_list is None
        if start_page is None:
            start_page = 1
        if end_page is None:
            end_page = total_pages
            
        if start_page < 1 or start_page > total_pages:
            return {"error": f"start_page {start_page} out of range (1-{total_pages})"}
        if end_page < start_page or end_page > total_pages:
            return {"error": f"end_page {end_page} out of range ({start_page}-{total_pages})"}
            
        pages_to_include = list(range(start_page, end_page + 1))
        mode_info = f"pages {start_page}-{end_page}"
    
    # Build selected content
    selected_content = []
    for page_num in pages_to_include:
        selected_content.append(f"# Page {page_num}\n{page_contents[page_num - 1]}")
    
    final_content = '\n\n'.join(selected_content)
    char_count = len(final_content)
    
    return {
        'file': file,
        'mode': mode_info,
        'selected_pages': pages_to_include,
        'char_count': char_count,
        'estimated_tokens': char_count // 4,
        'content': final_content
    }


# Helper functions
def _clean_content(content: str) -> str:
    """Clean and normalize transcript content for LLM consumption."""
    # Normalize whitespace
    content = re.sub(r'\r\n', '\n', content)
    content = re.sub(r'\r', '\n', content)
    
    # Collapse multiple spaces
    content = re.sub(r'[ \t]+', ' ', content)
    
    # Collapse multiple newlines (keep max 2)
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Collapse repeated punctuation
    content = re.sub(r'\.{4,}', '…', content)
    content = re.sub(r'-{3,}', '---', content)
    
    return content.strip()


def _extract_pages(content: str) -> List[str]:
    """Extract individual page sections from content."""
    pages = re.split(r'^# Page \d+', content, flags=re.MULTILINE)
    # Remove empty first element from split
    pages = [page.strip() for page in pages if page.strip()]
    return pages


def _get_snippet_around_position(content: str, position: int, context: int = 100) -> str:
    """Get snippet around a position in content."""
    start = max(0, position - context)
    end = min(len(content), position + context)
    return content[start:end]


@mcp.tool()
def sync_directory(directory_path: str = "./transcripts") -> Dict[str, Any]:
    """
    MANDATORY FIRST STEP: Sync directory to build/update file metadata cache for efficient operations.
    
    Scans directory for .md transcript files and creates persistent cache (.supercache.json) containing
    file metadata (filename, last_modified, char_count, estimated_tokens, pages).
    
    Usage Strategy:
    - ALWAYS call this first in any workflow to ensure cache is current
    - Re-run if search results seem outdated or missing recent files  
    - Cache persists across sessions for performance optimization
    
    Args:
        directory_path: Directory path containing transcript .md files (default: "./transcripts")
        
    Returns:
        Dict with sync results: {"processed": int, "new_files": int, "updated_files": int, "total_cached": int}
        
    Example: sync_directory("./transcripts") → Cache updated with 25 files, 5 new, 2 modified
    """
    try:
        result = _sync_files(directory_path)
        return result
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def find_files_by_name(query: str, regex: bool = False, safe: bool = True) -> Dict[str, Any]:
    """
    Search transcript filenames by company, ticker, date, or pattern. Use for targeted file discovery.
    
    Searches cached filenames for matches. Ideal for company-specific or date-specific targeting.
    
    Search Strategy:
    - Company targeting: "AAPL", "Apple", "Microsoft"
    - Date patterns: "2024", "Q3", "earnings"
    - Complex patterns: Use regex=True for "AAPL.*2024.*Q[1-4]"
    - Extract specific keywords from user queries before searching
    
    Args:
        query: Search term (ticker, company name, date pattern)
        regex: Use regex patterns for complex matching (default: False)
        safe: Warn if >10 results, prevents accidental large result sets (default: True)
        
    Returns:
        Dict: {"preview": bool, "count": int, "results": [{"file": str, "filename": str, "estimated_tokens": int, "pages": int}]}
        If preview=True: Results exceed safe limit, use safe=False to override
        
    Examples: find_files_by_name("AAPL") → 3 Apple transcript files
              find_files_by_name(".*2024.*Q[1-2]", regex=True) → Q1/Q2 2024 files
    """
    try:
        result = _search_filenames(query, regex, safe)
        return result
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def search_transcript_content(query: str, files: Optional[List[str]] = None, regex: bool = False, 
                            with_snippets: bool = True, safe: bool = True) -> Dict[str, Any]:
    """
    Search transcript content for thematic analysis. Use for keyword/topic discovery across files.
    
    Full-text search with snippet extraction. Ideal for finding financial terms, strategic topics, 
    management discussions, Q&A content, or identifying section boundaries.
    
    Search Strategy:
    - Financial terms: "revenue", "EBITDA", "guidance", "margin" 
    - Strategic topics: "AI", "cloud", "competition", "outlook"
    - Section identification: "Q&A", "presentation", "operator" (for segmentation)
    - Extract specific keywords from user queries, break complex topics into searchable terms
    
    Args:
        query: Search term (financial keywords, strategic topics, section markers)
        files: Specific files to search (default: None searches all cached files)
        regex: Use regex for complex patterns (default: False)
        with_snippets: Include context around matches for relevance validation (default: True)
        safe: Warn if >10 files match, prevents large result sets (default: True)
        
    Returns:
        Dict: {"preview": bool, "count": int, "results": [{"file": str, "match_count": int, "snippets": []}]}
        snippets show context around matches for content validation
        
    Examples: search_transcript_content("revenue growth") → 8 files with revenue discussions
              search_transcript_content("Q&A") → Files with Q&A sections for segmentation
    """
    try:
        result = _search_content(query, files, regex, with_snippets, safe)
        return result
    except Exception as e:

        return {"error": str(e)}


@mcp.tool()
def preview_transcript_lines(file: str, start_line: int = 1, end_line: Optional[int] = None, 
                           safe: bool = True) -> Dict[str, Any]:
    """
    VALIDATION STEP: Preview specific lines to validate content relevance before token calculation/reading.
    
    Quick content sampling for relevance validation. Use to check if file contains target content
    before committing to token estimation and full reading.
    
    Usage Strategy:
    - Validate search results: Check if files actually contain relevant content
    - Sample key sections: Opening lines, specific page ranges, around search matches
    - Content quality check: Ensure transcripts are properly formatted and readable
    - NOT for extensive reading - use read_transcript_file() for actual content retrieval
    
    Args:
        file: File path from search results to validate
        start_line: Starting line (1-indexed, default: 1 for opening preview)
        end_line: Ending line (inclusive, default: None for full file)
        safe: Warn if >2000 chars to prevent accidental large previews (default: True)
        
    Returns:
        Dict: {"preview": bool, "content": str, "char_count": int, "total_lines": int, "estimated_tokens": int}
        If preview=True: Content exceeds safe limit, use safe=False to override
        
    Examples: preview_transcript_lines(file, 1, 50) → First 50 lines for opening validation
              preview_transcript_lines(file, 200, 250) → Sample around Q&A section
    """
    try:
        result = _preview_file(file, start_line, end_line, safe)

        return result
    except Exception as e:

        return {"error": str(e)}


@mcp.tool()
def get_page_segments(file: str, page_list: Optional[List[int]] = None, start_page: int = 1, 
                     end_page: int = 2, max_chars: int = 500) -> Dict[str, Any]:
    """
    LARGE FILE VALIDATION: Get truncated page previews for section-based content validation and segmentation.
    
    Returns page previews with character limits. Use for validating large file sections and planning
    strategic page selection before full reading. Essential for >25K token files requiring segmentation.
    
    Usage Strategy:
    - Section validation: Preview key sections (mgmt presentation, Q&A) for relevance
    - Segmentation planning: Identify which pages contain target content for selective reading
    - Large file overview: Get sense of content distribution across pages
    - Use search_transcript_content() results to guide page selection
    
    Args:
        file: Large file (>25K tokens) requiring segmentation validation
        page_list: Specific pages to preview [1,3,5] (overrides range if provided)
        start_page: Range start (default: 1, used only if page_list is None)
        end_page: Range end (default: 2, used only if page_list is None)
        max_chars: Preview limit per page to prevent large returns (default: 500)
        
    Returns:
        Dict: {"file": str, "total_pages": int, "segments": [{"page": int, "estimated_tokens": int, "content": str}]}
        Use segments to decide which pages to include in final read_transcript_file() call
        
    Examples: get_page_segments(large_file, [1,5,10]) → Preview opening, middle, Q&A sections
              get_page_segments(large_file, start_page=1, end_page=3) → Management presentation overview
    """
    try:
        result = _segment_file(file, page_list, start_page, end_page, max_chars)

        return result
    except Exception as e:

        return {"error": str(e)}


@mcp.tool()
def calculate_token_usage(files: List[str], selections: Optional[Dict[str, List[int]]] = None) -> Dict[str, Any]:
    """
    TOKEN PLANNING: Calculate total tokens for validated files to determine loading strategy (ONLY for validated files).
    
    Essential step before reading to determine if <100K (load all) or >100K (prioritize/segment).
    Use ONLY after content validation via preview tools.
    
    Usage Strategy:
    - Input: Files that passed validation via preview_transcript_lines() or get_page_segments()
    - Decision point: <100K total = read all files entirely, >100K total = apply prioritization
    - Page selections: Use specific pages from get_page_segments() validation for large files
    - Warns if >100K tokens to trigger prioritization workflow
    
    Args:
        files: Validated file paths (from preview step) to estimate
        selections: Optional page selections {"file.md": [1,3,5]} from segmentation validation
        
    Returns:
        Dict: {"total_estimated_tokens": int, "files": [{"file": str, "estimated_tokens": int}], "warning": str}
        warning appears if >100K tokens, triggering prioritization workflow
        
    Examples: calculate_token_usage(validated_files) → {"total_estimated_tokens": 85000} → Load all
              calculate_token_usage(validated_files) → {"total_estimated_tokens": 150000, "warning": "Over 100k tokens"} → Prioritize
              calculate_token_usage(files, {"large_file.md": [1,2,5]}) → Estimate with page selections
    """
    try:
        result = _estimate_tokens(files, selections)

        return result
    except Exception as e:

        return {"error": str(e)}


@mcp.tool()
def read_transcript_file(file: str, page_list: Optional[List[int]] = None, start_page: Optional[int] = None, 
                        end_page: Optional[int] = None) -> Dict[str, Any]:
    """
    FINAL STEP: Read transcript content for analysis. Use after validation and token planning.
    
    Returns cleaned, normalized transcript content ready for LLM analysis. This is the primary
    content retrieval tool for actual financial analysis.
    
    Reading Strategy:
    - Small files (≤25K tokens): Always read entirely (no page parameters)
    - Large files (>25K tokens): Use page selections from get_page_segments() validation
    - Multiple files <100K total: Read all entirely
    - Multiple files >100K total: Read by priority (recency/relevancy), segment large files
    
    Args:
        file: Validated file path (from token planning step)
        page_list: Specific pages [1,3,5] (from get_page_segments validation, overrides ranges)
        start_page: Page range start (used only if page_list is None)
        end_page: Page range end (used only if page_list is None)
        
    Returns:
        Dict: {"file": str, "mode": str, "content": str, "estimated_tokens": int, "char_count": int}
        mode indicates reading approach: "full", "pages [1,3,5]", "pages 1-5"
        content is cleaned, normalized transcript ready for financial analysis
        
    Examples: read_transcript_file(small_file) → Full transcript for comprehensive analysis
              read_transcript_file(large_file, page_list=[1,2,5]) → Key sections from segmentation validation
              read_transcript_file(file, start_page=1, end_page=3) → Management presentation section
    """
    try:
        result = _read_file(file, page_list, start_page, end_page)
        mode = result.get('mode', 'unknown')
        tokens = result.get('estimated_tokens', 0)

        return result
    except Exception as e:

        return {"error": str(e)}


@mcp.tool()
def server_info() -> Dict[str, Any]:
    """
    Get server status and cache information. Use to verify system health and available transcript count.
    
    Returns server capabilities and current cache status. Useful for troubleshooting and
    understanding available transcript inventory.
    
    Returns:
        Dict: {"server": str, "status": str, "cached_files": int, "capabilities": [], "tools": []}
        cached_files shows number of transcripts available for search and analysis
        
    Example: server_info() → {"server": "SuperSearch Financial Transcripts", "cached_files": 47, "status": "active"}
    """
    try:
        return {
            "server": "SuperSearch Financial Transcripts MCP",
            "version": "1.0.0",
            "status": "active",
            "cached_files": len(file_cache),
            "capabilities": [
                "Directory synchronization",
                "Filename search (text & regex)",
                "Full-text content search",
                "Line-based file preview",
                "Page-based file segmentation", 
                "Token usage estimation",
                "Complete file reading"
            ],
            "tools": [
                "sync_directory",
                "find_files_by_name",
                "search_transcript_content",
                "preview_transcript_lines",
                "get_page_segments",
                "calculate_token_usage",
                "read_transcript_file",
                "server_info"
            ]
        }
    except Exception as e:

        return {"error": str(e), "status": "error"}


def main():
    """Run the SuperSearch MCP server"""
    
    # Start the MCP server
    mcp.run()


if __name__ == "__main__":
    main()