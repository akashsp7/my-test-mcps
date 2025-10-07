"""
Deep Research Agent Integration

Integrates the open_deep_research LangGraph graph as a DeepAgents subagent.
This agent conducts comprehensive web research on any topic using the full
Deep Research implementation.
"""

from typing import Dict, Any


def create_research_subagent() -> Dict[str, Any]:
    """
    Create the Deep Research subagent configuration.

    This function imports the compiled deep_researcher graph from open_deep_research
    and configures it as a custom LangGraph subagent for the orchestrator.

    The Deep Research agent:
    - Clarifies ambiguous research queries with users
    - Breaks down research into focused topics
    - Delegates to parallel researcher subagents
    - Compresses and synthesizes findings
    - Generates comprehensive research reports

    Returns:
        Dict containing subagent configuration with:
        - name: Unique identifier for the subagent
        - description: When the orchestrator should use this agent
        - graph: The compiled LangGraph graph from open_deep_research

    Note:
        Uses the local copy of open_deep_research in src/open_deep_research/
    """
    # Import the compiled deep_researcher graph
    # This is the full LangGraph implementation from open_deep_research
    from open_deep_research.deep_researcher import deep_researcher

    return {
        "name": "deep-research",
        "description": """Conducts comprehensive web research on any topic.

        Use this agent when you need to:
        - Research companies, markets, or financial trends
        - Gather information from multiple web sources
        - Get up-to-date information not in training data
        - Investigate specific topics or questions
        - Build a knowledge base on a subject

        This agent performs multi-step research with:
        - Clarifying questions for ambiguous queries
        - Parallel research across multiple topics
        - Source verification and synthesis
        - Comprehensive final reports
        """,
        "prompt": "You are a deep research agent (handled by custom graph)",
        "graph": deep_researcher  # Pass the compiled LangGraph graph
    }
