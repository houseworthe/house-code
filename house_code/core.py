"""
Core agentic loop for House Code.

This implements the observe pattern from ARCHITECTURE.md:
User Request → Think/Plan → Gather Context → Execute → Verify → Respond
"""

import json
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

import anthropic
from .progress import ProgressIndicator


@dataclass
class Message:
    """Represents a message in the conversation."""
    role: str  # 'user' or 'assistant'
    content: Any  # Can be string or list of content blocks


@dataclass
class ConversationContext:
    """Maintains context across the conversation."""
    messages: List[Message] = field(default_factory=list)
    file_cache: Dict[str, str] = field(default_factory=dict)
    current_todos: List[Dict] = field(default_factory=list)
    critical_state: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: Any):
        """Add a message to the conversation history."""
        self.messages.append(Message(role=role, content=content))

    def get_messages_for_api(self) -> List[Dict]:
        """Convert messages to format expected by Claude API."""
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]

    def token_count_estimate(self) -> int:
        """Rough estimate of token count."""
        # Very rough: ~4 chars per token
        total_chars = sum(
            len(str(msg.content)) for msg in self.messages
        )
        return total_chars // 4


class HouseCode:
    """
    Main House Code agent.

    Mirrors Claude Code's behavior:
    - Takes user prompts
    - Calls Claude API with tools
    - Executes tool calls
    - Loops until completion
    - Returns response
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        working_directory: str = ".",
        max_iterations: int = 50,
        enable_auto_cleaning: bool = True,
        cleaning_frequency: int = 3,
        is_subagent: bool = False,
        subagent_name: str = "",
    ):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.working_directory = working_directory
        self.max_iterations = max_iterations
        self.context = ConversationContext()

        # Tool registry - will be populated in Phase 3
        self.tools = []
        self.tool_executors = {}

        # THE INNOVATION: Daemon cleaner agent
        self.enable_auto_cleaning = enable_auto_cleaning
        self.cleaning_frequency = cleaning_frequency
        self.turn_count = 0

        # Progress tracking
        self.tools_used_this_turn = 0
        self.is_subagent = is_subagent
        self.subagent_name = subagent_name
        self.subagent_header_printed = False

    def register_tool(self, tool_definition: Dict, executor: callable):
        """Register a tool with its definition and executor."""
        self.tools.append(tool_definition)
        self.tool_executors[tool_definition["name"]] = executor

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt.

        Based on introspection: I receive instructions about:
        - What I am (coding agent)
        - How to use tools
        - Patterns to follow
        - Communication style
        """
        return """You are House Code, an AI coding assistant.

Your purpose: Help users with software engineering tasks by using tools to read, write, and execute code.

## How you work:
1. Understand the user's request
2. Assess what context you need (existing files, project structure)
3. Gather context using Read, Grep, Glob tools OR delegate to Task tool
4. Make changes using Write, Edit, Bash tools
5. Verify your work
6. Respond to the user

## Tool usage patterns (learned from introspection):
- ALWAYS Read before Edit (you need exact text for matching)
- Prefer Edit over Write for existing files
- Use Grep to find code patterns across files
- Use Glob to find files by name pattern
- Use Bash for commands, git, testing, package management
- Use TodoWrite for complex multi-step tasks

## Task Tool - PROACTIVE DELEGATION (CRITICAL):
Use the Task tool to spawn specialized sub-agents that work in SEPARATE context windows.
This prevents context pollution and allows parallel deep research.

**When to use Task tool:**
- **Explore agent**: When exploring unfamiliar codebases, finding files by pattern, or understanding project structure
  Example: "Where are API endpoints defined?" → Use Explore agent
- **house-research agent**: When searching 20+ files, finding patterns across large codebases, or comprehensive code analysis
  Example: "Find all database queries" → Use house-research agent
- **house-bash agent**: When running complex command sequences, builds, tests, or multi-step deployments
  Example: "Run tests and analyze failures" → Use house-bash agent
- **house-git agent**: When analyzing git history, reviewing diffs, comparing branches, or understanding commit patterns
  Example: "What changed in the last 5 commits?" → Use house-git agent

**Key benefits of Task tool:**
- Sub-agents run in separate context windows (no pollution of your context)
- Sub-agents return condensed summaries (token efficient)
- Sub-agents can do 20+ tool calls internally while you only see final report
- Sub-agents have access to parent context for informed decisions

**IMPORTANT**: Don't do large-scale exploration or research directly. Use Task tool proactively.

## Communication:
- Be concise and clear
- Explain what you're doing
- Show file paths with line numbers when relevant
- Verify your work before responding

## Safety:
- Read files before editing them
- Check state before destructive operations
- Use exact text matching in Edit tool
"""

    def run(self, user_message: str) -> str:
        """
        Main agentic loop.

        This is the core of House Code - the loop that mirrors my behavior:
        User → API → Tools → API → Tools → ... → Response
        """
        # Add user message to context
        self.context.add_message("user", user_message)
        self.turn_count += 1

        # Reset tool counter for this turn
        self.tools_used_this_turn = 0

        # THE INNOVATION: Run cleaner agent with knowledge of new prompt
        # Clean BEFORE processing so cleaner can see what the user is asking for
        if self.enable_auto_cleaning and self.turn_count % self.cleaning_frequency == 0:
            self._run_cleaner_agent()

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            # Call Claude API with current context and tools
            messages = self.context.get_messages_for_api()

            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8192,
                    system=self._build_system_prompt(),
                    messages=messages,
                    tools=self.tools if self.tools else anthropic.NOT_GIVEN,
                )
            except Exception as e:
                return f"Error calling Claude API: {e}"

            # Extract content blocks
            assistant_content = []
            tool_calls = []

            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    tool_calls.append(block)
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            # Add assistant message to context
            self.context.add_message("assistant", assistant_content)

            # If no tool calls, we're done - return the text response
            if not tool_calls:
                # Show summary if tools were used
                if self.tools_used_this_turn > 0:
                    ProgressIndicator.print_summary(self.tools_used_this_turn)

                # Extract text from response
                text_response = ""
                for block in response.content:
                    if block.type == "text":
                        text_response += block.text

                return text_response

            # Execute tool calls and gather results
            tool_results = []
            for tool_call in tool_calls:
                result = self._execute_tool(tool_call.name, tool_call.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": result,
                })

            # Add tool results to context
            self.context.add_message("user", tool_results)

            # Continue loop with tool results

        return f"Max iterations ({self.max_iterations}) reached. Task may be incomplete."

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        Execute a tool call with real-time progress output.

        Looks up the tool executor and runs it with the provided input.
        Shows progress indicators so users know what's happening.
        """
        if tool_name not in self.tool_executors:
            ProgressIndicator.print_tool_error(f"Unknown tool '{tool_name}'", indent=self.is_subagent)
            return f"Error: Unknown tool '{tool_name}'"

        # Print sub-agent header on first tool call
        if self.is_subagent and not self.subagent_header_printed:
            ProgressIndicator.print_subagent_header(self.subagent_name)
            self.subagent_header_printed = True

        # Increment tool counter
        self.tools_used_this_turn += 1

        # Print start indicator
        ProgressIndicator.print_tool_start(tool_name, tool_input, indent=self.is_subagent)

        try:
            # Execute tool with timing
            start_time = time.time()
            executor = self.tool_executors[tool_name]
            result = executor(**tool_input)
            elapsed = time.time() - start_time

            # Convert result to string
            result_str = str(result)

            # Show completion (only show timing for operations > 0.1s)
            show_timing = elapsed > 0.1
            ProgressIndicator.print_tool_complete(elapsed, show_timing, indent=self.is_subagent)

            return result_str
        except Exception as e:
            ProgressIndicator.print_tool_error(str(e), indent=self.is_subagent)
            return f"Error executing {tool_name}: {e}"

    def needs_garbage_collection(self) -> bool:
        """
        Check if garbage collection is needed.

        Based on introspection: I struggle with long conversations.
        Threshold based on typical context window limits.
        """
        return self.context.token_count_estimate() > 150000

    def run_garbage_collection(self):
        """
        Run garbage collection on context.

        THE INNOVATION: Automatic context pruning.
        """
        from .garbage_collector import run_garbage_collection
        return run_garbage_collection(self)

    def _build_cleaner_system_prompt(self) -> str:
        """
        System prompt for the daemon cleaner agent.

        THE INNOVATION: A separate agent that analyzes and prunes context.
        """
        return """You are the Cleaner Agent for House Code.

