"""Subagent configurations for the AgentX orchestrator"""

from .research_agent import create_research_subagent
from .daloopa_agent import create_daloopa_subagent
from .sec_agent import create_sec_subagent
from .obsidian_agent import create_obsidian_subagent
from .transcript_agent import create_transcript_subagent

__all__ = [
    "create_research_subagent",
    "create_daloopa_subagent",
    "create_sec_subagent",
    "create_obsidian_subagent",
    "create_transcript_subagent",
]
