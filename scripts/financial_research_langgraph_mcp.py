#!/usr/bin/env python3
"""
Enhanced Financial Research MCP Server with LangGraph Orchestration
Provides complex multi-step financial analysis workflows for hedge fund analysts.

Features:
- LangGraph-powered multi-step workflows
- Finnhub + SEC Edgar data integration
- Context preservation across workflow steps
- Comprehensive company research automation

Data Sources:
- Finnhub: Real-time quotes, company profiles, news, analyst data
- SEC Edgar: Regulatory filings, insider transactions, financial statements
"""

import os
import json
import requests
import asyncio
import logging
from typing import Dict, Any, Optional, List, Union, TypedDict
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# Core dependencies
from fastmcp import FastMCP

# LangGraph dependencies
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

# SEC Edgar integration
import sec_edgar_mcp
from sec_edgar_mcp.tools.company import CompanyTools
from sec_edgar_mcp.tools.filings import FilingsTools

# Initialize FastMCP server
mcp = FastMCP("Enhanced Financial Research MCP with LangGraph")

# =====================================================
# ENHANCED LOGGING SYSTEM
# =====================================================

class DataSource(Enum):
    """Data source types for logging and attribution"""
    FINNHUB_LIVE = "finnhub_live"
    SEC_EDGAR_LIVE = "sec_edgar_live"
    ALGORITHM = "algorithm"
    UNAVAILABLE = "unavailable"

class LogLevel(Enum):
    """Log levels for different types of information"""
    DEBUG = "DEBUG"
    INFO = "INFO" 
    WARN = "WARN"
    ERROR = "ERROR"

# Configure logging
LOG_LEVEL = os.getenv("MCP_LOG_LEVEL", "INFO").upper()
ENABLE_DATA_LOG = os.getenv("MCP_ENABLE_DATA_LOG", "true").lower() == "true"
ENABLE_WORKFLOW_LOG = os.getenv("MCP_ENABLE_WORKFLOW_LOG", "true").lower() == "true"

