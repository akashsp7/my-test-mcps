"""
SuperSearch MCP Tools - Individual Functions
Simple implementation for financial transcript search and analysis.

Based on PRP: MCP Server for Financial Transcripts & Earnings Calls
"""

import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


# Global variables for caching
CACHE_FILE = "transcript_cache.json"
file_cache = {}


def sync_files(directory_path: str = "./transcripts") -> Dict[str, any]:
    """
    Scan directory for new/modified .md files and update cached metadata.
    
    Args:
        directory_path: Path to directory containing transcript files
        
    Returns:
        Dict with sync results: files processed, new files, updated files
    """
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


def search_filenames(query: str, regex: bool = False, safe: bool = True) -> Dict[str, any]:
    """
    Search for files with matching filenames.
    
    Args:
        query: Search query string
        regex: Whether to treat query as regex pattern
        safe: If True, warns when results exceed 10 files
        
    Returns:
        Dict with results or preview warning
    """
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


def search_content(query: str, regex: bool = False, with_snippets: bool = True, safe: bool = True) -> Dict[str, any]:
    """
    Search for content within transcript files.
    
    Args:
        query: Search query string
        regex: Whether to treat query as regex pattern
        with_snippets: Include content snippets in results
        safe: If True, warns when results exceed 10 files
        
    Returns:
        Dict with results or preview warning
    """
    results = []
    
    for file_path, metadata in file_cache.items():
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
                for match in matches[:3]:  # Limit to first 5 matches
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


def preview_file(file: str, start_line: int = 1, end_line: Optional[int] = None, safe: bool = True) -> Dict[str, any]:
    """
    Preview specific line ranges from transcript files.
    
    Args:
        file: File path
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (inclusive). If None, goes to end of file
        safe: If True, warns when preview exceeds 2000 characters
        
    Returns:
        Dict with preview content or warning
    """
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


def segment_file(file: str, page_list: Optional[List[int]] = None, start_page: int = 1, end_page: int = 2, max_chars: int = 500) -> Dict[str, any]:
    """
    Return page segments from transcript file for specified pages.
    
    Args:
        file: File path
        page_list: List of specific page numbers to retrieve (e.g., [1,2,5,6]). If provided, ignores range parameters.
        start_page: Starting page number for range (default 1, used only if page_list is None)
        end_page: Ending page number for range (default 2, used only if page_list is None)
        max_chars: Maximum characters to show per page (default 500)
        
    Returns:
        Dict with page segments list and metadata
    """
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


def estimate_tokens(files: List[str], selections: Optional[Dict[str, List[int]]] = None) -> Dict[str, any]:
    """
    Estimate token usage for given files/pages.
    
    Args:
        files: List of file paths
        selections: Dict mapping file paths to list of page numbers
        
    Returns:
        Token estimation breakdown
    """
    total_tokens = 0
    file_estimates = []
    
    for file in files:
        if file not in file_cache:
            file_estimates.append({
                'file': file,
                'error': 'File not found in cache'
            })
            continue
        
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
    
    return {
        'total_estimated_tokens': total_tokens,
        'files': file_estimates,
        'warning': 'Over 50k tokens' if total_tokens > 50000 else None
    }


def read_file(file: str, mode: str = "full", pages: Optional[List[int]] = None) -> Dict[str, any]:
    """
    Read file content - full file or specific pages.
    
    Args:
        file: File path
        mode: "full" or "pages"
        pages: List of page numbers (for pages mode)
        
    Returns:
        File content with metadata
    """
    if file not in file_cache:
        return {"error": f"File {file} not found in cache"}
    
    metadata = file_cache[file]
    # Read and clean content at read time
    with open(file, 'r', encoding='utf-8') as f:
        raw_content = f.read()
    content = _clean_content(raw_content)
    
    if mode == "pages" and pages:
        page_contents = _extract_pages(content)
        selected_content = []
        
        for page_num in pages:
            if 1 <= page_num <= len(page_contents):
                selected_content.append(f"# Page {page_num}\n{page_contents[page_num - 1]}")
        
        final_content = '\n\n'.join(selected_content)
        char_count = len(final_content)
        
        return {
            'file': file,
            'mode': 'pages',
            'selected_pages': pages,
            'char_count': char_count,
            'estimated_tokens': char_count // 4,
            'content': final_content
        }
    
    else:  # full mode
        return {
            'file': file,
            'mode': 'full',
            'char_count': metadata['char_count'],
            'estimated_tokens': metadata['estimated_tokens'],
            'content': content
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


if __name__ == "__main__":
    # Simple test
    print("SuperSearch Tools - Individual Functions")
    print("Available functions:")
    print("- sync_files()")
    print("- search_filenames()")
    print("- search_content()")
    print("- preview_file()")
    print("- segment_file()")
    print("- estimate_tokens()")
    print("- read_file()")