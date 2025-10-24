#!/usr/bin/env python3
"""
Test the daemon cleaner agent.

This simulates a conversation with lots of stale content to see the cleaner in action.
"""

import os
from house_code.core import HouseCode
from house_code.tools.registry import register_all_tools


def test_cleaner_agent():
    """Test the cleaner agent by simulating a messy conversation."""

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Set ANTHROPIC_API_KEY environment variable")
        return

    # Create House Code instance with aggressive cleaning
    agent = HouseCode(
        api_key=api_key,
        enable_auto_cleaning=True,
        cleaning_frequency=2,  # Clean every 2 turns (aggressive for testing)
    )

    # Register tools
    register_all_tools(agent)

    print("=" * 80)
    print("DAEMON CLEANER AGENT TEST")
    print("=" * 80)
    print("\nThis test will:")
    print("1. Ask House Code to read the same file multiple times")
    print("2. Create and update todos")
    print("3. Watch the cleaner agent automatically prune stale content\n")
    print("Cleaning frequency: Every 2 turns")
    print("=" * 80)

    # Turn 1: Read a file
    print("\n\n[TURN 1: Read core.py]")
    response = agent.run("Read the file house_code/core.py and tell me what it does")
    print(f"Response: {response[:200]}...")
    print(f"Context size: {len(agent.context.messages)} messages, ~{agent.context.token_count_estimate()} tokens")

    # Turn 2: Read the same file again (creates superseded content)
    print("\n\n[TURN 2: Read core.py AGAIN - should trigger cleaning]")
    response = agent.run("Read house_code/core.py again and summarize the HouseCode class")
    print(f"Response: {response[:200]}...")
    print(f"Context size: {len(agent.context.messages)} messages, ~{agent.context.token_count_estimate()} tokens")

    # Turn 3: Create todos
    print("\n\n[TURN 3: Create todos]")
    response = agent.run("Create a todo list with 3 items: Learn about House Code, Test the cleaner, Write docs")
    print(f"Response: {response[:200]}...")
    print(f"Context size: {len(agent.context.messages)} messages, ~{agent.context.token_count_estimate()} tokens")

    # Turn 4: Update todos (should trigger cleaning and prune old todo state)
    print("\n\n[TURN 4: Update todos - should trigger cleaning]")
    response = agent.run("Mark the first todo as completed")
    print(f"Response: {response[:200]}...")
    print(f"Context size: {len(agent.context.messages)} messages, ~{agent.context.token_count_estimate()} tokens")

    # Turn 5: More work
    print("\n\n[TURN 5: Read another file]")
    response = agent.run("Read house_code/subagents.py and tell me about sub-agents")
    print(f"Response: {response[:200]}...")
    print(f"Context size: {len(agent.context.messages)} messages, ~{agent.context.token_count_estimate()} tokens")

    # Turn 6: Final turn - should trigger cleaning again
    print("\n\n[TURN 6: Final turn - should trigger cleaning]")
    response = agent.run("Summarize what you've learned about House Code")
    print(f"Response: {response[:200]}...")
    print(f"Context size: {len(agent.context.messages)} messages, ~{agent.context.token_count_estimate()} tokens")

    print("\n\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nThe cleaner agent should have pruned:")
    print("- The first read of core.py (superseded by second read)")
    print("- The first todo state (superseded by updated todos)")
    print("- Any other stale content")
    print("\nContext should be significantly smaller than without cleaning!")


if __name__ == "__main__":
    test_cleaner_agent()
