"""
Core agentic loop for House Code.

This implements the observe pattern from ARCHITECTURE.md:
User Request → Think/Plan → Gather Context → Execute → Verify → Respond
"""

import json
import time
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, field

import anthropic
from .progress import ProgressIndicator

if TYPE_CHECKING:
    from .visual import VisualCache, CompressionStats


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
    visual_cache: Optional['VisualCache'] = None  # Phase 5: Visual memory cache
    compression_stats: Optional['CompressionStats'] = None  # Phase 6: Compression statistics

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
        enable_visual_compression: Optional[bool] = None,
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

        # Phase 5: Initialize visual memory
        from .visual import VisualCache, RosieClient, load_config, CompressionStats
        config = load_config()
        self.visual_config = config  # Store for later access
        self.context.visual_cache = VisualCache(
            max_entries=config.cache_max_entries,
            max_size_mb=config.cache_max_size_mb,
            cache_path=config.cache_path,
        )
        self.rosie_client = RosieClient(config)

        # Phase 6: Initialize compression stats and settings
        self.context.compression_stats = CompressionStats()
        # Use config value if not explicitly provided
        self.enable_visual_compression = (
            enable_visual_compression
            if enable_visual_compression is not None
            else config.enable_auto_compression
        )

    def register_tool(self, tool_definition: Dict, executor: callable):
        """Register a tool with its definition and executor."""
        self.tools.append(tool_definition)
        self.tool_executors[tool_definition["name"]] = executor

    def _build_compression_status(self) -> str:
        """
        Build compression status section for system prompt.

        Returns:
            Formatted compression status string
        """
        if not self.enable_visual_compression:
            return "Visual Memory: DISABLED"

        stats = self.context.compression_stats
        mode = "mock mode" if self.visual_config.use_mock else "real mode"

        # Find compressed message placeholders
        compressed_blocks = []
        for idx, msg in enumerate(self.context.messages):
            if msg.role == "assistant" and isinstance(msg.content, list):
                for block in msg.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        metadata = block.get("metadata", {})
                        if metadata.get("compressed"):
                            start = metadata.get("start_idx")
                            end = metadata.get("end_idx")
                            compressed_blocks.append(f"turns {start}-{end}")

        lines = [
            "Visual Memory Compression:",
            f"  Status: ENABLED ({mode})",
            f"  Compressed blocks: {len(compressed_blocks)}",
        ]

        if compressed_blocks:
            blocks_str = ", ".join(compressed_blocks[:5])  # Show first 5
            if len(compressed_blocks) > 5:
                blocks_str += f" + {len(compressed_blocks) - 5} more"
            lines.append(f"  Blocks: {blocks_str}")

        if stats and stats.total_compressions > 0:
            lines.append(f"  Token savings: ~{stats.total_tokens_saved} tokens")
            lines.append(f"  Average ratio: {stats.average_compression_ratio:.1f}x")

        lines.append(f"  Age threshold: {self.visual_config.compression_age_threshold} turns")
        lines.append("")
        lines.append("  Note: Compressed messages can be retrieved using DecompressVisualMemory tool")
        lines.append("  if needed. Provide message_ids like ['turn_0', 'turn_1', ...].")

        return "\n".join(lines)

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