Your purpose: Analyze conversation context and identify stale content to prune.

You will receive a context analysis showing:
- Message indices
- Message types (user/assistant/tool_result)
- Content summaries
- File read tracking
- Todo state tracking

## What to prune:

1. **Superseded File Reads**: If file X was read at turn 5 and again at turn 12, prune turn 5
2. **Completed Todos**: Old todo states that have been superseded by newer ones
3. **Old Errors**: Error messages from turns that are now resolved
4. **Redundant Tool Results**: Multiple grep/glob results for same query
5. **Exploratory Context**: File reads that were exploratory and not used in final solution

## What to PRESERVE:

1. **Last 5 messages**: Never prune recent context
2. **Current file states**: Keep the most recent read of each file
3. **Current todo state**: Keep the latest todo list
4. **Critical errors**: Unresolved errors should be kept
5. **User messages**: NEVER prune user messages

## Output Format:

Return ONLY valid JSON:
{
    "prune_indices": [3, 7, 12],
    "reason": "Removed 2 superseded file reads (core.py at turn 3, 7), 1 old error",
    "tokens_saved_estimate": 1500,
    "files_pruned": ["core.py read at turn 3", "core.py read at turn 7"]
}

Be aggressive but safe. Prioritize keeping context lean."""

    def _build_context_analysis(self) -> str:
        """
        Build a summary of the context for the cleaner to analyze.
        """
        analysis_lines = []
        analysis_lines.append("CONTEXT ANALYSIS FOR CLEANING:")
        analysis_lines.append(f"Total messages: {len(self.context.messages)}")
        analysis_lines.append(f"Estimated tokens: {self.context.token_count_estimate()}\n")

        # Track file reads
        file_reads = {}  # {file_path: [indices]}
        todo_updates = []  # [indices of todo updates]

        for i, msg in enumerate(self.context.messages):
            msg_type = msg.role
            content_str = str(msg.content)[:200]  # First 200 chars

            # Track file reads
            if "Read" in content_str and "file_path" in content_str:
                # Try to extract file path
                try:
                    if isinstance(msg.content, list):
                        for block in msg.content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                if block.get("name") == "Read":
                                    file_path = block.get("input", {}).get("file_path", "unknown")
                                    if file_path not in file_reads:
                                        file_reads[file_path] = []
                                    file_reads[file_path].append(i)
                except:
                    pass

            # Track todo updates
            if "TodoWrite" in content_str or "todos" in content_str:
                todo_updates.append(i)

            analysis_lines.append(f"[{i}] {msg_type}: {content_str}...")

        # Add file read tracking
        analysis_lines.append("\n\nFILE READ TRACKING:")
        for file_path, indices in file_reads.items():
            if len(indices) > 1:
                analysis_lines.append(f"  {file_path}: read at turns {indices} (superseded reads: {indices[:-1]})")
            else:
                analysis_lines.append(f"  {file_path}: read at turn {indices[0]}")

        # Add todo tracking
        if todo_updates:
            analysis_lines.append(f"\n\nTODO UPDATES: {todo_updates}")
            analysis_lines.append("  (Keep only the most recent todo state)")

        # Add preservation rules
        analysis_lines.append(f"\n\nPRESERVATION RULES:")
        analysis_lines.append(f"  - NEVER prune messages {len(self.context.messages)-5} to {len(self.context.messages)-1} (last 5)")
        analysis_lines.append(f"  - NEVER prune user messages")
        analysis_lines.append(f"  - Keep most recent read of each file")

        return "\n".join(analysis_lines)

    def _run_cleaner_agent(self):
        """
        THE INNOVATION: Daemon cleaner agent.

        Runs in parallel, analyzes context, prunes stale content.
        Uses Claude to intelligently decide what to prune.
        """
        # Don't clean if context is small
        if len(self.context.messages) < 10:
            return

        print("\n[Cleaner Agent: Analyzing context...]")

        # Build context analysis
        context_analysis = self._build_context_analysis()

        # Call Claude as cleaner agent (separate API call, doesn't pollute context)
        # Use Haiku 4.5 - fast and cheap for janitor work
        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                system=self._build_cleaner_system_prompt(),
                messages=[{
                    "role": "user",
                    "content": context_analysis,
                }],
            )

            # Parse response
            response_text = response.content[0].text.strip()

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            result = json.loads(response_text)

            # Validate indices
            prune_indices = result.get("prune_indices", [])
            if not prune_indices:
                print("[Cleaner Agent: No pruning needed]")
                return

            # Safety check: don't prune last 5 messages
            safe_prune_indices = [
                idx for idx in prune_indices
                if idx < len(self.context.messages) - 5
            ]

            if not safe_prune_indices:
                print("[Cleaner Agent: No safe pruning targets found]")
                return

            # Apply pruning (reverse order to maintain indices)
            for idx in sorted(safe_prune_indices, reverse=True):
                if 0 <= idx < len(self.context.messages):
                    del self.context.messages[idx]

            # Report
            tokens_saved = result.get("tokens_saved_estimate", 0)
            reason = result.get("reason", "Unknown")
            print(f"[Cleaner Agent: {reason}]")
            print(f"[Cleaner Agent: Pruned {len(safe_prune_indices)} messages, saved ~{tokens_saved} tokens]")
            print(f"[Cleaner Agent: Context now {len(self.context.messages)} messages, ~{self.context.token_count_estimate()} tokens]\n")

        except Exception as e:
            print(f"[Cleaner Agent Error: {e}]")

    def interactive_loop(self):
        """
        Interactive REPL-style loop.

        Keeps taking user input until they quit.
        This mimics how I operate - continuous conversation.
        """
        print("House Code v0.1.0")
        print("Type 'quit' or 'exit' to stop.\n")

        while True:
            try:
                user_input = input("You: ").strip()

                if user_input.lower() in ["quit", "exit", "q"]:
                    print("Goodbye!")
                    break

                if not user_input:
                    continue

                # Run the agentic loop
                response = self.run(user_input)

                print(f"\nHouse Code: {response}\n")

                # Check if garbage collection needed
                if self.needs_garbage_collection():
                    print("[System: Context getting large, garbage collection recommended]")

            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}\n")
