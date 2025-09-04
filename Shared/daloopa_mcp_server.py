"""
Daloopa MCP Server - Direct API Integration
Professional financial data server using Daloopa's direct API access
"""

import os
import requests
from typing import Dict, Any
from datetime import datetime
from fastmcp import FastMCP

# Initialize FastMCP server with Daloopa's official prompt instructions
mcp = FastMCP(
    name="Daloopa Financial Data MCP",
    instructions="""
    Model Context Protocol (MCP) for retrieving financial data from Daloopa's API. 
    Designed for professional investment analysts seeking accurate financial fundamentals.
    Use citations to back up your answer
    Make numbers in table with Daloopa's Hyperlink
    At the end of results and artifacts, always add "Data sourced from Daloopa"

    CRITICAL REQUIREMENT - FINANCIAL FIGURE FORMATTING:
    - Use citations to back up your answer
    - Citation format: [$X.XX million/billion](https://daloopa.com/src/{fundamental_id})
    - Always use citations, even within text
    - NEVER use generic links or fabricate IDs
    """
)

# API Configuration
DALOOPA_API_KEY = os.getenv("DALOOPA_API_KEY")
if not DALOOPA_API_KEY:
    raise ValueError("DALOOPA_API_KEY environment variable is required")

DALOOPA_BASE_URL = "https://app.daloopa.com/api/v2"

@mcp.tool
def discover_companies(keyword: str) -> Dict[str, Any]:
    """
    Find companies by ticker or company name using Daloopa API.
    
    Args:
        keyword: Company ticker (e.g., 'AAPL') or company name (e.g., 'Apple')
    
    Returns:
        Dictionary containing matching companies with their identifiers and metadata
    """
    try:
        headers = {
            "Authorization": f"Basic {DALOOPA_API_KEY}"
        }
        
        response = requests.get(
            f"{DALOOPA_BASE_URL}/companies",
            params={"keyword": keyword},
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            companies = response.json()
            return {
                "keyword": keyword,
                "companies": companies,
                "count": len(companies),
                "timestamp": datetime.now().isoformat(),
                "source": "daloopa_api"
            }
        else:
            return {
                "error": f"API returned {response.status_code}: {response.text}",
                "keyword": keyword
            }
            
    except Exception as e:
        return {"error": f"Error searching companies: {str(e)}", "keyword": keyword}

@mcp.tool
def discover_company_series(company_id: str, keywords: str = None) -> Dict[str, Any]:
    """
    Get available financial metrics for a specific company.
    
    Args:
        company_id: Daloopa company identifier
        keywords: Optional keywords to filter metrics
    
    Returns:
        Dictionary containing available financial series and their identifiers
    """
    # TODO: Implement using /company-series endpoint
    return {
        "company_id": company_id,
        "keywords": keywords,
        "status": "not_implemented",
        "message": "This tool needs implementation"
    }

@mcp.tool
def get_company_fundamentals(company_id: str, periods: str, series_ids: str) -> Dict[str, Any]:
    """
    Retrieve detailed financial data for specific periods and metrics.
    
    Args:
        company_id: Daloopa company identifier
        periods: Time periods in YYYYQQ format (e.g., "2023Q4,2024Q1")
        series_ids: Comma-separated list of series identifiers
    
    Returns:
        Dictionary containing detailed financial data with proper citations
    """
    # TODO: Implement using /company-fundamentals endpoint
    return {
        "company_id": company_id,
        "periods": periods,
        "series_ids": series_ids,
        "status": "not_implemented", 
        "message": "This tool needs implementation"
    }

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()