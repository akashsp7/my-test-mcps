#!/usr/bin/env python3
"""
SEC EDGAR MCP Server - Simple FastMCP Implementation
Can run as stdio (for Claude Desktop) or as HTTP server (for remote hosting)
"""

import logging
import os
from fastmcp import FastMCP
from sec_edgar_mcp.tools import CompanyTools, FilingsTools, FinancialTools, InsiderTools

# Suppress INFO logs from edgar library
logging.getLogger("edgar").setLevel(logging.WARNING)

# Set default user agent if not provided
if not os.getenv("SEC_EDGAR_USER_AGENT"):
    os.environ["SEC_EDGAR_USER_AGENT"] = "FirstName LastName blahblah@blah.com"

DETERMINISTIC_INSTRUCTIONS = """
CRITICAL: When responding to SEC filing data requests, you MUST follow these rules:

1. ONLY use data from the SEC filing provided by the tools - NO EXTERNAL KNOWLEDGE
2. ALWAYS include complete filing reference information:
   - Filing date, form type, accession number
   - Direct SEC URL for verification
   - Period/context for each data point
3. NEVER add external knowledge, estimates, interpretations, or calculations
4. NEVER analyze trends, provide context, or make comparisons not in the filing
5. Be completely deterministic - identical queries must give identical responses
6. If data is not in the filing, state "Not available in this filing" - DO NOT guess or estimate
7. ALWAYS specify the exact period/date/context for each piece of data from the XBRL
8. PRESERVE EXACT NUMERIC PRECISION - NO ROUNDING! Use the exact values from the filing
9. Include clickable SEC URL so users can independently verify all data
10. State that all data comes directly from SEC EDGAR filings with no modifications

EXAMPLE RESPONSE FORMAT:
"Based on [Company]'s [Form Type] filing dated [Date] (Accession: [Number]):
- [Data point]: $37,044,000,000 (Period: [Date]) - EXACT VALUE, NO ROUNDING
- [Data point]: $12,714,000,000 (Period: [Date]) - EXACT VALUE, NO ROUNDING

Source: SEC EDGAR Filing [Accession Number], extracted directly from XBRL data with no rounding or estimates.
Verify at: [SEC URL]"

CRITICAL: NEVER round numbers like "$37.0B" - always show exact values like "$37,044,000,000"

YOU ARE A FILING DATA EXTRACTION SERVICE, NOT A FINANCIAL ANALYST OR ADVISOR.
"""

# Initialize MCP server
mcp = FastMCP(
    name="SEC EDGAR MCP",
    instructions=DETERMINISTIC_INSTRUCTIONS,
    dependencies=["edgartools"]
)

# Initialize tool classes
company_tools = CompanyTools()
filings_tools = FilingsTools()
financial_tools = FinancialTools()
insider_tools = InsiderTools()

# Company Tools
@mcp.tool()
def get_cik_by_ticker(ticker: str):
    """Get the CIK for a company based on its ticker symbol."""
    return company_tools.get_cik_by_ticker(ticker)

@mcp.tool()
def get_company_info(identifier: str):
    """Get detailed information about a company from SEC records."""
    return company_tools.get_company_info(identifier)

@mcp.tool()
def search_companies(query: str, limit: int = 10):
    """Search for companies by name."""
    return company_tools.search_companies(query, limit)

@mcp.tool()
def get_company_facts(identifier: str):
    """Get company facts and key financial metrics."""
    return company_tools.get_company_facts(identifier)

# Filing Tools
@mcp.tool()
def get_recent_filings(identifier: str = None, form_type: str = None, days: int = 30, limit: int = 50):
    """Get recent SEC filings."""
    return filings_tools.get_recent_filings(identifier, form_type, days, limit)

@mcp.tool()
def get_filing_content(identifier: str, accession_number: str):
    """Get the content of a specific SEC filing."""
    return filings_tools.get_filing_content(identifier, accession_number)

@mcp.tool()
def analyze_8k(identifier: str, accession_number: str):
    """Analyze an 8-K filing for specific events and items."""
    return filings_tools.analyze_8k(identifier, accession_number)

@mcp.tool()
def get_filing_sections(identifier: str, accession_number: str, form_type: str):
    """Get specific sections from a filing."""
    return filings_tools.get_filing_sections(identifier, accession_number, form_type)

# Financial Tools
@mcp.tool()
def get_financials(identifier: str, statement_type: str = "all"):
    """Get financial statements. PRESERVE EXACT NUMERIC PRECISION."""
    return financial_tools.get_financials(identifier, statement_type)

@mcp.tool()
def get_segment_data(identifier: str, segment_type: str = "geographic"):
    """Get revenue breakdown by segments."""
    return financial_tools.get_segment_data(identifier, segment_type)

@mcp.tool()
def get_key_metrics(identifier: str, metrics: list = None):
    """Get key financial metrics."""
    return financial_tools.get_key_metrics(identifier, metrics)

