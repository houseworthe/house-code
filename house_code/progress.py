"""
Progress output utilities for House Code.

Provides real-time feedback during tool execution so users know what's happening.
"""

import sys
from typing import Dict, Any


class ProgressIndicator:
    """Handles progress output for tool execution."""

    # ANSI color codes
    GRAY = "\033[90m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    @staticmethod
    def supports_color() -> bool:
        """Check if terminal supports ANSI colors."""
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

    @staticmethod
    def format_params(params: Dict[str, Any], max_length: int = 60) -> str:
        """Format parameters for display, truncating if too long."""
        if not params:
            return ""

        # Format key-value pairs
        parts = []
        for key, value in params.items():
            # Convert value to string and truncate if needed
            value_str = str(value)
            if len(value_str) > 50:
                value_str = value_str[:47] + "..."
            parts.append(f"{key}={value_str}")

        result = ", ".join(parts)
        if len(result) > max_length:
            result = result[:max_length-3] + "..."

        return result

    @staticmethod
    def preview_output(output: str, max_lines: int = 5) -> str:
        """Create a preview of tool output (first N lines)."""
        if not output:
            return "(empty output)"

        lines = output.split('\n')
        preview_lines = []

        # Show first max_lines lines
        for i, line in enumerate(lines[:max_lines]):
            # Truncate very long lines
            if len(line) > 100:
                line = line[:97] + "..."
            preview_lines.append(f"     {line}")

        # Add ellipsis if there are more lines
        if len(lines) > max_lines:
            remaining = len(lines) - max_lines
            preview_lines.append(f"     {ProgressIndicator.gray('...')} ({remaining} more lines)")

        return "\n".join(preview_lines)

    @staticmethod
    def gray(text: str) -> str:
        """Apply gray color if supported."""
        if ProgressIndicator.supports_color():
            return f"{ProgressIndicator.GRAY}{text}{ProgressIndicator.RESET}"
        return text

    @staticmethod
    def green(text: str) -> str:
        """Apply green color if supported."""
        if ProgressIndicator.supports_color():
            return f"{ProgressIndicator.GREEN}{text}{ProgressIndicator.RESET}"
        return text

    @staticmethod
    def red(text: str) -> str:
        """Apply red color if supported."""
        if ProgressIndicator.supports_color():
            return f"{ProgressIndicator.RED}{text}{ProgressIndicator.RESET}"
        return text

    @staticmethod
    def blue(text: str) -> str:
        """Apply blue color if supported."""
        if ProgressIndicator.supports_color():
            return f"{ProgressIndicator.BLUE}{text}{ProgressIndicator.RESET}"
        return text

    @staticmethod
    def print_tool_start(tool_name: str, params: Dict[str, Any], indent: bool = False):
        """Print tool execution start indicator (overwrites previous line)."""
        params_str = ProgressIndicator.format_params(params)
        if params_str:
            status_line = f"{ProgressIndicator.blue('⏺')} {tool_name}({params_str})"
        else:
            status_line = f"{ProgressIndicator.blue('⏺')} {tool_name}()"

        # Add indentation for sub-agents
        if indent:
            status_line = f"  {status_line}"

        # Clear line and print status (use \r to go to start of line)
        # \033[K clears from cursor to end of line
        print(f"\r\033[K{status_line}", end='', flush=True)

    @staticmethod
    def print_tool_complete(elapsed_seconds: float, show_timing: bool = True, indent: bool = False):
        """Print tool execution completion indicator (updates same line)."""
        if show_timing:
            completion = f" {ProgressIndicator.green('✓')} ({elapsed_seconds:.1f}s)"
        else:
            completion = f" {ProgressIndicator.green('✓')}"
        print(completion, end='', flush=True)

    @staticmethod
    def print_tool_error(error_msg: str, indent: bool = False):
        """Print tool execution error indicator."""
        print(f" {ProgressIndicator.red('✗')} Error: {error_msg}", end='', flush=True)

    @staticmethod
    def print_subagent_header(agent_name: str):
        """Print header when sub-agent starts executing."""
        header = f"\n  {ProgressIndicator.gray(f'[{agent_name} Agent]')}"
        print(header, flush=True)

    @staticmethod
    def print_summary(tool_count: int):
        """Print summary after all tools complete."""
        # Move to new line and show summary
        summary = f"\r\033[K{ProgressIndicator.green('✓')} Used {tool_count} tool{'s' if tool_count != 1 else ''}"
        print(f"\n{summary}\n", flush=True)

    @staticmethod
    def print_output_preview(output: str, max_lines: int = 5):
        """Print a preview of the tool output (only for verbose mode)."""
        # Don't show preview by default - keep it clean
        pass