## {compression_status}
""".format(compression_status=self._build_compression_status())

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

        # Phase 6: Compress old messages after cleaning
        if self.enable_visual_compression:
            compressed_count = self._compress_old_messages()
            # Stats are already printed in _compress_old_messages()

    def _compress_old_messages(self) -> int:
        """
        Compress old messages during garbage collection.

        Identifies message blocks older than threshold and compresses
        them to visual tokens, replacing with placeholders.

        Returns:
            Number of blocks successfully compressed
        """
        import time

        # Identify compressible message blocks
        blocks = self._identify_compressible_messages()

        if not blocks:
            return 0

        compressed_count = 0
        total_tokens_saved = 0

        start_time = time.time()

        # Compress each block (process in reverse to maintain indices)
        for start_idx, end_idx in reversed(blocks):
            # Compress block
            memory = self._compress_message_block(start_idx, end_idx)

            if memory:
                # Replace with placeholder
                self._replace_with_placeholder(start_idx, end_idx, memory)

                # Update stats
                tokens_saved = memory.savings_estimate
                total_tokens_saved += tokens_saved
                compressed_count += 1

                # Update compression stats
                elapsed_ms = (time.time() - start_time) * 1000
                self.context.compression_stats.update_compression(
                    tokens_saved=tokens_saved,
                    compression_ratio=memory.compression_ratio,
                    latency_ms=elapsed_ms,
                )

        # Report results
        if compressed_count > 0:
            elapsed_total = time.time() - start_time
            print(f"[Visual Memory: Compressed {compressed_count} block(s)]")
            print(f"[Visual Memory: Saved ~{total_tokens_saved} tokens ({elapsed_total:.1f}s)]")

        return compressed_count

    def _identify_compressible_messages(self) -> List[tuple[int, int]]:
        """
        Identify blocks of old messages that can be compressed.

        Returns list of (start_idx, end_idx) tuples representing
        consecutive old messages suitable for compression.

        Preserves:
        - Last 5 messages (safety buffer)
        - Messages younger than age threshold
        """
        threshold = self.visual_config.compression_age_threshold
        total_messages = len(self.context.messages)

        # Safety: preserve last 5 messages
        if total_messages <= 5:
            return []

        max_compressible_idx = total_messages - 5 - 1  # -1 for 0-based indexing

        # Calculate age for each message (turns since it was added)
        # Current turn is self.turn_count
        compressible_blocks = []
        block_start = None

        for idx in range(max_compressible_idx + 1):
            # Calculate message age in turns
            # Approximate: messages at idx were added ~(total_messages - idx) turns ago
            # More accurate: turn_count - (message creation turn)
            # For simplicity, use message position as proxy for age
            message_age_estimate = total_messages - idx

            is_old = message_age_estimate > threshold

            # Check if message is user message (never compress user messages)
            msg = self.context.messages[idx]
            is_user = msg.role == "user"

            if is_old and not is_user:
                # Start or continue block
                if block_start is None:
                    block_start = idx
            else:
                # End block if one was started
                if block_start is not None:
                    compressible_blocks.append((block_start, idx - 1))
                    block_start = None

        # Close final block if still open
        if block_start is not None:
            compressible_blocks.append((block_start, max_compressible_idx))

        return compressible_blocks

    def _extract_message_text(self, messages: List[Message]) -> str:
        """
        Extract text content from a list of messages.

        Formats messages similar to how they appear in context.

        Args:
            messages: List of Message objects

        Returns:
            Formatted text string
        """
        lines = []

        for i, msg in enumerate(messages):
            role = msg.role.upper()
            lines.append(f"[{role}]")

            # Handle different content types
            content = msg.content

            if isinstance(content, str):
                lines.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        block_type = block.get("type", "unknown")

                        if block_type == "text":
                            lines.append(block.get("text", ""))
                        elif block_type == "tool_use":
                            tool_name = block.get("name", "unknown")
                            tool_input = block.get("input", {})
                            lines.append(f"[Tool: {tool_name}]")
                            lines.append(f"Input: {str(tool_input)[:200]}")
                        elif block_type == "tool_result":
                            result_text = block.get("content", "")
                            lines.append(f"[Tool Result]")
                            lines.append(str(result_text)[:200])
                    else:
                        lines.append(str(block))
            else:
                lines.append(str(content))

            lines.append("")  # Blank line between messages

        return "\n".join(lines)

    def _compress_message_block(
        self,
        start_idx: int,
        end_idx: int,
    ) -> Optional['VisualMemory']:
        """
        Compress a block of messages to visual tokens.

        Args:
            start_idx: Starting message index (inclusive)
            end_idx: Ending message index (inclusive)

        Returns:
            VisualMemory object if successful, None on error
        """
        try:
            from .visual import create_renderer, VisualMemory

            # Extract messages
            messages = self.context.messages[start_idx:end_idx + 1]

            # Generate message IDs (turn-based)
            message_ids = [f"turn_{i}" for i in range(start_idx, end_idx + 1)]

            # Extract text
            text = self._extract_message_text(messages)
            if not text or not text.strip():
                return None

            # Render to image
            renderer = create_renderer()
            images = renderer.render_conversation(text, message_ids)

            if not images:
                return None

            # Compress (Phase 5: only first image)
            first_image = images[0]
            visual_tokens = self.rosie_client.compress(first_image.image_bytes)

            # Create VisualMemory entry
            compression_ratio = visual_tokens.metadata.get("compression_ratio", 8.0)
            memory = VisualMemory(
                message_ids=message_ids,
                visual_tokens=visual_tokens,
                original_text_length=len(text),
                compression_ratio=compression_ratio,
            )

            # Store in cache
            cache_key = ",".join(message_ids)
            self.context.visual_cache.put(cache_key, memory)

            return memory

        except Exception as e:
            print(f"[Compression Error: {e}]")
            return None

    def _replace_with_placeholder(
        self,
        start_idx: int,
        end_idx: int,
        memory: 'VisualMemory',
    ) -> None:
        """
        Replace message block with compression placeholder.

        Args:
            start_idx: Starting message index
            end_idx: Ending message index
            memory: VisualMemory object with compression details
        """
        # Create placeholder content
        placeholder_text = (
            f"[COMPRESSED: turns {start_idx}-{end_idx}, "
            f"{memory.token_count} visual tokens, "
            f"{memory.compression_ratio}x ratio]"
        )

        # Create placeholder message with metadata
        placeholder_msg = Message(
            role="assistant",
            content=[{
                "type": "text",
                "text": placeholder_text,
                "metadata": {
                    "compressed": True,
                    "cache_key": ",".join(memory.message_ids),
                    "start_idx": start_idx,
                    "end_idx": end_idx,
                    "token_count": memory.token_count,
                    "compression_ratio": memory.compression_ratio,
                }
            }]
        )

        # Replace messages[start_idx:end_idx+1] with placeholder
        # Delete old messages
        del self.context.messages[start_idx:end_idx + 1]

        # Insert placeholder
        self.context.messages.insert(start_idx, placeholder_msg)

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
