"""
Main entry point for AgentX Financial Research Platform

Provides a simple interface to run financial research queries through the orchestrator.
"""

import os
from dotenv import load_dotenv
from orchestrator import create_orchestrator


def run_query(query: str, verbose: bool = True):
    """
    Run a financial research query through the orchestrator.

    Args:
        query: The research question or task
        verbose: Whether to print streaming output (default: True)

    Returns:
        Final result dictionary containing messages and any artifacts

    Example:
        >>> result = run_query("Research Apple's latest earnings")
    """
    # Create orchestrator with GPT-4o
    orchestrator = create_orchestrator(
        model="openai:gpt-4o",
        temperature=0.7,
    )

    # Prepare input messages
    input_messages = {
        "messages": [{"role": "user", "content": query}]
    }

    if verbose:
        print(f"\n{'='*80}")
        print(f"QUERY: {query}")
        print(f"{'='*80}\n")

    # Stream the orchestrator's response
    final_result = None
    for chunk in orchestrator.stream(input_messages, stream_mode="values"):
        if "messages" in chunk:
            # Get the most recent message
            last_message = chunk["messages"][-1]

            if verbose and hasattr(last_message, "content") and last_message.content:
                # Print message type and content
                msg_type = last_message.type if hasattr(last_message, "type") else "unknown"
                print(f"\n[{msg_type.upper()}]")
                print(last_message.content)
                print("-" * 80)

        final_result = chunk

    if verbose:
        print(f"\n{'='*80}")
        print("RESEARCH COMPLETE")
        print(f"{'='*80}\n")

    return final_result


def interactive_mode():
    """
    Run the orchestrator in interactive mode for multiple queries.
    """
    print("\n" + "="*80)
    print("AgentX Financial Research Platform - Interactive Mode")
    print("="*80)
    print("\nAvailable commands:")
    print("  - Type your research query and press Enter")
    print("  - Type 'quit' or 'exit' to end session")
    print("  - Type 'help' for more information")
    print("\n" + "="*80 + "\n")

    while True:
        try:
            # Get user input
            query = input("\n🔍 Research Query: ").strip()

            # Handle commands
            if query.lower() in ["quit", "exit"]:
                print("\nThank you for using AgentX. Goodbye!\n")
                break

            if query.lower() == "help":
                print("\nAgentX is a financial research orchestrator with 5 specialized agents:")
                print("  1. Deep Research - Web research (FULLY FUNCTIONAL)")
                print("  2. Daloopa - Financial data (placeholder)")
                print("  3. SEC - SEC filings (placeholder)")
                print("  4. Obsidian - Personal notes (placeholder)")
                print("  5. Transcript - Earnings calls (placeholder)")
                print("\nExample queries:")
                print("  - 'Research Apple's latest earnings report'")
                print("  - 'Compare NVDA and AMD market positions'")
                print("  - 'What are the key risks in Tesla's latest 10-K?'")
                continue

            if not query:
                continue

            # Run the query
            run_query(query, verbose=True)

        except KeyboardInterrupt:
            print("\n\nSession interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")


def main():
    """
    Main function - loads environment and starts interactive mode.
    """
    # Load environment variables from .env file
    load_dotenv()

    # Check for required API keys
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ Error: OPENAI_API_KEY not found in environment variables")
        print("Please set it in your .env file or export it:")
        print("  export OPENAI_API_KEY='sk-...'")
        print("\nSee .env.example for a template\n")
        return

    # Start interactive mode
    interactive_mode()


if __name__ == "__main__":
    main()
