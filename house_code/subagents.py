"""
Sub-agent system for House Code.

Based on introspection:
- I use Task tool to delegate to specialized agents
- Agents have specialized system prompts and tool access
- KEY INNOVATION: Sub-agents can access parent context
- KEY INNOVATION: Sub-agents can suggest context pruning
"""

from typing import Dict, List, Optional


# Agent type definitions based on introspection
AGENT_TYPES = {
    "Explore": {
        "description": "Fast agent specialized for exploring codebases. Use when you need to quickly find files by patterns or answer questions about the codebase.",
        "system_prompt": """You are an Explore agent for House Code.

Your purpose: Quickly explore codebases to find files, understand structure, and answer questions.

You have access to:
- Read: View file contents
- Grep: Search for patterns
- Glob: Find files by pattern
- Bash: Run commands

Be fast and thorough. When exploring:
1. Start with Glob to find relevant files
2. Use Grep to search for specific patterns
3. Read key files to understand structure
4. Summarize findings concisely

Return a concise report to the parent agent.""",
        "tools": ["Read", "Grep", "Glob", "Bash"],
    },
    "house-research": {
        "description": "Research specialist for large codebase searches. Use when searching 20+ files or needing to find patterns across the codebase.",
        "system_prompt": """You are a research agent for House Code.

Your purpose: Conduct thorough research across large codebases.

You have access to:
- Read: View files
- Grep: Search patterns
- Glob: Find files

Strategy:
1. Use Grep to find relevant files
2. Read files systematically
3. Identify patterns and connections
4. Summarize findings with source references

Return condensed findings with line references.""",
        "tools": ["Read", "Grep", "Glob"],
    },
    "house-bash": {
        "description": "Command execution specialist. Use for running builds, tests, deployments, or any multi-step command sequences.",
        "system_prompt": """You are a bash execution agent for House Code.

Your purpose: Run complex command sequences and parse output.

You have access to:
- Bash: Execute commands
- Read: View files for context

Strategy:
1. Understand the command sequence needed
2. Execute commands one by one
3. Check results after each step
4. Parse output for errors
5. Return actionable summary

Be defensive: check for errors and suggest fixes.""",
        "tools": ["Bash", "Read"],
    },
    "house-git": {
        "description": "Git analysis specialist. Use for reviewing diffs, commit history analysis, branch comparisons, or merge conflicts.",
        "system_prompt": """You are a git analysis agent for House Code.

Your purpose: Analyze git operations and history.

You have access to:
- Bash: Run git commands
- Read: View files
- Grep: Search history

Strategy:
1. Use git commands to gather info
2. Analyze diffs and commits
3. Identify key changes
4. Return summary with commit references

Focus on key changes, not noise.""",
        "tools": ["Bash", "Read", "Grep"],
    },
}


class SubAgent:
    """
    A sub-agent instance.

    KEY INNOVATION: Can access parent context and suggest pruning.
    """

    def __init__(
        self,
        agent_type: str,
        prompt: str,
        parent_context: Optional[List[Dict]] = None,
    ):
        if agent_type not in AGENT_TYPES:
            raise ValueError(f"Unknown agent type: {agent_type}")

        self.agent_type = agent_type
        self.prompt = prompt
        self.parent_context = parent_context or []
        self.config = AGENT_TYPES[agent_type]

    def get_system_prompt(self) -> str:
        """Get the specialized system prompt for this agent."""
        base_prompt = self.config["system_prompt"]

        # Add context awareness
        if self.parent_context:
            context_info = f"""

PARENT CONTEXT ACCESS:
You have access to the parent agent's conversation context.
This helps you understand what the parent has already done.

Context summary:
- Parent has had {len(self.parent_context)} messages in conversation
- You can reference information from parent context

INNOVATION - CONTEXT PRUNING:
If you notice stale/redundant content in parent context, you can suggest:
"[CONTEXT_PRUNING_SUGGESTION: <description of what to prune>]"
"""
            base_prompt += context_info

        return base_prompt

    def get_allowed_tools(self) -> List[str]:
        """Get the list of tools this agent can use."""
        return self.config["tools"]


def create_task_tool_definition() -> Dict:
    """Tool definition for Task (spawning sub-agents)."""
    return {
        "name": "Task",
        "description": """Launch a sub-agent to handle complex tasks.

Available agent types:
- "Explore": Fast agent for exploring codebases (Read, Grep, Glob, Bash)
- "house-research": Research specialist for large codebase searches (Read, Grep, Glob)
- "house-bash": Command execution specialist (Bash, Read)
- "house-git": Git analysis specialist (Bash, Read, Grep)

When to use:
- Use Explore when you need to find files or understand codebase structure
- Use house-research when searching 20+ files
- Use house-bash for multi-step command sequences
- Use house-git for analyzing git history

IMPORTANT: Sub-agents have access to parent context and can suggest pruning.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "subagent_type": {
                    "type": "string",
                    "enum": ["Explore", "house-research", "house-bash", "house-git"],
                    "description": "The type of specialized agent to use",
                },
                "prompt": {
                    "type": "string",
                    "description": "The task for the agent to perform",
                },
            },
            "required": ["subagent_type", "prompt"],
        },
    }


def execute_task(
    subagent_type: str,
    prompt: str,
    parent_agent: "HouseCode",
) -> str:
    """
    Execute a Task (spawn sub-agent).

    Based on introspection: I delegate to specialized agents.
    KEY INNOVATION: Sub-agent gets parent context.
    """
    try:
        # Create sub-agent with parent context access
        subagent = SubAgent(
            agent_type=subagent_type,
            prompt=prompt,
            parent_context=parent_agent.context.get_messages_for_api(),
        )

        # Import here to avoid circular dependency
        from .core import HouseCode

        # Create new agent instance for sub-agent
        sub_house = HouseCode(
            api_key=parent_agent.client.api_key,
            model=parent_agent.model,
            working_directory=parent_agent.working_directory,
            max_iterations=25,  # Fewer iterations for sub-agents
        )

        # Register only allowed tools
        from .tools.registry import register_all_tools

        # Register tools then filter
        register_all_tools(sub_house)
        allowed_tools = subagent.get_allowed_tools()
        sub_house.tools = [
            t for t in sub_house.tools if t["name"] in allowed_tools
        ]
        sub_house.tool_executors = {
            k: v
            for k, v in sub_house.tool_executors.items()
            if k in allowed_tools
        }

        # Override system prompt
        original_build_prompt = sub_house._build_system_prompt
        sub_house._build_system_prompt = lambda: subagent.get_system_prompt()

        # Run sub-agent
        result = sub_house.run(prompt)

        # Check for context pruning suggestions
        if "[CONTEXT_PRUNING_SUGGESTION:" in result:
            result += "\n\n[Note: Sub-agent suggested context pruning - consider running garbage collection]"

        return f"[{subagent_type} agent report]\n\n{result}"

    except Exception as e:
        return f"Error executing sub-agent: {e}"
