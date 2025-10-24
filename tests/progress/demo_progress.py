#!/usr/bin/env python3
"""
Demo script to show progress output formatting.

This demonstrates what users will see during tool execution.
"""

import time
from house_code.progress import ProgressIndicator


def demo_read_tool():
    """Demonstrate progress output for Read tool."""
    print("\n" + "=" * 70)
    print("DEMO: Reading a file")
    print("=" * 70)

    # Simulate tool execution
    tool_name = "Read"
    params = {"file_path": "house_code/core.py"}

    ProgressIndicator.print_tool_start(tool_name, params)

    # Simulate execution time
    time.sleep(0.3)

    # Simulate output
    output = """     1→#!/usr/bin/env python3
     2→\"\"\"
     3→Core agentic loop for House Code.
     4→\"\"\"
     5→import json
     6→import time
     7→from typing import List, Dict, Any, Optional
     8→from dataclasses import dataclass, field
     9→
    10→import anthropic
    11→from .progress import ProgressIndicator
... (464 more lines)"""

    ProgressIndicator.print_output_preview(output, max_lines=10)
    ProgressIndicator.print_tool_complete(0.3, show_timing=True)


def demo_bash_tool():
    """Demonstrate progress output for Bash tool."""
    print("\n" + "=" * 70)
    print("DEMO: Running a bash command")
    print("=" * 70)

    tool_name = "Bash"
    params = {"command": "ls -la house_code/", "description": "List files in house_code directory"}

    ProgressIndicator.print_tool_start(tool_name, params)

    time.sleep(0.5)

    output = """total 128
drwxr-xr-x  12 user  staff   384 Oct 23 10:30 .
drwxr-xr-x  15 user  staff   480 Oct 23 09:15 ..
-rw-r--r--   1 user  staff  1234 Oct 23 10:25 __init__.py
-rw-r--r--   1 user  staff 15678 Oct 23 10:30 core.py
-rw-r--r--   1 user  staff  2345 Oct 23 09:20 cli.py
-rw-r--r--   1 user  staff  8901 Oct 23 10:15 garbage_collector.py
-rw-r--r--   1 user  staff  3456 Oct 23 10:28 progress.py
drwxr-xr-x   8 user  staff   256 Oct 23 09:30 tools"""

    ProgressIndicator.print_output_preview(output, max_lines=5)
    ProgressIndicator.print_tool_complete(0.5, show_timing=True)


def demo_grep_tool():
    """Demonstrate progress output for Grep tool."""
    print("\n" + "=" * 70)
    print("DEMO: Searching for a pattern")
    print("=" * 70)

    tool_name = "Grep"
    params = {
        "pattern": "def.*tool",
        "path": "house_code/",
        "output_mode": "files_with_matches"
    }

    ProgressIndicator.print_tool_start(tool_name, params)

    time.sleep(0.2)

    output = """house_code/core.py
house_code/tools/read.py
house_code/tools/write.py
house_code/tools/edit.py
house_code/tools/bash.py
house_code/tools/grep.py
house_code/tools/glob.py
house_code/tools/todowrite.py
house_code/tools/registry.py"""

    ProgressIndicator.print_output_preview(output, max_lines=5)
    ProgressIndicator.print_tool_complete(0.2, show_timing=True)


def demo_long_output():
    """Demonstrate truncation for long outputs."""
    print("\n" + "=" * 70)
    print("DEMO: Long output (truncation)")
    print("=" * 70)

    tool_name = "Read"
    params = {"file_path": "very_long_file.py"}

    ProgressIndicator.print_tool_start(tool_name, params)

    time.sleep(0.4)

    # Create a long output
    lines = [f"     {i}→Line {i} of code" for i in range(1, 101)]
    output = "\n".join(lines)

    ProgressIndicator.print_output_preview(output, max_lines=5)
    ProgressIndicator.print_tool_complete(0.4, show_timing=True)


def demo_error():
    """Demonstrate error output."""
    print("\n" + "=" * 70)
    print("DEMO: Tool error")
    print("=" * 70)

    tool_name = "Read"
    params = {"file_path": "nonexistent_file.py"}

    ProgressIndicator.print_tool_start(tool_name, params)

    time.sleep(0.1)

    ProgressIndicator.print_tool_error("File not found: nonexistent_file.py")


def demo_fast_tool():
    """Demonstrate fast tool (no timing shown)."""
    print("\n" + "=" * 70)
    print("DEMO: Fast tool execution (< 0.1s, no timing)")
    print("=" * 70)

    tool_name = "TodoWrite"
    params = {"todos": [{"content": "Test task", "status": "pending"}]}

    ProgressIndicator.print_tool_start(tool_name, params)

    time.sleep(0.05)

    output = "Todos have been modified successfully."

    ProgressIndicator.print_output_preview(output, max_lines=5)
    ProgressIndicator.print_tool_complete(0.05, show_timing=False)


def main():
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "HOUSE CODE PROGRESS OUTPUT DEMO" + " " * 21 + "║")
    print("╚" + "=" * 68 + "╝")

    # Run all demos
    demo_read_tool()
    demo_bash_tool()
    demo_grep_tool()
    demo_long_output()
    demo_fast_tool()
    demo_error()

    print("\n" + "=" * 70)
    print("Demo complete! This is what users will see during tool execution.")
    print("=" * 70)
    print("\nKey features:")
    print("  • Real-time feedback before/during/after tool execution")
    print("  • Color-coded indicators (⏺ starting, ✓ success, ✗ error)")
    print("  • Output preview (first 5 lines)")
    print("  • Timing for slow operations (> 0.1s)")
    print("  • Truncation for long outputs")
    print()


if __name__ == "__main__":
    main()
