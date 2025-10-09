#!/usr/bin/env python
"""
Test script to analyze agent delegation behavior.

This script runs the same query with both Claude and GPT-4o models
and logs the execution to help identify delegation differences.
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Set up logging to both file and console
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f'delegation_test_{timestamp}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TEST_QUERY = "Get market data for Tesla (TSLA) for the last month"

async def test_agent_with_model(model_name, agent):
    """Test the agent with a specific model and log the execution."""
    logger.info("=" * 80)
    logger.info(f"DELEGATION TEST - {model_name}")
    logger.info("=" * 80)
    logger.info(f"Test Query: {TEST_QUERY}")
    logger.info("")

    logger.info("Invoking agent...")
    result = agent.invoke({
        "messages": [
            {"role": "user", "content": TEST_QUERY}
        ]
    })

    logger.info("")
    logger.info("=" * 80)
    logger.info(f"RESULT - {model_name}")
    logger.info("=" * 80)

    # Print messages
    for i, msg in enumerate(result.get("messages", [])):
        logger.info(f"Message {i+1} ({msg.type if hasattr(msg, 'type') else 'unknown'}):")
        content = msg.content if hasattr(msg, 'content') else str(msg)
        logger.info(f"  Content type: {type(content)}")
        logger.info(f"  Content: {content if content else '(empty)'}...")

        # Log additional_kwargs to see tool_calls
        if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
            logger.info(f"  Additional kwargs keys: {list(msg.additional_kwargs.keys())}")
        logger.info("")

    # Look for tool calls vs subagent calls
    tool_calls = []
    subagent_calls = []
    import json

    for i, msg in enumerate(result.get("messages", [])):
        # Log full tool call structure for analysis
        if hasattr(msg, 'additional_kwargs'):
            tool_calls_in_msg = msg.additional_kwargs.get('tool_calls', [])
            if tool_calls_in_msg:
                logger.info(f"\n📋 Message {i+1} TOOL CALLS (full structure):")
                logger.info(json.dumps(tool_calls_in_msg, indent=2, default=str))
                for tc in tool_calls_in_msg:
                    tool_name = tc.get('function', {}).get('name', 'unknown')
                    tool_calls.append(tool_name)
                    logger.info(f"🔧 TOOL CALL DETECTED: {tool_name}")

                    # Check if this is a task tool call with subagent_type
                    if tool_name == 'task':
                        args = tc.get('function', {}).get('arguments', '{}')
                        if isinstance(args, str):
                            try:
                                args_dict = json.loads(args)
                            except:
                                args_dict = {}
                        else:
                            args_dict = args
                        logger.info(f"   Task args: {json.dumps(args_dict, indent=4)}")
                        if 'subagent_type' in args_dict:
                            logger.info(f"   ✅ Has subagent_type: {args_dict['subagent_type']}")
                        else:
                            logger.info(f"   ❌ Missing subagent_type field!")

        # Check for subagent invocations (these would appear as specific tool names)
        if hasattr(msg, 'name') and msg.name:
            if 'task' in msg.name.lower():  # DeepAgents uses 'task' for subagent calls
                subagent_calls.append(msg.name)
                logger.info(f"🤖 SUBAGENT CALL DETECTED: {msg.name}")

    logger.info("")
    logger.info("=" * 80)
    logger.info(f"ANALYSIS SUMMARY - {model_name}")
    logger.info("=" * 80)
    logger.info(f"Total tool calls: {len(tool_calls)}")
    logger.info(f"Total subagent calls: {len(subagent_calls)}")

    if tool_calls:
        logger.info("\nDirect tool calls:")
        for tc in tool_calls:
            logger.info(f"  - {tc}")

    if subagent_calls:
        logger.info("\nSubagent delegations:")
        for sa in subagent_calls:
            logger.info(f"  - {sa}")

    if tool_calls and not subagent_calls:
        logger.warning(f"⚠️  PROBLEM ({model_name}): Agent called tools directly without delegating to subagents!")
        return "DIRECT_TOOL_USE"
    elif subagent_calls:
        logger.info(f"✅ SUCCESS ({model_name}): Agent properly delegated to subagents!")
        return "DELEGATED"
    else:
        logger.warning(f"❓ UNCLEAR ({model_name}): No tool calls or subagent calls detected")
        return "UNCLEAR"


async def run_comparison_test():
    """Run tests with both Claude and GPT-4o for comparison."""
    logger.info("=" * 100)
    logger.info("AGENT DELEGATION COMPARISON TEST")
    logger.info("=" * 100)
    logger.info(f"Test Query: {TEST_QUERY}")
    logger.info(f"Log File: {log_filename}")
    logger.info("=" * 100)
    logger.info("")

    # Import shared config and tools (avoid importing the module-level agent)
    from langchain_anthropic import ChatAnthropic
    from langchain_openai import ChatOpenAI
    from deepagents import async_create_deep_agent

    # Define placeholder tools
    def placeholder_market_data(ticker: str, period: str = "1mo") -> dict:
        """Get market data for a ticker (placeholder)."""
        return {"ticker": ticker, "period": period, "status": "placeholder"}

    def placeholder_news_search(query: str, max_results: int = 5) -> dict:
        """Search for financial news (placeholder)."""
        return {"query": query, "max_results": max_results, "status": "placeholder"}

    # Define subagent configs
    market_data_analyst = {
        "name": "market-data-analyst",
        "description": "Analyzes market data, stock prices, and trading metrics.",
        "prompt": """You are a market data analyst specialist.""",
        "tools": ["placeholder_market_data"],
    }

    news_researcher = {
        "name": "news-researcher",
        "description": "Researches financial news and current events.",
        "prompt": """You are a financial news researcher.""",
        "tools": ["placeholder_news_search"],
    }

    report_writer = {
        "name": "report-writer",
        "description": "Synthesizes research into comprehensive reports.",
        "prompt": """You are a professional financial report writer.""",
    }

    quality_validator = {
        "name": "quality-validator",
        "description": "Validates and critiques reports for accuracy and completeness.",
        "prompt": """You are a quality control specialist for financial research.""",
    }

    main_agent_instructions = """You are a financial research orchestrator.
