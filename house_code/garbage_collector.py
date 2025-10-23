"""
Garbage Collector - THE INNOVATION

This is what Claude Code wishes it had: automatic context pruning.

Based on introspection:
- I struggle with long conversations that accumulate tokens
- Old file reads become superseded by newer reads
- Completed todos are no longer relevant
- Resolved errors don't need full stack traces
- BUT: Must preserve critical state

The garbage collector analyzes conversation history and prunes stale content.
"""

from typing import List, Dict, Set, Tuple
import re


class GarbageCollector:
    """
    Analyzes conversation context and identifies content for pruning.

    This is the innovation House Code has that Claude Code doesn't.
    """

    def __init__(self, context: "ConversationContext"):
        self.context = context

    def analyze(self) -> Dict:
        """
        Analyze conversation and identify prunable content.

        Returns statistics and suggestions.
        """
        messages = self.context.messages

        # Collect file reads
        file_reads = self._find_file_reads(messages)

        # Collect tool results
        tool_results = self._find_tool_results(messages)

        # Collect todos
        todos = self._find_todos(messages)

        # Identify superseded content
        superseded_reads = self._find_superseded_file_reads(file_reads)
        completed_todos = self._find_completed_todos(todos)
        old_errors = self._find_old_errors(messages)

        # Calculate savings
        prunable_messages = len(superseded_reads) + len(completed_todos) + len(old_errors)
        current_tokens = self.context.token_count_estimate()
        potential_savings = self._estimate_savings(
            superseded_reads, completed_todos, old_errors
        )

        return {
            "current_tokens": current_tokens,
            "prunable_messages": prunable_messages,
            "potential_token_savings": potential_savings,
            "superseded_file_reads": len(superseded_reads),
            "completed_todos": len(completed_todos),
            "old_errors": len(old_errors),
            "recommendations": self._generate_recommendations(
                superseded_reads, completed_todos, old_errors
            ),
        }

    def prune(self) -> Tuple[List, int]:
        """
        Prune stale content from context.

        Returns: (new_messages, tokens_saved)
        """
        messages = self.context.messages
        file_reads = self._find_file_reads(messages)
        todos = self._find_todos(messages)

        # Identify what to keep
        superseded_reads = self._find_superseded_file_reads(file_reads)
        completed_todos = self._find_completed_todos(todos)
        old_errors = self._find_old_errors(messages)

        # Build new message list
        new_messages = []
        tokens_saved = 0

        for i, msg in enumerate(messages):
            content_str = str(msg.content)

            # Skip superseded file reads
            if i in superseded_reads:
                tokens_saved += len(content_str) // 4
                # Replace with summary
                new_messages.append(
                    self._create_summary_message(f"[Pruned: superseded file read]")
                )
                continue

            # Skip completed todos (keep only most recent todo state)
            if i in completed_todos:
                tokens_saved += len(content_str) // 4
                continue

            # Compress old errors
            if i in old_errors:
                compressed = self._compress_error(content_str)
                if len(compressed) < len(content_str):
                    tokens_saved += (len(content_str) - len(compressed)) // 4
                    msg.content = compressed

            # Keep critical messages
            new_messages.append(msg)

        return new_messages, tokens_saved

    def _find_file_reads(self, messages) -> Dict[str, List[int]]:
        """Find all file read operations, indexed by file path."""
        file_reads = {}

        for i, msg in enumerate(messages):
            content_str = str(msg.content)
            if "Read" in content_str and "file_path" in content_str:
                # Extract file path (simplified)
                match = re.search(r'"file_path":\s*"([^"]+)"', content_str)
                if match:
                    file_path = match.group(1)
                    if file_path not in file_reads:
                        file_reads[file_path] = []
                    file_reads[file_path].append(i)

        return file_reads

    def _find_superseded_file_reads(self, file_reads: Dict[str, List[int]]) -> Set[int]:
        """Find file reads that have been superseded by later reads."""
        superseded = set()

        for file_path, indices in file_reads.items():
            if len(indices) > 1:
                # Keep only the most recent read
                superseded.update(indices[:-1])

        return superseded

    def _find_tool_results(self, messages) -> List[int]:
        """Find tool result messages."""
        results = []
        for i, msg in enumerate(messages):
            if "tool_result" in str(msg.content):
                results.append(i)
        return results

    def _find_todos(self, messages) -> List[int]:
        """Find TodoWrite messages."""
        todos = []
        for i, msg in enumerate(messages):
            if "TodoWrite" in str(msg.content) or "todos" in str(msg.content).lower():
                todos.append(i)
        return todos

    def _find_completed_todos(self, todo_indices: List[int]) -> Set[int]:
        """Find older todo states (keep only most recent)."""
        if len(todo_indices) <= 1:
            return set()
        # Keep only the most recent todo state
        return set(todo_indices[:-1])

    def _find_old_errors(self, messages) -> Set[int]:
        """Find error messages from earlier in conversation."""
        errors = []
        for i, msg in enumerate(messages):
            content_str = str(msg.content)
            if "error" in content_str.lower() or "traceback" in content_str.lower():
                errors.append(i)

        # Keep recent errors (last 5), mark older ones for compression
        if len(errors) > 5:
            return set(errors[:-5])
        return set()

    def _estimate_savings(
        self, superseded_reads, completed_todos, old_errors
    ) -> int:
        """Estimate token savings from pruning."""
        # Rough estimate: each superseded item saves ~500 tokens on average
        return (
            len(superseded_reads) * 500
            + len(completed_todos) * 200
            + len(old_errors) * 300
        )

    def _generate_recommendations(
        self, superseded_reads, completed_todos, old_errors
    ) -> List[str]:
        """Generate human-readable recommendations."""
        recommendations = []

        if superseded_reads:
            recommendations.append(
                f"Remove {len(superseded_reads)} superseded file reads"
            )

        if completed_todos:
            recommendations.append(
                f"Remove {len(completed_todos)} old todo states"
            )

        if old_errors:
            recommendations.append(f"Compress {len(old_errors)} old error messages")

        if not recommendations:
            recommendations.append("Context is clean, no pruning needed")

        return recommendations

    def _create_summary_message(self, summary: str):
        """Create a summary message for pruned content."""
        from .core import Message

        return Message(role="assistant", content=summary)

    def _compress_error(self, error_content: str) -> str:
        """Compress an error message to just the key info."""
        # Keep first and last line of errors
        lines = error_content.split("\n")
        if len(lines) > 5:
            return "\n".join([lines[0], "...", lines[-1]])
        return error_content


def run_garbage_collection(agent: "HouseCode") -> Dict:
    """
    Run garbage collection on an agent's context.

    Returns statistics about what was pruned.
    """
    gc = GarbageCollector(agent.context)

    # Analyze first
    analysis = gc.analyze()

    # Prune if significant savings
    if analysis["potential_token_savings"] > 1000:
        new_messages, tokens_saved = gc.prune()
        agent.context.messages = new_messages

        return {
            **analysis,
            "action": "pruned",
            "actual_tokens_saved": tokens_saved,
        }
    else:
        return {
            **analysis,
            "action": "no_pruning_needed",
        }
