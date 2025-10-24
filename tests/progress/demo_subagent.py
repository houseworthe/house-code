#!/usr/bin/env python3
"""
Demo script to show sub-agent progress output.

This demonstrates what users will see when a sub-agent executes.
"""

import time
from house_code.progress import ProgressIndicator


def demo_subagent_execution():
    """Demonstrate progress output with sub-agent."""
    print("\n" + "=" * 70)
    print("DEMO: Task tool spawning a sub-agent")
    print("=" * 70)

    # Main tool starts (Task tool)
    tool_name = "Task"
    params = {
        "subagent_type": "Explore",
        "prompt": "Find all Python files and identify the main entry point"
    }

    print("\nYou: Can you explore the codebase and find the main entry point?\n")

    # Show Task tool starting
    ProgressIndicator.print_tool_start(tool_name, params, indent=False)
    time.sleep(0.1)

    # Sub-agent header
    ProgressIndicator.print_subagent_header("Explore")

    # Sub-agent executes tools (indented)
    # Tool 1: Glob
    ProgressIndicator.print_tool_start("Glob", {"pattern": "**/*.py"}, indent=True)
    time.sleep(0.3)
    ProgressIndicator.print_tool_complete(0.3, show_timing=False, indent=True)

    # Tool 2: Read
    ProgressIndicator.print_tool_start("Read", {"file_path": "house_code/cli.py"}, indent=True)
    time.sleep(0.2)
    ProgressIndicator.print_tool_complete(0.2, show_timing=True, indent=True)

    # Tool 3: Grep
    ProgressIndicator.print_tool_start("Grep", {"pattern": "if __name__", "path": "."}, indent=True)
    time.sleep(0.2)
    ProgressIndicator.print_tool_complete(0.2, show_timing=False, indent=True)

    # Tool 4: Read again
    ProgressIndicator.print_tool_start("Read", {"file_path": "house_code/__init__.py"}, indent=True)
    time.sleep(0.15)
    ProgressIndicator.print_tool_complete(0.15, show_timing=True, indent=True)

    # Task completes
    print("\n")
    ProgressIndicator.print_tool_start(tool_name, params, indent=False)
    ProgressIndicator.print_tool_complete(1.2, show_timing=True, indent=False)

    # Final summary
    ProgressIndicator.print_summary(1)

    print("\nHouse Code: The main entry point is in house_code/cli.py. The CLI uses Click...")
    print()


def demo_multiple_subagents():
    """Demonstrate multiple sub-agents in one turn."""
    print("\n" + "=" * 70)
    print("DEMO: Multiple sub-agents")
    print("=" * 70)

    print("\nYou: Search the codebase and run the tests\n")

    # First sub-agent: house-research
    ProgressIndicator.print_tool_start("Task", {"subagent_type": "house-research", "prompt": "Find all test files"}, indent=False)
    ProgressIndicator.print_subagent_header("house-research")

    ProgressIndicator.print_tool_start("Grep", {"pattern": "test_", "path": "."}, indent=True)
    time.sleep(0.2)
    ProgressIndicator.print_tool_complete(0.2, show_timing=False, indent=True)

    ProgressIndicator.print_tool_start("Read", {"file_path": "test_phase2.py"}, indent=True)
    time.sleep(0.15)
    ProgressIndicator.print_tool_complete(0.15, show_timing=True, indent=True)

    print("\n")
    ProgressIndicator.print_tool_start("Task", {"subagent_type": "house-research", "prompt": "..."}, indent=False)
    ProgressIndicator.print_tool_complete(0.5, show_timing=True, indent=False)

    # Second sub-agent: house-bash
    ProgressIndicator.print_tool_start("Task", {"subagent_type": "house-bash", "prompt": "Run pytest"}, indent=False)
    ProgressIndicator.print_subagent_header("house-bash")

    ProgressIndicator.print_tool_start("Bash", {"command": "pytest -v"}, indent=True)
    time.sleep(1.5)
    ProgressIndicator.print_tool_complete(1.5, show_timing=True, indent=True)

    print("\n")
    ProgressIndicator.print_tool_start("Task", {"subagent_type": "house-bash", "prompt": "..."}, indent=False)
    ProgressIndicator.print_tool_complete(1.8, show_timing=True, indent=False)

    # Final summary
    ProgressIndicator.print_summary(2)

    print("\nHouse Code: I found 3 test files and ran them. All tests passed!")
    print()


def main():
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 18 + "SUB-AGENT PROGRESS DEMO" + " " * 25 + "║")
    print("╚" + "=" * 68 + "╝")

    demo_subagent_execution()
    demo_multiple_subagents()

    print("=" * 70)
    print("Demo complete!")
    print("=" * 70)
    print("\nKey features:")
    print("  • Main Task tool shows on primary level")
    print("  • Sub-agent header shows which agent is running")
    print("  • Sub-agent tools are indented for clarity")
    print("  • Same line-updating behavior for all tools")
    print("  • Summary shows total tools used by parent")
    print()


if __name__ == "__main__":
    main()