Your job is to coordinate specialized subagents to conduct comprehensive financial research.

IMPORTANT: You must ALWAYS delegate tasks to the appropriate subagent. NEVER call tools directly.

Available subagents:
- market-data-analyst: For market data, stock prices, trading metrics
- news-researcher: For financial news and current events
- report-writer: For synthesizing information into reports
- quality-validator: For validating report quality

Always use the task tool to delegate to these subagents."""

    results = {}

    # Test 1: Claude Sonnet 4 (Expected to work)
    logger.info("\n" + "=" * 100)
    logger.info("TEST 1: CLAUDE SONNET 4")
    logger.info("=" * 100)

    try:
        logger.info("Creating Claude agent...")

        claude_agent = async_create_deep_agent(
            tools=[placeholder_market_data, placeholder_news_search],
            instructions=main_agent_instructions,
            model=ChatAnthropic(
                model="claude-sonnet-4-20250514",
                temperature=0.3,
                max_tokens=64000,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            ),
            subagents=[
                market_data_analyst,
                news_researcher,
                report_writer,
                quality_validator,
            ],
        )

        results["Claude"] = await test_agent_with_model("Claude Sonnet 4", claude_agent)

    except Exception as e:
        logger.error(f"❌ Claude test failed: {e}")
        logger.exception("Full traceback:")
        results["Claude"] = "ERROR"

    # Test 2: GPT-4o (Expected to fail)
    logger.info("\n" + "=" * 100)
    logger.info("TEST 2: GPT-4o")
    logger.info("=" * 100)

    try:
        logger.info("Creating GPT-4o agent...")

        gpt_agent = async_create_deep_agent(
            tools=[placeholder_market_data, placeholder_news_search],
            instructions=main_agent_instructions,
            model=ChatOpenAI(
                model="gpt-4o",
                temperature=0.3,
                max_tokens=16000,
                api_key=os.getenv("OPENAI_API_KEY"),
            ),
            subagents=[
                market_data_analyst,
                news_researcher,
                report_writer,
                quality_validator,
            ],
        )

        results["GPT-4o"] = await test_agent_with_model("GPT-4o", gpt_agent)

    except Exception as e:
        logger.error(f"❌ GPT-4o test failed: {e}")
        logger.exception("Full traceback:")
        results["GPT-4o"] = "ERROR"

    # Final comparison
    logger.info("\n\n" + "=" * 100)
    logger.info("FINAL COMPARISON")
    logger.info("=" * 100)
    logger.info(f"Claude Sonnet 4: {results.get('Claude', 'NOT TESTED')}")
    logger.info(f"GPT-4o:          {results.get('GPT-4o', 'NOT TESTED')}")
    logger.info("")

    if results.get("Claude") == "DELEGATED" and results.get("GPT-4o") == "DIRECT_TOOL_USE":
        logger.warning("⚠️  CONFIRMED: Claude delegates properly, GPT-4o calls tools directly")
        logger.warning("    This is the delegation bug we're investigating!")
    elif results.get("Claude") == results.get("GPT-4o"):
        logger.info("✅ Both models behave the same way")

    logger.info("=" * 100)
    logger.info(f"Full logs saved to: {log_filename}")
    logger.info("=" * 100)


if __name__ == "__main__":
    asyncio.run(run_comparison_test())