# Setup loggers
def setup_loggers():
    """Setup separate loggers for workflow and data tracking"""
    
    # Create logs directory if it doesn't exist
    log_dir = "/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Workflow logger - tracks step progression
    workflow_logger = logging.getLogger("financial_workflow")
    workflow_logger.setLevel(getattr(logging, LOG_LEVEL))
    
    if not workflow_logger.handlers:
        # File handler for workflow log
        workflow_fh = logging.FileHandler(f"{log_dir}/workflow.log")
        workflow_fh.setLevel(getattr(logging, LOG_LEVEL))
        
        # Console handler for workflow log
        workflow_ch = logging.StreamHandler()
        workflow_ch.setLevel(getattr(logging, LOG_LEVEL))
        
        # Workflow formatter
        workflow_formatter = logging.Formatter(
            '%(asctime)s | 🔄 WORKFLOW | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        workflow_fh.setFormatter(workflow_formatter)
        workflow_ch.setFormatter(workflow_formatter)
        
        if ENABLE_WORKFLOW_LOG:
            workflow_logger.addHandler(workflow_fh)
            workflow_logger.addHandler(workflow_ch)
    
    # Data source logger - tracks API calls and data sources
    data_logger = logging.getLogger("financial_data")
    data_logger.setLevel(getattr(logging, LOG_LEVEL))
    
    if not data_logger.handlers:
        # File handler for data log
        data_fh = logging.FileHandler(f"{log_dir}/data_sources.log")
        data_fh.setLevel(getattr(logging, LOG_LEVEL))
        
        # Console handler for data log  
        data_ch = logging.StreamHandler()
        data_ch.setLevel(getattr(logging, LOG_LEVEL))
        
        # Data formatter with source indicators
        data_formatter = logging.Formatter(
            '%(asctime)s | 📊 DATA | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        data_fh.setFormatter(data_formatter)
        data_ch.setFormatter(data_formatter)
        
        if ENABLE_DATA_LOG:
            data_logger.addHandler(data_fh)
            data_logger.addHandler(data_ch)
    
    return workflow_logger, data_logger

# Initialize loggers
workflow_log, data_log = setup_loggers()

def log_workflow_step(step_name: str, ticker: str, status: str, duration: float = None, details: str = "", step_data: Dict[str, Any] = None):
    """
    Log workflow step progress with comprehensive data capture.
    
    Args:
        step_name: Name of the workflow step
        ticker: Stock ticker being analyzed
        status: STARTED, COMPLETED, FAILED
        duration: Time taken in seconds (for COMPLETED/FAILED)
        details: Additional details or error info
        step_data: Complete step input/output data for comprehensive logging
    """
    if not ENABLE_WORKFLOW_LOG:
        return
        
    status_emoji = {
        "STARTED": "🚀",
        "COMPLETED": "✅", 
        "FAILED": "❌"
    }
    
    message = f"{status_emoji.get(status, '🔄')} {step_name} [{ticker}] - {status}"
    
    if duration is not None:
        message += f" ({duration:.2f}s)"
    
    if details:
        message += f" | {details}"
    
    # Add comprehensive step data logging for COMPLETED status
    if status == "COMPLETED" and step_data:
        # Create a summary of key data points
        if step_name == "Company Profile":
            profile = step_data.get("company_profile", {})
            basic_info = profile.get("basic_info", {})
            trading = profile.get("current_trading", {})
            message += f"\n    📊 PROFILE DATA: Name={basic_info.get('name', {}).get('value', 'N/A')}, Sector={basic_info.get('sector', {}).get('value', 'N/A')}, Price=${trading.get('current_price', {}).get('value', 'N/A')}"
        
        elif step_name == "News Analysis":
            news = step_data.get("news_analysis", {})
            summary = news.get("news_summary", {})
            sentiment = summary.get("sentiment_indicators", {})
            message += f"\n    📰 NEWS DATA: Articles={summary.get('total_articles', 0)}, Positive={sentiment.get('positive_articles', {}).get('value', 0)}, Negative={sentiment.get('negative_articles', {}).get('value', 0)}"
        
        elif step_name == "SEC Filings":
            sec = step_data.get("sec_filings", {})
            filings = sec.get("recent_filings", {})
            key_forms = filings.get("key_forms", {})
            message += f"\n    📋 SEC DATA: Total={filings.get('total_filings', 0)}, 10-K={key_forms.get('10-K', 0)}, 10-Q={key_forms.get('10-Q', 0)}, 8-K={key_forms.get('8-K', 0)}"
        
        elif step_name == "Analyst Data":
            analyst = step_data.get("analyst_data", {})
            recs = analyst.get("recommendations", {}).get("current_summary", {})
            earnings = analyst.get("earnings", {}).get("surprise_analysis", {})
            total_analysts = recs.get("total_analysts", {}).get("value", 0)
            avg_surprise = earnings.get("average_surprise", {}).get("value", 0)
            avg_surprise_str = f"{avg_surprise:.3f}" if avg_surprise is not None else "N/A"
            message += f"\n    📈 ANALYST DATA: Analysts={total_analysts}, Avg_Surprise={avg_surprise_str}, Buy_Rating={(recs.get('strong_buy', {}).get('value', 0) + recs.get('buy', {}).get('value', 0))/max(total_analysts, 1):.1%}"
        
        elif step_name == "Research Synthesis":
            summary = step_data.get("research_summary", {})
            metrics = summary.get("quantitative_metrics", {})
            quality = summary.get("data_quality", {})
            analyst_score = metrics.get('analyst_score', None)
            analyst_score_str = f"{analyst_score:.3f}" if analyst_score is not None else "N/A"
            message += f"\n    🎯 SYNTHESIS: Sentiment_Score={metrics.get('sentiment_score', 'N/A')}, Analyst_Score={analyst_score_str}, Completeness={quality.get('completeness_score', 0)}%"
    
    if status == "FAILED":
        workflow_log.error(message)
    elif status == "COMPLETED":
        workflow_log.info(message)
    else:
        workflow_log.debug(message)

def log_data_request(source: DataSource, endpoint: str, ticker: str, status: str, details: str = "", request_data: Dict[str, Any] = None, response_data: Dict[str, Any] = None):
    """
    Log data source requests with comprehensive request/response details.
    
    Args:
        source: DataSource enum indicating the data source type
        endpoint: API endpoint or data type requested
        ticker: Stock ticker being requested
        status: SUCCESS, FAILED, UNAVAILABLE
        details: Additional details about the request
        request_data: Full request parameters for detailed logging
        response_data: API response data (truncated for large responses)
    """
    if not ENABLE_DATA_LOG:
        return
        
    source_emoji = {
        DataSource.FINNHUB_LIVE: "🟢 LIVE",
        DataSource.SEC_EDGAR_LIVE: "🔵 LIVE",
        DataSource.ALGORITHM: "🟣 CALC",
        DataSource.UNAVAILABLE: "⚫ N/A"
    }
    
    status_emoji = {
        "SUCCESS": "✅",
        "FAILED": "❌",
        "UNAVAILABLE": "⚫"
    }
    
    source_indicator = source_emoji.get(source, "❓")
    status_indicator = status_emoji.get(status, "❓")
    
    message = f"{status_indicator} {source_indicator} | {endpoint} [{ticker}]"
    
    if details:
        message += f" | {details}"
    
    # Add comprehensive request/response logging
    if request_data:
        # Filter out sensitive data like API keys
        safe_request = {k: v for k, v in request_data.items() if k.lower() not in ['token', 'api_key', 'password']}
        message += f"\n    📤 REQUEST: {json.dumps(safe_request, separators=(',', ':'))}"
    
    if response_data:
        # Truncate large responses but keep structure visible
        if isinstance(response_data, dict):
            # For dict responses, show structure with truncated values
            truncated_response = {}
            for k, v in response_data.items():
                if isinstance(v, str) and len(v) > 200:
                    truncated_response[k] = f"{v[:200]}...[truncated]"
                elif isinstance(v, list) and len(v) > 5:
                    truncated_response[k] = f"[{len(v)} items: {v[:2]}...]"
                else:
                    truncated_response[k] = v
            message += f"\n    📥 RESPONSE: {json.dumps(truncated_response, separators=(',', ':'), default=str)}"
        elif isinstance(response_data, list) and len(response_data) > 3:
            message += f"\n    📥 RESPONSE: [{len(response_data)} items: {json.dumps(response_data[:2], separators=(',', ':'), default=str)}...]"
        else:
            message += f"\n    📥 RESPONSE: {json.dumps(response_data, separators=(',', ':'), default=str)}"
    
    if status == "FAILED":
        data_log.error(message)
    elif status == "UNAVAILABLE":
        data_log.warning(message)
    else:
        data_log.info(message)

def log_data_summary(ticker: str, total_calls: int, live_calls: int, unavailable_calls: int, failed_calls: int):
    """
    Log summary of data sources used for analysis.
    
    Args:
        ticker: Stock ticker analyzed
        total_calls: Total API/data calls made
        live_calls: Number of live API calls
        unavailable_calls: Number of unavailable data calls
        failed_calls: Number of failed calls
    """
    if not ENABLE_DATA_LOG:
        return
        
    live_pct = (live_calls / total_calls * 100) if total_calls > 0 else 0
    unavailable_pct = (unavailable_calls / total_calls * 100) if total_calls > 0 else 0
    
    message = f"📈 SUMMARY [{ticker}] | Total: {total_calls} | Live: {live_calls} ({live_pct:.0f}%) | Unavailable: {unavailable_calls} ({unavailable_pct:.0f}%) | Failed: {failed_calls}"
    
    if failed_calls > 0 or unavailable_calls > live_calls:
        data_log.warning(message)
    else:
        data_log.info(message)

# API Configuration
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

# Test mode if no API key is provided
TEST_MODE = not FINNHUB_API_KEY
if TEST_MODE:
    print("⚠️  WARNING: FINNHUB_API_KEY not found. Running in TEST MODE with mock data.")
    print("   Set FINNHUB_API_KEY environment variable for live data.")

# Initialize SEC Edgar tools
try:
    sec_company_tools = CompanyTools()
    sec_filings_tools = FilingsTools()
    SEC_EDGAR_AVAILABLE = True
except ValueError as e:
    print(f"⚠️  WARNING: SEC Edgar tools not available: {e}")
    print("   Set SEC_EDGAR_USER_AGENT environment variable for SEC data.")
    sec_company_tools = None
    sec_filings_tools = None
    SEC_EDGAR_AVAILABLE = False

# LangGraph State Definition
class ResearchState(TypedDict):
    """State object for research workflow."""
    ticker: str
    stage: str
    company_profile: Optional[Dict[str, Any]]
    market_data: Optional[Dict[str, Any]]
    news_analysis: Optional[Dict[str, Any]]
    sec_filings: Optional[Dict[str, Any]]
    analyst_data: Optional[Dict[str, Any]]
    research_summary: Optional[Dict[str, Any]]
    workflow_metadata: Dict[str, Any]

@dataclass
class WorkflowConfig:
    """Configuration for research workflows."""
    include_sec_filings: bool = True
    news_days_back: int = 7
    max_filings: int = 5
    include_insider_analysis: bool = True

def _finnhub_request(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Make authenticated request to Finnhub API with comprehensive logging."""
    symbol = params.get("symbol", "UNKNOWN")
    start_time = datetime.now()
    
    # Prepare safe request data for logging (without API key)
    safe_params = {k: v for k, v in params.items() if k.lower() not in ['token', 'api_key']}
    
    if TEST_MODE:
        # Generate mock response
        mock_response = None
        mock_response = {"error": "Data not available - API key not configured"}
        
        # Log unavailable data
        log_data_request(
            DataSource.UNAVAILABLE, 
            endpoint, 
            symbol, 
            "FAILED", 
            "Data not available - API key not configured",
            request_data=safe_params,
            response_data=mock_response
        )
        
        return mock_response
    
    if not FINNHUB_API_KEY:
        error_response = {"error": "FINNHUB_API_KEY not configured"}
        log_data_request(
            DataSource.UNAVAILABLE, 
            endpoint, 
            symbol, 
            "FAILED", 
            "FINNHUB_API_KEY not configured",
            request_data=safe_params,
            response_data=error_response
        )
        return error_response
    
    # Make live API request
    params["token"] = FINNHUB_API_KEY
    
    try:
        response = requests.get(f"{FINNHUB_BASE_URL}/{endpoint}", params=params, timeout=10)
        response.raise_for_status()
        
        duration = (datetime.now() - start_time).total_seconds()
        data = response.json()
        
        # Log successful live API call with full request/response
        log_data_request(
            DataSource.FINNHUB_LIVE, 
            endpoint, 
            symbol, 
            "SUCCESS", 
            f"Response time: {duration:.2f}s",
            request_data=safe_params,
            response_data=data
        )
        
        return data
        
    except requests.RequestException as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = f"Finnhub API error: {str(e)}"
        error_response = {"error": error_msg}
        
        # Log API failure with request details
        log_data_request(
            DataSource.FINNHUB_LIVE, 
            endpoint, 
            symbol, 
            "FAILED", 
            f"{error_msg} (after {duration:.2f}s)",
            request_data=safe_params,
            response_data=error_response
        )
        
        return error_response
        
    except json.JSONDecodeError:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = "Invalid JSON response from Finnhub"
        error_response = {"error": error_msg}
        
        # Log JSON decode error with request details
        log_data_request(
            DataSource.FINNHUB_LIVE, 
            endpoint, 
            symbol, 
            "FAILED", 
            f"{error_msg} (after {duration:.2f}s)",
            request_data=safe_params,
            response_data=error_response
        )
        
        return error_response

def _create_attributed_value(value: Any, source: str, confidence: str = "high") -> Dict[str, Any]:
    """Create a data point with source attribution for auditability."""
    return {
        "value": value,
        "source": source,
        "timestamp": datetime.now().isoformat(),
        "confidence": confidence
    }

# Workflow Node Functions
async def fetch_company_profile(state: ResearchState) -> ResearchState:
    """
    Fetch comprehensive company profile from multiple sources.
    
    Combines Finnhub company profile with basic market data.
    """
    ticker = state["ticker"]
    step_start = datetime.now()
    
    # Log workflow step start
    log_workflow_step("Company Profile", ticker, "STARTED")
    
    try:
        # Get company profile from Finnhub
        profile_data = _finnhub_request("stock/profile2", {"symbol": ticker})
        quote_data = _finnhub_request("quote", {"symbol": ticker})
        
        # Check if we got error responses
        if "error" in profile_data or "error" in quote_data:
            state["company_profile"] = {"error": "Company profile data not available", "timestamp": datetime.now().isoformat()}
            state["stage"] = "profile_failed"
            return state
        
        company_profile = {
            "ticker": ticker,
            "basic_info": {
                "name": _create_attributed_value(profile_data.get("name"), "finnhub"),
                "description": _create_attributed_value(profile_data.get("description", "")[:500], "finnhub"),
                "exchange": _create_attributed_value(profile_data.get("exchange"), "finnhub"),
                "country": _create_attributed_value(profile_data.get("country"), "finnhub"),
                "sector": _create_attributed_value(profile_data.get("finnhubIndustry"), "finnhub"),
                "website": _create_attributed_value(profile_data.get("weburl"), "finnhub"),
                "market_cap": _create_attributed_value(profile_data.get("marketCapitalization"), "finnhub"),
                "logo": _create_attributed_value(profile_data.get("logo"), "finnhub")
            },
            "current_trading": {
                "current_price": _create_attributed_value(quote_data.get("c"), "finnhub"),
                "change": _create_attributed_value(quote_data.get("d"), "finnhub"),
                "change_percent": _create_attributed_value(quote_data.get("dp"), "finnhub"),
                "previous_close": _create_attributed_value(quote_data.get("pc"), "finnhub"),
                "open": _create_attributed_value(quote_data.get("o"), "finnhub"),
                "high": _create_attributed_value(quote_data.get("h"), "finnhub"),
                "low": _create_attributed_value(quote_data.get("l"), "finnhub")
            },
            "timestamp": datetime.now().isoformat()
        }
    
        state["company_profile"] = company_profile
        state["stage"] = "profile_complete"
        state["workflow_metadata"]["steps_completed"] = state["workflow_metadata"].get("steps_completed", 0) + 1
        
        # Log successful completion with comprehensive data
        duration = (datetime.now() - step_start).total_seconds()
        log_workflow_step("Company Profile", ticker, "COMPLETED", duration, f"Market cap: {profile_data.get('marketCapitalization', 'N/A')}", step_data=state)
        
        return state
        
    except Exception as e:
        # Log failure
        duration = (datetime.now() - step_start).total_seconds()
        log_workflow_step("Company Profile", ticker, "FAILED", duration, str(e))
        
        # Return error state but don't break workflow
        state["company_profile"] = {"error": str(e), "timestamp": datetime.now().isoformat()}
        state["stage"] = "profile_failed"
        return state

async def analyze_recent_news(state: ResearchState) -> ResearchState:
    """
    Analyze recent company news for sentiment and key events.
    
    Fetches and analyzes news from past week for market sentiment.
    """
    ticker = state["ticker"]
    step_start = datetime.now()
    
    # Log workflow step start
    log_workflow_step("News Analysis", ticker, "STARTED")
    
    try:
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        to_date = datetime.now().strftime("%Y-%m-%d")
        
        # Get company news from Finnhub
        news_data = _finnhub_request("company-news", {
            "symbol": ticker,
            "from": from_date,
            "to": to_date
        })
        
        # Check if we got an error response
        if "error" in news_data:
            state["news_analysis"] = {"error": news_data["error"], "timestamp": datetime.now().isoformat()}
            state["stage"] = "news_failed"
            return state
        
        news_analysis = {
            "ticker": ticker,
            "analysis_period": {"from": from_date, "to": to_date},
            "news_summary": {
                "total_articles": len(news_data) if isinstance(news_data, list) else 0,
                "recent_headlines": [],
                "key_themes": [],
                "sentiment_indicators": []
            },
            "timestamp": datetime.now().isoformat()
        }
    
        if isinstance(news_data, list) and news_data:
            # Process top 10 most recent articles
            for article in news_data[:10]:
                headline_data = {
                    "headline": _create_attributed_value(article.get("headline", "")[:200], "finnhub"),
                    "datetime": _create_attributed_value(article.get("datetime"), "finnhub"),
                    "source": _create_attributed_value(article.get("source"), "finnhub"),
                    "url": _create_attributed_value(article.get("url"), "finnhub"),
                    "summary": _create_attributed_value(article.get("summary", "")[:300], "finnhub")
                }
                news_analysis["news_summary"]["recent_headlines"].append(headline_data)
            
            # Simple sentiment analysis based on headline keywords
            positive_keywords = ["growth", "profit", "revenue", "expansion", "success", "gain", "rise", "up", "positive", "beat", "exceed"]
            negative_keywords = ["loss", "decline", "fall", "drop", "concern", "risk", "down", "negative", "miss", "below"]
            
            positive_count = 0
            negative_count = 0
            
            for article in news_data[:20]:  # Analyze top 20 for sentiment
                headline = article.get("headline", "").lower()
                if any(word in headline for word in positive_keywords):
                    positive_count += 1
                if any(word in headline for word in negative_keywords):
                    negative_count += 1
            
            news_analysis["news_summary"]["sentiment_indicators"] = {
                "positive_articles": _create_attributed_value(positive_count, "algorithm", "medium"),
                "negative_articles": _create_attributed_value(negative_count, "algorithm", "medium"),
                "sentiment_ratio": _create_attributed_value(
                    positive_count / max(negative_count, 1) if negative_count > 0 else positive_count,
                    "algorithm", "medium"
                )
            }
        
        # Log sentiment calculation with comprehensive data
        total_articles = len(news_data) if isinstance(news_data, list) else 0
        if total_articles > 0:
            sentiment_ratio = news_analysis["news_summary"]["sentiment_indicators"].get("sentiment_ratio", {}).get("value", 0)
            algorithm_request = {"articles_analyzed": total_articles, "positive_keywords": positive_keywords[:5], "negative_keywords": negative_keywords[:5]}
            algorithm_response = {"sentiment_ratio": sentiment_ratio, "positive_count": positive_count, "negative_count": negative_count}
            log_data_request(DataSource.ALGORITHM, "sentiment_analysis", ticker, "SUCCESS", 
                           f"{total_articles} articles analyzed, sentiment ratio: {sentiment_ratio:.2f}",
                           request_data=algorithm_request, response_data=algorithm_response)
        
        state["news_analysis"] = news_analysis
        state["stage"] = "news_complete"
        state["workflow_metadata"]["steps_completed"] = state["workflow_metadata"].get("steps_completed", 0) + 1
        
        # Log successful completion with comprehensive data
        duration = (datetime.now() - step_start).total_seconds()
        log_workflow_step("News Analysis", ticker, "COMPLETED", duration, f"{total_articles} articles processed", step_data=state)
        
        return state
        
    except Exception as e:
        # Log failure
        duration = (datetime.now() - step_start).total_seconds()
        log_workflow_step("News Analysis", ticker, "FAILED", duration, str(e))
        
        # Return error state but don't break workflow
        state["news_analysis"] = {"error": str(e), "timestamp": datetime.now().isoformat()}
        state["stage"] = "news_failed"
        return state

async def fetch_sec_filings(state: ResearchState) -> ResearchState:
    """
    Fetch and analyze recent SEC filings.
    
    Gets recent 10-K, 10-Q, 8-K filings for regulatory insights.
    """
    ticker = state["ticker"]
    step_start = datetime.now()
    
    # Log workflow step start
    log_workflow_step("SEC Filings", ticker, "STARTED")
    
    try:
        if not SEC_EDGAR_AVAILABLE:
            # Log SEC Edgar unavailable
            log_data_request(DataSource.UNAVAILABLE, "recent_filings", ticker, "FAILED", "SEC Edgar not configured")
            
            # Return error when SEC data not available
            sec_analysis = {
                "ticker": ticker,
                "error": "SEC Edgar data not available - configuration required",
                "timestamp": datetime.now().isoformat()
            }
        else:
            try:
                # Get recent filings using SEC Edgar MCP
                recent_filings = sec_filings_tools.get_recent_filings(
                    identifier=ticker,
                    form_type=["10-K", "10-Q", "8-K"],
                    days=90,
                    limit=10
                )
                
                # Get company info for additional context
                company_info = sec_company_tools.get_company_info(ticker)
                
                sec_analysis = {
                    "ticker": ticker,
                    "company_info": {
                        "cik": _create_attributed_value(company_info.get("cik"), "sec_edgar"),
                        "name": _create_attributed_value(company_info.get("name"), "sec_edgar"),
                        "sic": _create_attributed_value(company_info.get("sic"), "sec_edgar"),
                        "sic_description": _create_attributed_value(company_info.get("sic_description"), "sec_edgar")
                    },
                    "recent_filings": {
                        "total_filings": len(recent_filings.get("filings", [])),
                        "filing_summary": [],
                        "key_forms": {"10-K": 0, "10-Q": 0, "8-K": 0}
                    },
                    "timestamp": datetime.now().isoformat()
                }
            
                # Process recent filings
                if recent_filings.get("filings"):
                    for filing in recent_filings["filings"][:5]:  # Top 5 most recent
                        filing_data = {
                            "form_type": _create_attributed_value(filing.get("form_type"), "sec_edgar"),
                            "filing_date": _create_attributed_value(filing.get("filing_date"), "sec_edgar"),
                            "accession_number": _create_attributed_value(filing.get("accession_number"), "sec_edgar"),
                            "period_of_report": _create_attributed_value(filing.get("period_of_report"), "sec_edgar")
                        }
                        sec_analysis["recent_filings"]["filing_summary"].append(filing_data)
                        
                        # Count form types
                        form_type = filing.get("form_type", "")
                        if form_type in sec_analysis["recent_filings"]["key_forms"]:
                            sec_analysis["recent_filings"]["key_forms"][form_type] += 1
        
            except Exception as e:
                log_data_request(DataSource.SEC_EDGAR_LIVE, "recent_filings", ticker, "FAILED", str(e))
                sec_analysis = {
                    "ticker": ticker,
                    "error": f"SEC filing analysis failed: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
    
        state["sec_filings"] = sec_analysis
        state["stage"] = "sec_complete" 
        state["workflow_metadata"]["steps_completed"] = state["workflow_metadata"].get("steps_completed", 0) + 1
        
        # Log successful completion with comprehensive data
        duration = (datetime.now() - step_start).total_seconds()
        filing_count = sec_analysis.get("recent_filings", {}).get("total_filings", 0)
        log_workflow_step("SEC Filings", ticker, "COMPLETED", duration, f"{filing_count} filings analyzed", step_data=state)
        
        return state
        
    except Exception as e:
        # Log failure
        duration = (datetime.now() - step_start).total_seconds()
        log_workflow_step("SEC Filings", ticker, "FAILED", duration, str(e))
        
        # Return error state but don't break workflow
        state["sec_filings"] = {"error": str(e), "timestamp": datetime.now().isoformat()}
        state["stage"] = "sec_failed"
        return state

async def gather_analyst_data(state: ResearchState) -> ResearchState:
    """
    Gather analyst recommendations and earnings data.
    
    Combines analyst recommendations with earnings estimates and surprises.
    """
    ticker = state["ticker"]
    
    # Get analyst recommendations
    recommendations = _finnhub_request("stock/recommendation", {"symbol": ticker})
    
    # Get earnings data
    earnings_data = _finnhub_request("stock/earnings", {"symbol": ticker})
    
    # Check if we got error responses
    if "error" in recommendations and "error" in earnings_data:
        state["analyst_data"] = {"error": "Analyst data not available", "timestamp": datetime.now().isoformat()}
        state["stage"] = "analyst_failed"
        return state
    
    analyst_analysis = {
        "ticker": ticker,
        "recommendations": {
            "current_summary": {},
            "trend_data": []
        },
        "earnings": {
            "recent_quarters": [],
            "surprise_analysis": {}
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # Process recommendation data
    if isinstance(recommendations, list) and recommendations and "error" not in recommendations:
        latest_rec = recommendations[0]
        total_analysts = sum([
            latest_rec.get("strongBuy", 0),
            latest_rec.get("buy", 0),
            latest_rec.get("hold", 0),
            latest_rec.get("sell", 0),
            latest_rec.get("strongSell", 0)
        ])
        
        analyst_analysis["recommendations"]["current_summary"] = {
            "strong_buy": _create_attributed_value(latest_rec.get("strongBuy", 0), "finnhub"),
            "buy": _create_attributed_value(latest_rec.get("buy", 0), "finnhub"),
            "hold": _create_attributed_value(latest_rec.get("hold", 0), "finnhub"),
            "sell": _create_attributed_value(latest_rec.get("sell", 0), "finnhub"),
            "strong_sell": _create_attributed_value(latest_rec.get("strongSell", 0), "finnhub"),
            "total_analysts": _create_attributed_value(total_analysts, "finnhub"),
            "period": _create_attributed_value(latest_rec.get("period"), "finnhub")
        }
        
        # Get trend data (last 4 periods)
        for rec in recommendations[:4]:
            trend_data = {
                "period": _create_attributed_value(rec.get("period"), "finnhub"),
                "strong_buy": _create_attributed_value(rec.get("strongBuy", 0), "finnhub"),
                "buy": _create_attributed_value(rec.get("buy", 0), "finnhub"),
                "hold": _create_attributed_value(rec.get("hold", 0), "finnhub"),
                "sell": _create_attributed_value(rec.get("sell", 0), "finnhub"),
                "strong_sell": _create_attributed_value(rec.get("strongSell", 0), "finnhub")
            }
            analyst_analysis["recommendations"]["trend_data"].append(trend_data)
    
    # Process earnings data
    if isinstance(earnings_data, list) and earnings_data and "error" not in earnings_data:
        surprise_sum = 0
        surprise_count = 0
        
        for earnings in earnings_data[-4:]:  # Last 4 quarters
            earnings_info = {
                "period": _create_attributed_value(earnings.get("period"), "finnhub"),
                "actual": _create_attributed_value(earnings.get("actual"), "finnhub"),
                "estimate": _create_attributed_value(earnings.get("estimate"), "finnhub"),
                "surprise": _create_attributed_value(earnings.get("surprise"), "finnhub"),
                "surprise_percent": _create_attributed_value(earnings.get("surprisePercent"), "finnhub")
            }
            analyst_analysis["earnings"]["recent_quarters"].append(earnings_info)
            
            # Calculate average surprise
            if earnings.get("surprise") is not None:
                surprise_sum += earnings.get("surprise")
                surprise_count += 1
        
        if surprise_count > 0:
            analyst_analysis["earnings"]["surprise_analysis"] = {
                "average_surprise": _create_attributed_value(surprise_sum / surprise_count, "algorithm", "medium"),
                "quarters_analyzed": _create_attributed_value(surprise_count, "algorithm", "high"),
                "consistent_beats": _create_attributed_value(
                    sum(1 for e in earnings_data[-4:] if e.get("surprise", 0) > 0),
                    "algorithm", "medium"
                )
            }
    
    step_start = datetime.now()
    
    # Log workflow step start
    log_workflow_step("Analyst Data", ticker, "STARTED")
    
    try:
        state["analyst_data"] = analyst_analysis
        state["stage"] = "analyst_complete"
        state["workflow_metadata"]["steps_completed"] = state["workflow_metadata"].get("steps_completed", 0) + 1
        
        # Log successful completion with comprehensive data
        duration = (datetime.now() - step_start).total_seconds()
        total_analysts = analyst_analysis.get("recommendations", {}).get("current_summary", {}).get("total_analysts", {}).get("value", 0)
        log_workflow_step("Analyst Data", ticker, "COMPLETED", duration, f"{total_analysts} analysts tracked", step_data=state)
        
        return state
    
    except Exception as e:
        # Log failure
        duration = (datetime.now() - step_start).total_seconds()
        log_workflow_step("Analyst Data", ticker, "FAILED", duration, str(e))
        
        # Return error state but don't break workflow
        state["analyst_data"] = {"error": str(e), "timestamp": datetime.now().isoformat()}
        state["stage"] = "analyst_failed"
        return state

async def synthesize_research(state: ResearchState) -> ResearchState:
    """
    Synthesize all research data into comprehensive summary.
    
    Creates investment thesis based on all collected data points.
    """
    ticker = state["ticker"]
    
    # Gather all analysis components
    profile = state.get("company_profile", {})
    news = state.get("news_analysis", {})
    sec = state.get("sec_filings", {})
    analyst = state.get("analyst_data", {})
    
    # Create comprehensive research summary
    research_summary = {
        "ticker": ticker,
        "analysis_timestamp": datetime.now().isoformat(),
        "executive_summary": {
            "company_overview": "",
            "current_sentiment": "",
            "regulatory_status": "",
            "analyst_consensus": "",
            "key_risks": [],
            "investment_highlights": []
        },
        "quantitative_metrics": {
            "valuation": {},
            "sentiment_score": None,
            "analyst_score": None,
            "filing_activity": None
        },
        "data_quality": {
            "sources_used": [],
            "completeness_score": 0,
            "last_updated": datetime.now().isoformat()
        },
        "workflow_metadata": state["workflow_metadata"]
    }
    
    # Extract company overview
    if profile.get("basic_info") and not profile.get("error"):
        basic_info = profile["basic_info"]
        name = basic_info.get("name", {}).get("value")
        sector = basic_info.get("sector", {}).get("value")
        market_cap = basic_info.get("market_cap", {}).get("value")
        
        if name:
            research_summary["executive_summary"]["company_overview"] = (
                f"{name} is a {sector or 'Unknown'} company" +
                (f" with a market cap of ${market_cap/1000:.1f}B" if market_cap and isinstance(market_cap, (int, float)) and market_cap > 1000000000 else "")
            )
            research_summary["data_quality"]["sources_used"].append("company_profile")
            research_summary["data_quality"]["completeness_score"] += 25
        else:
            research_summary["executive_summary"]["company_overview"] = "Company profile data not available"
    elif profile.get("error"):
        research_summary["executive_summary"]["company_overview"] = "Company profile data not available"
    
    # Extract sentiment analysis
    if news.get("news_summary") and not news.get("error"):
        sentiment = news["news_summary"].get("sentiment_indicators", {})
        positive = sentiment.get("positive_articles", {}).get("value", 0)
        negative = sentiment.get("negative_articles", {}).get("value", 0)
        
        if positive + negative > 0:
            sentiment_ratio = positive / max(positive + negative, 1)
            research_summary["quantitative_metrics"]["sentiment_score"] = sentiment_ratio
            
            if sentiment_ratio > 0.6:
                research_summary["executive_summary"]["current_sentiment"] = "Positive news sentiment"
            elif sentiment_ratio < 0.4:
                research_summary["executive_summary"]["current_sentiment"] = "Negative news sentiment"
            else:
                research_summary["executive_summary"]["current_sentiment"] = "Neutral news sentiment"
            
            research_summary["data_quality"]["sources_used"].append("news_analysis")
            research_summary["data_quality"]["completeness_score"] += 25
    elif news.get("error"):
        research_summary["executive_summary"]["current_sentiment"] = "News sentiment data not available"
    
    # Extract SEC filing insights
    if sec.get("recent_filings") and not sec.get("error"):
        filing_count = sec["recent_filings"].get("total_filings", 0)
        research_summary["quantitative_metrics"]["filing_activity"] = filing_count
        
        if filing_count > 0:
            research_summary["executive_summary"]["regulatory_status"] = f"Recent filing activity: {filing_count} filings in last 90 days"
        
        research_summary["data_quality"]["sources_used"].append("sec_filings")
        research_summary["data_quality"]["completeness_score"] += 25
    elif sec.get("error"):
        research_summary["executive_summary"]["regulatory_status"] = "SEC filing data not available"
    
    # Extract analyst consensus
    if analyst.get("recommendations", {}).get("current_summary") and not analyst.get("error"):
        rec_summary = analyst["recommendations"]["current_summary"]
        total = rec_summary.get("total_analysts", {}).get("value", 0)
        
        if total > 0:
            buy_rating = (
                rec_summary.get("strong_buy", {}).get("value", 0) + 
                rec_summary.get("buy", {}).get("value", 0)
            ) / total
            
            research_summary["quantitative_metrics"]["analyst_score"] = buy_rating
            
            if buy_rating > 0.6:
                research_summary["executive_summary"]["analyst_consensus"] = f"Positive analyst sentiment ({total} analysts)"
            elif buy_rating < 0.4:
                research_summary["executive_summary"]["analyst_consensus"] = f"Negative analyst sentiment ({total} analysts)"
            else:
                research_summary["executive_summary"]["analyst_consensus"] = f"Mixed analyst sentiment ({total} analysts)"
            
            research_summary["data_quality"]["sources_used"].append("analyst_data")
            research_summary["data_quality"]["completeness_score"] += 25
    elif analyst.get("error"):
        research_summary["executive_summary"]["analyst_consensus"] = "Analyst data not available"
    
    # Add investment highlights and risks based on data
    if research_summary["quantitative_metrics"]["sentiment_score"] and research_summary["quantitative_metrics"]["sentiment_score"] > 0.6:
        research_summary["executive_summary"]["investment_highlights"].append("Positive recent news sentiment")
    
    if research_summary["quantitative_metrics"]["analyst_score"] and research_summary["quantitative_metrics"]["analyst_score"] > 0.6:
        research_summary["executive_summary"]["investment_highlights"].append("Strong analyst support")
    
    if research_summary["quantitative_metrics"]["filing_activity"] and research_summary["quantitative_metrics"]["filing_activity"] > 5:
        research_summary["executive_summary"]["key_risks"].append("High regulatory filing activity may indicate volatility")
    
    step_start = datetime.now()
    
    # Log workflow step start
    log_workflow_step("Research Synthesis", ticker, "STARTED")
    
    try:
        state["research_summary"] = research_summary
        state["stage"] = "complete"
        state["workflow_metadata"]["steps_completed"] = state["workflow_metadata"].get("steps_completed", 0) + 1
        state["workflow_metadata"]["end_time"] = datetime.now().isoformat()
        
        # Log successful completion with comprehensive data
        duration = (datetime.now() - step_start).total_seconds()
        completeness = research_summary.get("data_quality", {}).get("completeness_score", 0)
        log_workflow_step("Research Synthesis", ticker, "COMPLETED", duration, f"{completeness}% data completeness", step_data=state)
        
        return state
        
    except Exception as e:
        # Log failure
        duration = (datetime.now() - step_start).total_seconds()
        log_workflow_step("Research Synthesis", ticker, "FAILED", duration, str(e))
        
        # Return error state
        state["research_summary"] = {"error": str(e), "timestamp": datetime.now().isoformat()}
        state["stage"] = "synthesis_failed"
        return state

# Build LangGraph Workflow
def create_research_workflow() -> StateGraph:
    """
    Create the LangGraph workflow for comprehensive company research.
    
    Returns:
        StateGraph: Configured workflow graph
    """
    workflow = StateGraph(ResearchState)
    
    # Add nodes
    workflow.add_node("company_profile", fetch_company_profile)
    workflow.add_node("news_analysis", analyze_recent_news)
    workflow.add_node("sec_filings", fetch_sec_filings)
    workflow.add_node("analyst_data", gather_analyst_data)
    workflow.add_node("synthesis", synthesize_research)
    
    # Add edges
    workflow.add_edge(START, "company_profile")
    workflow.add_edge("company_profile", "news_analysis")
    workflow.add_edge("news_analysis", "sec_filings")
    workflow.add_edge("sec_filings", "analyst_data")
    workflow.add_edge("analyst_data", "synthesis")
    workflow.add_edge("synthesis", END)
    
    return workflow

# Initialize workflow
memory = MemorySaver()
research_workflow = create_research_workflow()
app = research_workflow.compile(checkpointer=memory)

@mcp.tool
async def company_deep_research(ticker: str, include_sec_filings: bool = True) -> Dict[str, Any]:
    """
    Perform comprehensive multi-step company research using LangGraph orchestration.
    
    This tool executes a complex workflow that:
    1. Fetches company profile and current market data
    2. Analyzes recent news sentiment
    3. Reviews SEC filings and regulatory activity  
    4. Gathers analyst recommendations and earnings data
    5. Synthesizes all data into investment thesis
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        include_sec_filings: Whether to include SEC filing analysis (default: True)
    
    Returns:
        Dictionary containing comprehensive research analysis with workflow metadata
    """
    ticker = ticker.upper()
    
    # Initialize workflow state
    initial_state = {
        "ticker": ticker,
        "stage": "initialized",
        "company_profile": None,
        "market_data": None,
        "news_analysis": None,
        "sec_filings": None,
        "analyst_data": None,
        "research_summary": None,
        "workflow_metadata": {
            "start_time": datetime.now().isoformat(),
            "workflow_version": "1.0",
            "include_sec_filings": include_sec_filings,
            "steps_completed": 0,
            "total_steps": 5
        }
    }
    
    try:
        # Create unique thread ID for this research session
        thread_id = f"research_{ticker}_{int(datetime.now().timestamp())}"
        config = {"configurable": {"thread_id": thread_id}}
        
        # Execute the workflow
        final_state = await app.ainvoke(initial_state, config=config)
        
        return {
            "success": True,
            "ticker": ticker,
            "research_data": final_state,
            "workflow_info": {
                "thread_id": thread_id,
                "execution_time": final_state["workflow_metadata"].get("end_time"),
                "steps_completed": final_state["workflow_metadata"].get("steps_completed"),
                "final_stage": final_state.get("stage")
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Workflow execution failed: {str(e)}",
            "ticker": ticker,
            "partial_data": initial_state
        }

@mcp.tool
def quick_company_overview(ticker: str) -> Dict[str, Any]:
    """
    Get quick company overview without full workflow (for simple queries).
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
    
    Returns:
        Dictionary containing basic company information and current market data
    """
    ticker = ticker.upper()
    
    # Get basic company data
    profile_data = _finnhub_request("stock/profile2", {"symbol": ticker})
    quote_data = _finnhub_request("quote", {"symbol": ticker})
    
    if "error" in profile_data:
        return {"error": f"Company data not available for {ticker}", "ticker": ticker}
    
    return {
        "ticker": ticker,
        "name": profile_data.get("name", "Unknown"),
        "sector": profile_data.get("finnhubIndustry", "Unknown"),
        "market_cap_millions": profile_data.get("marketCapitalization"),
        "current_price": quote_data.get("c"),
        "change_percent": quote_data.get("dp"),
        "exchange": profile_data.get("exchange"),
        "country": profile_data.get("country"),
        "website": profile_data.get("weburl"),
        "last_updated": datetime.now().isoformat()
    }

@mcp.tool
def workflow_status(ticker: str, thread_id: str) -> Dict[str, Any]:
    """
    Check the status of a running or completed research workflow.
    
    Args:
        ticker: Stock ticker symbol
        thread_id: Workflow thread ID from company_deep_research response
    
    Returns:
        Dictionary containing workflow status and progress information
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}
        
        # Try to get the current state
        current_state = app.get_state(config)
        
        if current_state and current_state.values:
            state_data = current_state.values
            return {
                "ticker": ticker,
                "thread_id": thread_id,
                "current_stage": state_data.get("stage", "unknown"),
                "steps_completed": state_data.get("workflow_metadata", {}).get("steps_completed", 0),
                "total_steps": state_data.get("workflow_metadata", {}).get("total_steps", 5),
                "start_time": state_data.get("workflow_metadata", {}).get("start_time"),
                "status": "completed" if state_data.get("stage") == "complete" else "in_progress"
            }
        else:
            return {
                "ticker": ticker,
                "thread_id": thread_id, 
                "status": "not_found",
                "error": "Workflow thread not found or expired"
            }
            
    except Exception as e:
        return {
            "ticker": ticker,
            "thread_id": thread_id,
            "status": "error",
            "error": f"Failed to check workflow status: {str(e)}"
        }

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()