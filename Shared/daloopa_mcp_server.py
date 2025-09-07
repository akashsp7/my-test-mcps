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
        Model Context Protocol (MCP) for retrieving financial data from Daloopa's API. 
        Designed for professional investment analysts seeking accurate financial fundamentals.

        CAPABILITIES:
        1. Discover companies by ticker symbol or company name
        2. Find available financial metrics for specific companies
        3. Retrieve detailed financial data for specified time periods

        COMPREHENSIVE WORKFLOW GUIDELINES:

        1. Company Search Strategy:
           - First, search using the exact ticker symbol (e.g., AAPL, MSFT)
           - If no results found, search using the core company name
           - When searching by name, ALWAYS omit legal entity designations (Inc., Ltd., Corp., GmbH, S.A., etc.)
           - Use only the distinctive part of the company name (e.g., "Apple" not "Apple Inc.")
           - For best results with name searches, use the shortest unique identifier (e.g., "Microsoft" not "Microsoft Corporation")
           - Use "latest_quarter" field to determine the most recent quarter available for the company

        2. Series Selection:
           - EXTRACT SPECIFIC KEYWORDS from the user's prompt (e.g., if they ask about "revenue growth" or "profit margins")
           - EXTRACT ALL NECESSARY SERIES before calling get_company_fundamentals tool
           - Use these extracted keywords to search for relevant financial metrics
           - If the user doesn't specify any particular metrics, search for common financial statement categories:
             * Income Statement items (revenue, net income, EPS, etc.)
             * Balance Sheet items (assets, liabilities, equity, etc.)
             * Cash Flow items (operating cash flow, free cash flow, etc.)
        
        3. Datapoints Retrieval:
           - Call this tool after fetching all necessary series_ids
           - Only call it more times if data for different periods is needed or if there are more than 50 series
           - After identifying the series_ids, fetch the actual financial data for the specified periods
           - Ensure to include all relevant financial figures with proper formatting
           - Provide context for the data (e.g., YoY growth, industry benchmarks)

        DATA INTERPRETATION BEST PRACTICES:
        - Always provide context for financial figures (YoY growth, industry benchmarks)
        - Highlight significant trends or anomalies in the data
        - Consider seasonal factors when analyzing quarterly results
        - Provide concise, insightful analysis rather than just raw numbers
        - Use standard financial analysis table format: 
            - Horizontal axis = time periods
            - Vertical axis = financial metrics/series

        MANDATORY TABLE FORMAT:
        ALWAYS use standard financial analysis table format:
        - Horizontal axis (columns) = time periods (Q1 2023, Q2 2023, etc.)
        - Vertical axis (rows) = financial metrics/series (Revenue, Net Income, etc.)
        NEVER put time periods as rows or metrics as columns.
        
        Example correct format:
        | Metric | Q1 2023 | Q2 2023 | Q3 2023 |
        |--------|---------|---------|---------|
        | Revenue | $X.X billion | $X.X billion | $X.X billion |
        | Net Income | $X.X million | $X.X million | $X.X million |

        CRITICAL GUIDANCE RULES:
        Before comparing Guidance vs Actual:
        1. FIRST: Create quarter mapping table showing guidance quarter → results quarter (+1)
        2. SECOND: Verify each comparison follows the +1 quarter offset rule
        3. THIRD: Proceed with analysis only after confirming correct matching
            RULES: 
                - Companies provide guidance for the NEXT quarter, not the current quarter.
                - Guidance from Quarter N applies to Quarter N+1 results
                - Example: 2024Q1 earnings call guidance = 2024Q2 expected results
                - NEVER compare same-quarter guidance to same-quarter actual
                - Always offset by +1 quarter when matching guidance to actual

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
            - latest_quarter (str): Latest period with available data (use to determine most recent data availability)
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
    The series include various financial metrics and their respective IDs needed for data retrieval.
    
    Keyword Extraction Methodology:
    - EXTRACT SPECIFIC KEYWORDS from the user's request (e.g., "revenue growth", "profit margins", "cash flow")
    - Use extracted keywords to identify relevant financial metrics
    - If user doesn't specify metrics, search for comprehensive financial statement categories:
      * Income Statement: revenue, net income, earnings per share, operating income, gross profit, EBITDA
      * Balance Sheet: total assets, total liabilities, shareholders equity, cash and cash equivalents, debt
      * Cash Flow Statement: operating cash flow, free cash flow, capital expenditures, dividends
      * Financial Ratios: ROE, ROA, debt-to-equity, current ratio, profit margins
    - Use broader category terms if specific metrics aren't found
    
    Args:
        company_id (int): The unique identifier for the company in Daloopa's system
        keywords (List[str]): List of keywords to filter the series by name (extracted from user query)
        
    Returns:
        Union[List[Dict[str, Any]], Dict[str, Any]]: On success - list of financial series, each containing:
            - id (int): The unique identifier for the series (required for get_company_fundamentals)
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
    optionally filtered by specific series IDs. The data includes metrics from Income Statement,
    Balance Sheet, Cash Flow Statement, and various financial ratios.
    
    Args:
        company_id (int): The unique identifier for the company in Daloopa's system
        periods (List[str]): List of periods in YYYYQQ format (e.g., ["2023Q1", "2023Q2"])
                            For annual data, use FY (e.g., "2022FY" for full year 2022)
        series_ids (List[int]): List of specific financial metric IDs to retrieve (from discover_company_series)
        
    Returns:
        Union[Dict[str, Any], Dict[str, Any]]: On success - paginated API response containing:
            - count (int): Total number of matching results available
            - next (str): URL to next page or null
            - previous (str): URL to previous page or null
            - results (List[Dict]): List of financial datapoints, each containing:
                - id (int): Unique datapoint identifier (fundamental_id)
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
            
    Usage Guidelines:
    1. Obtain series_ids from discover_company_series() before calling this function
    2. Always present financial values with proper formatting and context
    3. Analysis Approaches:
       - For sequential analysis, request consecutive periods (e.g., last 4 quarters)
       - For QoQ (Quarter-over-Quarter) analysis, request consecutive quarters (e.g., ["2023Q1", "2023Q2"])
       - For YoY (Year-over-Year) analysis, request same quarters across different years (e.g., ["2022Q2", "2023Q2"])
       - For TTM (Trailing Twelve Months), aggregate the last 4 quarters of data
    
    MANDATORY TABLE FORMAT:
    ALWAYS use standard financial analysis table format:
        - Horizontal axis (columns) = time periods (Q1 2023, Q2 2023, etc.)
        - Vertical axis (rows) = financial metrics/series (Revenue, Net Income, etc.)
    NEVER put time periods as rows or metrics as columns.
        
    Example correct format:
    | Metric | Q1 2023 | Q2 2023 | Q3 2023 |
    |--------|---------|---------|---------|
    | Revenue | $X.X billion | $X.X billion | $X.X billion |
    | Net Income | $X.X million | $X.X million | $X.X million |

    CRITICAL GUIDANCE RULES:
    Before comparing Guidance vs Actual:
    1. FIRST: Create quarter mapping table showing guidance quarter → results quarter (+1)
    2. SECOND: Verify each comparison follows the +1 quarter offset rule
    3. THIRD: Proceed with analysis only after confirming correct matching
        RULES: 
            - Companies provide guidance for the NEXT quarter, not the current quarter.
            - Guidance from Quarter N applies to Quarter N+1 results
            - Example: 2024Q1 earnings call guidance = 2024Q2 expected results
            - NEVER compare same-quarter guidance to same-quarter actual
            - Always offset by +1 quarter when matching guidance to actual
    
    Data Analysis Best Practices:
    - Always provide context for financial figures (YoY growth, industry benchmarks)
    - Highlight significant trends or anomalies in the data
    - Consider seasonal factors when analyzing quarterly results
    - Provide concise, insightful analysis rather than just raw numbers
    - Include relevant financial ratios and performance metrics
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