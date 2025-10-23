"""
TodoWrite tool implementation.

Based on introspection:
- I use TodoWrite to plan and track complex multi-step tasks
- Critical for maintaining focus
- Gives user visibility into progress
- States: pending, in_progress, completed
"""

from typing import List, Dict
import json


# Global state for todos (in real implementation, this would be in agent context)
_current_todos: List[Dict] = []


def create_todowrite_tool_definition() -> dict:
    """Tool definition for Claude API."""
    return {
        "name": "TodoWrite",
        "description": """Create and manage a structured task list for the current session.

Usage:
- Use proactively for complex multi-step tasks (3+ steps)
- Use when user provides multiple tasks
- Update task status as you work (exactly ONE task should be in_progress)
- Mark tasks completed IMMEDIATELY after finishing
- Each task needs: content (imperative form), status, activeForm (present continuous)

Task states: pending, in_progress, completed

Example:
- content: "Fix authentication bug"
- activeForm: "Fixing authentication bug"
- status: "in_progress"

IMPORTANT:
- ONLY mark a task as completed when FULLY accomplished
- If you encounter errors or cannot finish, keep as in_progress
- Never mark completed if tests are failing or implementation is partial""",
        "input_schema": {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "description": "The updated todo list",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "What needs to be done (imperative form)",
                            },
                            "activeForm": {
                                "type": "string",
                                "description": "Present continuous form shown during execution",
                            },
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"],
                                "description": "Task status",
                            },
                        },
                        "required": ["content", "status", "activeForm"],
                    },
                },
            },
            "required": ["todos"],
        },
    }


def execute_todowrite(todos: List[Dict]) -> str:
    """
    Execute the TodoWrite tool.

    Based on introspection: I use todos to track progress on complex tasks.
    """
    global _current_todos

    try:
        # Validate todos
        for i, todo in enumerate(todos):
            if "content" not in todo or "status" not in todo or "activeForm" not in todo:
                return f"Error: Todo {i} missing required fields (content, status, activeForm)"

            if todo["status"] not in ["pending", "in_progress", "completed"]:
                return f"Error: Todo {i} has invalid status: {todo['status']}"

        # Check that exactly one is in_progress (or zero if all done)
        in_progress_count = sum(1 for t in todos if t["status"] == "in_progress")
        if in_progress_count > 1:
            return "Warning: Multiple tasks marked as in_progress. Should be exactly one."

        # Update todos
        _current_todos = todos

        # Format output
        completed = sum(1 for t in todos if t["status"] == "completed")
        pending = sum(1 for t in todos if t["status"] == "pending")
        in_progress = sum(1 for t in todos if t["status"] == "in_progress")

        output = f"Todos updated: {completed} completed, {in_progress} in progress, {pending} pending"

        # Show current in_progress task
        for todo in todos:
            if todo["status"] == "in_progress":
                output += f"\n\nCurrent task: {todo['activeForm']}"
                break

        return output

    except Exception as e:
        return f"Error updating todos: {e}"


def get_current_todos() -> List[Dict]:
    """Get current todos (for context management)."""
    return _current_todos