@mcp.tool()
def compare_periods(identifier: str, metric: str, start_year: int, end_year: int):
    """Compare a financial metric across periods."""
    return financial_tools.compare_periods(identifier, metric, start_year, end_year)

@mcp.tool()
def discover_company_metrics(identifier: str, search_term: str = None):
    """Discover available financial metrics."""
    return financial_tools.discover_company_metrics(identifier, search_term)

@mcp.tool()
def get_xbrl_concepts(identifier: str, accession_number: str = None, concepts: list = None, form_type: str = "10-K"):
    """Extract specific XBRL concepts from a filing."""
    return financial_tools.get_xbrl_concepts(identifier, accession_number, concepts, form_type)

@mcp.tool()
def discover_xbrl_concepts(identifier: str, accession_number: str = None, form_type: str = "10-K", namespace_filter: str = None):
    """Discover all available XBRL concepts in a filing."""
    return financial_tools.discover_xbrl_concepts(identifier, accession_number, form_type, namespace_filter)

# Insider Trading Tools
@mcp.tool()
def get_insider_transactions(identifier: str, form_types: list = None, days: int = 90, limit: int = 50):
    """Get insider trading transactions from SEC filings."""
    return insider_tools.get_insider_transactions(identifier, form_types, days, limit)

@mcp.tool()
def get_insider_summary(identifier: str, days: int = 180):
    """Get a summary of insider trading activity."""
    return insider_tools.get_insider_summary(identifier, days)

@mcp.tool()
def get_form4_details(identifier: str, accession_number: str):
    """Get detailed information from a Form 4 filing."""
    return insider_tools.get_form4_details(identifier, accession_number)

@mcp.tool()
def analyze_form4_transactions(identifier: str, days: int = 90, limit: int = 50):
    """Analyze Form 4 filings and extract transaction data."""
    return insider_tools.analyze_form4_transactions(identifier, days, limit)

@mcp.tool()
def analyze_insider_sentiment(identifier: str, months: int = 6):
    """Analyze insider trading sentiment and trends."""
    return insider_tools.analyze_insider_sentiment(identifier, months)

# Utility Tools
@mcp.tool()
def get_recommended_tools(form_type: str):
    """Get recommended tools for analyzing specific form types."""
    recommendations = {
        "10-K": {
            "tools": ["get_financials", "get_filing_sections", "get_segment_data", "get_key_metrics"],
            "description": "Annual report with comprehensive business and financial information",
            "tips": [
                "Use get_financials to extract financial statements",
                "Use get_filing_sections to read business description and risk factors",
                "Use get_segment_data for geographic/product revenue breakdown",
            ],
        },
        "10-Q": {
            "tools": ["get_financials", "get_filing_sections", "compare_periods"],
            "description": "Quarterly report with unaudited financial statements",
            "tips": [
                "Use get_financials for quarterly financial data",
                "Use compare_periods to analyze quarter-over-quarter trends",
            ],
        },
        "8-K": {
            "tools": ["analyze_8k", "get_filing_content"],
            "description": "Current report for material events",
            "tips": [
                "Use analyze_8k to identify specific events reported",
                "Check for press releases and material agreements",
            ],
        },
        "4": {
            "tools": [
                "get_insider_transactions",
                "analyze_form4_transactions",
                "get_form4_details",
                "analyze_insider_sentiment",
            ],
            "description": "Statement of changes in beneficial ownership",
            "tips": [
                "Use get_insider_transactions for recent trading activity overview",
                "Use analyze_form4_transactions for detailed transaction analysis and tables",
                "Use analyze_insider_sentiment to understand trading patterns",
            ],
        },
        "DEF 14A": {
            "tools": ["get_filing_content", "get_filing_sections"],
            "description": "Proxy statement with executive compensation and governance",
            "tips": ["Look for executive compensation tables", "Review shareholder proposals and board information"],
        },
    }

    form_type_upper = form_type.upper()
    if form_type_upper in recommendations:
        return {"success": True, "form_type": form_type_upper, "recommendations": recommendations[form_type_upper]}
    else:
        return {
            "success": True,
            "form_type": form_type_upper,
            "message": "No specific recommendations available for this form type",
            "general_tools": ["get_filing_content", "get_recent_filings"],
        }

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SEC EDGAR MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"], help="Transport protocol")
    parser.add_argument("--port", type=int, default=8080, help="Port for SSE transport")
    parser.add_argument("--host", default="0.0.0.0", help="Host for SSE transport")
    args = parser.parse_args()

    if args.transport == "sse":
        print(f"🚀 Starting SEC EDGAR MCP Server with SSE transport")
        print(f"   SSE endpoint: http://{args.host}:{args.port}/sse")
        print(f"   Message endpoint: http://{args.host}:{args.port}/message")
        mcp.run(transport="sse", port=args.port, host=args.host)
    else:
        mcp.run(transport="stdio")