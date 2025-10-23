"""
Tool registry for House Code.

Registers all available tools with the agent.
"""

from .write import create_write_tool_definition, execute_write
from .read import create_read_tool_definition, execute_read
from .edit import create_edit_tool_definition, execute_edit
from .bash import create_bash_tool_definition, execute_bash
from .grep import create_grep_tool_definition, execute_grep
from .glob import create_glob_tool_definition, execute_glob
from .todowrite import create_todowrite_tool_definition, execute_todowrite
from ..subagents import create_task_tool_definition, execute_task


def register_all_tools(agent):
    """
    Register all tools with the House Code agent.

    Based on introspection, these are the core tools I use.
    """
    # Read tool - most frequently used
    agent.register_tool(
        create_read_tool_definition(),
        execute_read,
    )

    # Write tool - for creating new files
    agent.register_tool(
        create_write_tool_definition(),
        execute_write,
    )

    # Edit tool - preferred over Write for existing files
    agent.register_tool(
        create_edit_tool_definition(),
        execute_edit,
    )

    # Bash tool - for commands, git, testing
    agent.register_tool(
        create_bash_tool_definition(),
        execute_bash,
    )

    # Grep tool - for searching code patterns
    agent.register_tool(
        create_grep_tool_definition(),
        execute_grep,
    )

    # Glob tool - for finding files by pattern
    agent.register_tool(
        create_glob_tool_definition(),
        execute_glob,
    )

    # TodoWrite tool - for planning complex tasks
    agent.register_tool(
        create_todowrite_tool_definition(),
        execute_todowrite,
    )

    # Task tool - for delegating to sub-agents
    # Special handling: needs parent_agent parameter
    agent.register_tool(
        create_task_tool_definition(),
        lambda subagent_type, prompt: execute_task(subagent_type, prompt, agent),
    )
