"""
Main Orchestrator for AgentX Financial Research Platform

Creates a DeepAgent orchestrator that coordinates multiple specialized subagents
for comprehensive financial research.
"""

import os
from typing import Optional
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

from subagents import (
    create_research_subagent,
    create_daloopa_subagent,
    create_sec_subagent,
    create_obsidian_subagent,
    create_transcript_subagent,
)


def create_orchestrator(
    model: str = "openai:gpt-4o",
    temperature: float = 0.7,
    max_tokens: int = 8192,
    api_key: Optional[str] = None,
):
    """
    Create the main orchestrator DeepAgent with all specialized subagents.

    The orchestrator coordinates 5 specialized subagents:
    1. Deep Research - Comprehensive web research (FULLY FUNCTIONAL)
    2. Daloopa - Premium financial data (FULLY FUNCTIONAL with MCP)
    3. SEC - SEC Edgar filings (FULLY FUNCTIONAL with MCP)
    4. Obsidian - Personal notes and research (FULLY FUNCTIONAL with MCP)
    5. Transcript - Earnings call transcripts (FULLY FUNCTIONAL with MCP)

    The orchestrator's role is decision-making and coordination:
    - Analyzes user's financial research query
    - Determines which data sources are needed
    - Delegates to appropriate subagents (can call multiple in parallel)
    - Synthesizes results into comprehensive answer
    - Uses TODO planner for complex multi-step research

    Args:
        model: LLM model to use (default: gpt-4o)
        temperature: Model temperature for creativity (default: 0.7)
        max_tokens: Maximum tokens for responses (default: 8192)
        api_key: OpenAI API key (optional, uses env var if not provided)

    Returns:
        Compiled DeepAgent orchestrator ready for queries

    Example:
        >>> orchestrator = create_orchestrator()
        >>> result = orchestrator.invoke({
        ...     "messages": [{"role": "user", "content": "Research Apple's Q4 earnings"}]
        ... })
    """
    # Initialize the LLM model for orchestrator
    orchestrator_model = init_chat_model(
        model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
    )

    # Create tools dictionary for subagents to populate
    tools_dict = {}

    # Create all subagent configurations
    # All MCP-based agents populate tools_dict with their respective tools
    subagents = [
        create_research_subagent(),                  # Full implementation (web research)
        create_daloopa_subagent(tools_dict),         # Full implementation with MCP
        create_sec_subagent(tools_dict),             # Full implementation with MCP
        create_obsidian_subagent(tools_dict),        # Full implementation with MCP
        create_transcript_subagent(tools_dict),      # Full implementation with MCP
    ]

    # Convert tools dict to list for create_deep_agent
    tools = list(tools_dict.values())

    # Orchestrator instructions - defines coordination strategy
    orchestrator_instructions = """You are a sophisticated financial research orchestrator for hedge fund analysts.

Your role is to coordinate specialized research agents to provide comprehensive, grounded financial intelligence.

## Available Research Agents

1. **deep-research** (FULLY FUNCTIONAL)
   - Comprehensive web research on any topic
   - Multi-source information gathering
   - Up-to-date market information
   - Company news and analysis
   USE FOR: General research, company info, market trends, news analysis

2. **daloopa-agent** (FULLY FUNCTIONAL)
   - Premium financial metrics and data from Daloopa API
   - Company fundamentals (revenue, EBITDA, margins, cash flow)
   - Historical financial data with high accuracy
   - Analyst estimates and consensus data
   - Industry-specific KPIs and metrics
   USE FOR: Detailed financials, premium data, analyst estimates
   STATUS: MCP tools available (requires DALOOPA_API_KEY)

3. **sec-agent** (FULLY FUNCTIONAL)
   - SEC Edgar filings (10-K, 10-Q, 8-K, proxy statements, Form 4)
   - Official financial statements from filings
   - Regulatory disclosures and risk factors
   - Insider transactions and ownership data
   - XBRL data extraction for precise metrics
   - Full text search across filings
   USE FOR: Official SEC data, financial statements, insider activity, regulatory information
   STATUS: 21 tools available for comprehensive SEC analysis

4. **obsidian-agent** (FULLY FUNCTIONAL)
   - User's personal Obsidian vault notes
   - Meeting summaries and research notes
   - Newsletter archives and highlights
   - Transcript annotations
   - Tagged notes and backlinks
   USE FOR: Personal insights, past research, meeting notes, investment theses
   STATUS: MCP tools available (requires OBSIDIAN_CONFIG_PATH)

5. **transcript-agent** (FULLY FUNCTIONAL)
   - Earnings call transcripts search via SuperSearch
   - Management commentary and prepared remarks
   - Analyst Q&A sections
   - Forward guidance and outlook statements
   - Quarter-over-quarter comparisons
   USE FOR: Management quotes, earnings discussions, sentiment analysis
   STATUS: MCP tools available (requires TRANSCRIPT_DIR)

## Research Strategy

1. **Analyze the Query**: Understand what information the user needs
2. **Plan Your Approach**: Determine which agents to call (can use multiple in parallel)
3. **Delegate Work**: Call appropriate subagents with specific instructions
4. **Synthesize Results**: Combine findings into a comprehensive answer
5. **Cite Sources**: Always reference which agents provided which information

## Best Practices

- **Use TODO planner** for complex multi-step research
- **Call multiple agents in parallel** when they provide complementary data
- **Be specific** in subagent instructions - tell them exactly what to find
- **Synthesize, don't just concatenate** - provide integrated analysis
- **Layer data sources** - combine official data (SEC), premium data (Daloopa), and context (transcripts, notes)
- **Cross-reference findings** - verify claims across multiple sources

## Example Workflows

**Simple Query**: "What's Apple's latest news?"
→ Call deep-research only

**Complex Query**: "Analyze Apple's Q4 performance"
→ Call deep-research (news, market sentiment)
→ Call sec-agent (10-Q filing, official financials)
→ Call daloopa-agent (detailed metrics, analyst estimates)
→ Call transcript-agent (earnings call commentary)
→ Synthesize all sources into comprehensive analysis

**Financial Metrics Query**: "What were Apple's revenues last quarter?"
→ Call sec-agent (official SEC data)
→ Call daloopa-agent (structured financial data)
→ Compare and present with proper citations

**Insider Activity Query**: "Show me recent insider transactions for Tesla"
→ Call sec-agent (Form 4 filings, insider transaction tools)

**Management Commentary**: "What did Tim Cook say about iPhone sales?"
→ Call transcript-agent (search recent earnings calls)
→ Call obsidian-agent (check user's meeting notes if applicable)

**Personal Context Query**: "What are my notes on Tesla's AI strategy?"
→ Call obsidian-agent (search vault for Tesla + AI tags/keywords)
→ Optionally call deep-research for latest updates

**Multi-Source Query**: "Compare NVDA and AMD market positions with management perspective"
→ Call deep-research (market trends, news)
→ Call sec-agent (official financials, risk factors)
→ Call daloopa-agent (detailed metrics comparison)
→ Call transcript-agent (management commentary from both companies)
→ Call obsidian-agent (user's past research or thesis)
→ Synthesize comprehensive comparison

Remember: You are the coordinator, not the researcher. Delegate ALL actual research work to subagents.
"""

    # Create the orchestrator DeepAgent
    # Note: LangGraph API handles checkpointing automatically, no need to pass checkpointer
    # Tools list includes all MCP tools for subagents to use
    orchestrator = create_deep_agent(
        tools=tools,  # MCP tools from subagents
        instructions=orchestrator_instructions,
        model=orchestrator_model,
        subagents=subagents,
    )

    return orchestrator


# Create the graph instance for LangGraph deployment
# This is the entry point for `langgraph dev`
graph = create_orchestrator(
    api_key=os.getenv("OPENAI_API_KEY"),
)
