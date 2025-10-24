#!/usr/bin/env python3
"""
Test script for progress output feature.

Run this to see the progress indicators in action.
"""

import os
from house_code.core import HouseCode
from house_code.tools.registry import register_all_tools


def main():
    # Get API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        return

    # Create agent
    print("Creating House Code agent...")
    agent = HouseCode(
        api_key=api_key,
        working_directory=".",
        enable_auto_cleaning=False,  # Disable for testing
    )

    # Register tools
    print("Registering tools...")
    register_all_tools(agent)

    print("\n" + "=" * 60)
    print("PROGRESS OUTPUT TEST")
    print("=" * 60)

    # Test 1: Read a small file
    print("\n\nTest 1: Read a small file (README.md)")
    print("-" * 60)
    response = agent.run("Read the README.md file")
    print(f"\nAgent response: {response[:200]}...")

    # Test 2: List files with bash
    print("\n\nTest 2: Execute bash command (ls -la)")
    print("-" * 60)
    response = agent.run("Run 'ls -la house_code' and show me the output")
    print(f"\nAgent response: {response[:200]}...")

    # Test 3: Read a longer file
    print("\n\nTest 3: Read a longer file (core.py)")
    print("-" * 60)
    response = agent.run("Read the house_code/core.py file and tell me how many lines it has")
    print(f"\nAgent response: {response[:200]}...")

    print("\n\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
