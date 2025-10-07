"""
Setup script for AgentX Financial Research Platform
"""

from setuptools import setup, find_packages

setup(
    name="agentx",
    version="0.1.0",
    description="AI-powered financial research platform with DeepAgents",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.12",
    install_requires=[
        "deepagents>=0.0.1",
        "langgraph",
        "langchain-core",
        "langchain-openai",
        "tavily-python",
        "python-dotenv",
    ],
)
