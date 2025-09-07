"""
Daloopa MCP Server - Direct API Integration
Professional financial data server using Daloopa's direct API access
"""

import os
import requests
from typing import Dict, Any, List, Union
from fastmcp import FastMCP

# Initialize FastMCP server with Daloopa's official prompt instructions
mcp = FastMCP(
    name="Daloopa Financial Data MCP",
    instructions="""
        Professional financial data server using Daloopa's API for investment analysis.
        
        CAPABILITIES:
        1. Search for companies by ticker symbol or company name
        2. Discover available financial metrics for specific companies  
        3. Retrieve detailed financial data across time periods

        WORKFLOW:
        1. Company Discovery: Use discover_companies() with ticker or company name
        2. Series Discovery: Use discover_company_series() to find available metrics
        3. Data Retrieval: Use get_company_fundamentals() for specific financial data

        SEARCH BEST PRACTICES:
        - For tickers: Use exact symbol (e.g., "AAPL", "MSFT")
        - For names: Use core name only, omit legal designations
          * Good: "Apple", "Microsoft" 
          * Avoid: "Apple Inc.", "Microsoft Corporation"

        DATA ANALYSIS:
        - Present data in standard financial table format
        - Time periods as columns, metrics as rows
        - Provide YoY/QoQ growth context when relevant
        - Highlight significant trends and anomalies
        
        Always add "Data sourced from Daloopa" at the end of responses.
    """
)

# API Configuration
DALOOPA_API_KEY = os.getenv("DALOOPA_API_KEY")
if not DALOOPA_API_KEY:
    raise ValueError("DALOOPA_API_KEY environment variable is required")

DALOOPA_BASE_URL = "https://app.daloopa.com/api/v2"

@mcp.tool
def discover_companies(keyword: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Search for companies in the Daloopa database using ticker symbols or company names.
    
    This tool searches the Daloopa database for companies matching the provided keyword,
    which can be either a ticker symbol or company name. The search results include
    the ticker, full company name, and company ID needed for subsequent data retrieval.
    
    Search Strategy:
    1. For ticker search: Use the exact ticker symbol (e.g., "AAPL", "MSFT")
    2. For name search: Use only the core company name
       - IMPORTANT: Omit legal entity designations (Inc., Ltd., Corp., LLC, GmbH, S.A., etc.)
       - Examples: Use "Apple" instead of "Apple Inc.", "Microsoft" instead of "Microsoft Corporation"
    3. If initial search returns no results, try alternative forms of the company name
       - Try shorter versions of the name if the full name doesn't yield results
       - For companies with multiple words, try the most distinctive word
    
    Args:
        keyword (str): The search term - either a ticker symbol or company name
                      (without legal entity designations)
    
    Returns:
        Union[List[Dict[str, Any]], Dict[str, Any]]: On success - list of companies, each containing:
            - name (str): The full company name
            - ticker (str): The stock ticker symbol
            - model_updated_at (str): When the model was last updated
            - earliest_quarter (str): First period with available data
            - latest_quarter (str): Latest period with available data  
            - companyidentifier_set (List[Dict]): Company identifiers (ISIN, CIK, etc.)
        On error - dictionary containing:
            - error (str): Error message
            - keyword (str): The search term that caused the error
            
    Examples:
        - Search by ticker: discover_companies("AAPL")
        - Search by name: discover_companies("Apple")
        - NOT: discover_companies("Apple Inc.") or discover_companies("Apple Incorporated")
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
            return response.json()
        else:
            return {
                "error": f"API returned {response.status_code}: {response.text}",
                "keyword": keyword
            }
            
    except Exception as e:
        return {"error": f"Error searching companies: {str(e)}", "keyword": keyword}

@mcp.tool
def discover_company_series(company_id: int, keywords: List[str]) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Retrieve a list of all financial series available for a specific company.
    
    This tool fetches all financial series for a given company_id, filtering by keywords.
    The series include various financial metrics and their respective IDs.
    
    Args:
        company_id (int): The unique identifier for the company in Daloopa's system
        keywords (List[str]): List of keywords to filter the series by name
        
    Returns:
        Union[List[Dict[str, Any]], Dict[str, Any]]: On success - list of financial series, each containing:
            - id (int): The unique identifier for the series
            - full_series_name (str): Full hierarchical context (e.g., "Income Statement | Revenue")
        On error - dictionary containing:
            - error (str): Error message
            - company_id (int): The company ID that caused the error
            - keywords (List[str]): The keywords that caused the error
    """
    try:
        headers = {
            "Authorization": f"Basic {DALOOPA_API_KEY}",
            "accept": "application/json"
        }
        
        params = {"company_id": company_id}
        if keywords:
            params["keywords"] = keywords
        
        response = requests.get(
            f"{DALOOPA_BASE_URL}/companies/series",
            params=params,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"API returned {response.status_code}: {response.text}",
                "company_id": company_id,
                "keywords": keywords
            }
            
    except Exception as e:
        return {
            "error": f"Error fetching company series: {str(e)}", 
            "company_id": company_id,
            "keywords": keywords
        }

@mcp.tool
def get_company_fundamentals(company_id: int, periods: List[str], series_ids: List[int]) -> Union[Dict[str, Any], Dict[str, Any]]:
    """
    Retrieve financial fundamentals for a specific company across specified periods.
    
    This tool fetches detailed financial data for a given company across requested time periods,
    optionally filtered by specific series IDs.
    
    Args:
        company_id (int): The unique identifier for the company in Daloopa's system
        periods (List[str]): List of periods in YYYYQQ format (e.g., ["2023Q1", "2023Q2"])
        series_ids (List[int]): List of series IDs to retrieve specific metrics
        
    Returns:
        Union[Dict[str, Any], Dict[str, Any]]: On success - paginated API response containing:
            - count (int): Total number of matching results available
            - next (str): URL to next page or null
            - previous (str): URL to previous page or null
            - results (List[Dict]): List of financial datapoints, each containing:
                - id (int): Unique datapoint identifier (fundamental_id for citations)
                - label (str): Short description of the datapoint
                - category (str): Financial statement section
                - value_raw (float): Raw financial value
                - value_normalized (float): Normalized financial value
                - unit (str): Unit of measurement (million, billion, etc.)
                - calendar_period (str): Calendar period (YYYYQQ format)
                - fiscal_period (str): Fiscal period (YYYYQQ format)
                - series_id (int): Series identifier
                - title (str): Full hierarchical context
        On error - dictionary containing:
            - error (str): Error message
            - company_id (int): The company ID that caused the error
            - periods (List[str]): The periods that caused the error
            - series_ids (List[int]): The series IDs that caused the error
    """
    try:
        headers = {
            "Authorization": f"Basic {DALOOPA_API_KEY}",
            "accept": "application/json"
        }
        
        params = {
            "company_id": company_id,
            "periods": periods,
            "limit": 100,
            "offset": 0
        }
        
        if series_ids:
            params["series_ids"] = series_ids
        
        response = requests.get(
            f"{DALOOPA_BASE_URL}/companies/fundamentals",
            params=params,
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"API returned {response.status_code}: {response.text}",
                "company_id": company_id,
                "periods": periods,
                "series_ids": series_ids
            }
            
    except Exception as e:
        return {
            "error": f"Error fetching fundamentals: {str(e)}", 
            "company_id": company_id,
            "periods": periods,
            "series_ids": series_ids
        }

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()