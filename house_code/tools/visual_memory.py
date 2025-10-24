"""
Visual memory tools for House Code.

Provides tools for compressing conversation history into visual tokens
and decompressing them back to text.
"""

import time
import logging
from typing import List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core import HouseCode

from ..visual import (
    create_renderer,
    RosieClient,
    VisualMemory,
)


# Set up logging
logger = logging.getLogger(__name__)


# ========== Tool 1: Compress Visual Memory ==========

def create_compress_tool_definition() -> Dict:
    """
    Create tool definition for compressing conversation text to visual tokens.

    Returns:
        Tool definition dict for Claude API
    """
    return {
        "name": "CompressVisualMemory",
        "description": (
            "Compress conversation messages into visual tokens using OCR compression. "
            "Converts text to rendered images and compresses them to visual tokens, "
            "achieving 7-20x compression over raw text. The compressed memory is cached "
            "for later retrieval. Currently operates in MOCK mode (returns placeholder "
            "tokens) until Rosie supercomputer integration is complete."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The conversation text to compress (code, messages, etc.)",
                },
                "message_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of message IDs to associate with this compression (for cache retrieval)",
                },
            },
            "required": ["text", "message_ids"],
        },
    }


def execute_compress(text: str, message_ids: List[str], agent: "HouseCode") -> str:
    """
    Execute visual memory compression.

    Args:
        text: Text content to compress
        message_ids: Message IDs for cache key
        agent: HouseCode agent instance (for cache access)

    Returns:
        Formatted stats string showing compression results
    """
    start_time = time.time()

    # Validate inputs
    if not text or not text.strip():
        return "Error: Cannot compress empty text"

    if not message_ids or len(message_ids) == 0:
        return "Error: Must provide at least one message ID"

    # Generate cache key from message IDs
    cache_key = ",".join(message_ids)

    try:
        # Step 1: Render text to image
        logger.debug(f"Rendering {len(text)} chars to image")
        renderer = create_renderer()
        images = renderer.render_conversation(text, message_ids)

        if not images or len(images) == 0:
            return "Error: Rendering failed - no images generated"

        # For Phase 5, only compress first image
        first_image = images[0]
        logger.debug(f"Generated {len(images)} image(s), compressing first ({first_image.size_kb:.1f} KB)")

        # Step 2: Compress image to visual tokens
        client = agent.rosie_client
        visual_tokens = client.compress(first_image.image_bytes)

        # Step 3: Calculate stats
        original_length = len(text)
        token_count = len(visual_tokens)
        compression_ratio = visual_tokens.metadata.get("compression_ratio", 8.0)

        # Rough estimate: original text in tokens (chars / 4) - visual tokens
        estimated_text_tokens = original_length // 4
        savings_estimate = estimated_text_tokens - token_count

        # Step 4: Create VisualMemory entry
        memory = VisualMemory(
            message_ids=message_ids,
            visual_tokens=visual_tokens,
            original_text_length=original_length,
            compression_ratio=compression_ratio,
        )

        # Step 5: Store in cache
        cache = agent.context.visual_cache
        cache.put(cache_key, memory)

        # Calculate elapsed time
        elapsed_ms = (time.time() - start_time) * 1000

        # Step 6: Format output
        mode = "MOCK" if client.config.use_mock else "REAL"

        output = []
        output.append(f"✓ Compressed {original_length:,} chars → {token_count} visual tokens")
        output.append(f"  Compression: {compression_ratio}x ratio")
        output.append(f"  Savings: ~{savings_estimate} tokens (estimated)")
        output.append(f"  Cache: Stored under key '{cache_key}'")
        output.append(f"  Mode: {mode}")
        output.append(f"  Latency: {elapsed_ms:.0f}ms")

        if len(images) > 1:
            output.append(f"  Note: Generated {len(images)} images, but only compressed first (Phase 5 limitation)")

        logger.info(f"Compressed {original_length} chars → {token_count} tokens ({compression_ratio}x)")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Compression failed: {e}")
        return f"Error: Compression failed - {str(e)}"


# ========== Tool 2: Decompress Visual Memory ==========

def create_decompress_tool_definition() -> Dict:
    """
    Create tool definition for decompressing visual tokens back to text.

    Returns:
        Tool definition dict for Claude API
    """
    return {
        "name": "DecompressVisualMemory",
        "description": (
            "Retrieve and decompress visual memory back to text. "
            "Looks up cached visual tokens by message IDs and decompresses them. "
            "Currently operates in MOCK mode (returns placeholder text showing "
            "token count and metadata) until Rosie supercomputer integration is complete."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of message IDs to retrieve from cache",
                },
            },
            "required": ["message_ids"],
        },
    }


def execute_decompress(message_ids: List[str], agent: "HouseCode") -> str:
    """
    Execute visual memory decompression.

    Args:
        message_ids: Message IDs to retrieve
        agent: HouseCode agent instance (for cache access)

    Returns:
        Decompressed text (or placeholder in mock mode)
    """
    start_time = time.time()

    # Validate inputs
    if not message_ids or len(message_ids) == 0:
        return "Error: Must provide at least one message ID"

    # Generate cache key
    cache_key = ",".join(message_ids)

    try:
        # Step 1: Look up in cache
        cache = agent.context.visual_cache
        memory = cache.get(cache_key)

        if memory is None:
            # Cache miss - return helpful error
            available_keys = cache.keys()
            if len(available_keys) == 0:
                return f"Error: No visual memory found for message IDs: {message_ids}\n(Cache is empty)"
            else:
                return f"Error: No visual memory found for message IDs: {message_ids}\n\nAvailable cache keys:\n" + "\n".join(f"  - {key}" for key in available_keys[:5])

        # Step 2: Decompress tokens
        client = agent.rosie_client
        decompressed_text = client.decompress(memory.visual_tokens)

        # Calculate elapsed time
        elapsed_ms = (time.time() - start_time) * 1000

        # Step 3: Format output
        mode = "MOCK" if client.config.use_mock else "REAL"

        output = []
        output.append(f"✓ Decompressed visual memory for: {cache_key}")
        output.append(f"  Token count: {memory.token_count}")
        output.append(f"  Original length: {memory.original_text_length:,} chars")
        output.append(f"  Compression ratio: {memory.compression_ratio}x")
        output.append(f"  Mode: {mode}")
        output.append(f"  Latency: {elapsed_ms:.0f}ms")
        output.append("")
        output.append("Decompressed content:")
        output.append("-" * 60)
        output.append(decompressed_text)
        output.append("-" * 60)

        logger.info(f"Decompressed {memory.token_count} tokens → {len(decompressed_text)} chars")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Decompression failed: {e}")
        return f"Error: Decompression failed - {str(e)}"


# ========== Tool 3: Get Visual Memory Stats ==========

def create_stats_tool_definition() -> Dict:
    """
    Create tool definition for querying visual memory cache statistics.

    Returns:
        Tool definition dict for Claude API
    """
    return {
        "name": "GetVisualMemoryStats",
        "description": (
            "Get statistics about the visual memory cache, including hit rate, "
            "size, entry count, and evictions. Useful for monitoring cache "
            "utilization and deciding when to compress more messages."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }


def execute_stats(agent: "HouseCode") -> str:
    """
    Execute visual memory stats query.

    Args:
        agent: HouseCode agent instance (for cache access)

    Returns:
        Formatted cache statistics
    """
    try:
        cache = agent.context.visual_cache
        stats = cache.stats()

        # Format output
        output = []
        output.append("Visual Memory Cache Statistics")
        output.append("=" * 60)
        output.append(f"  Entries: {stats['entries']} / {stats['max_entries']} max")
        output.append(f"  Size: {stats['size_mb']} MB / {stats['max_size_mb']} MB max")
        output.append(f"  Hit rate: {stats['hit_rate']}% ({stats['hits']} hits / {stats['misses']} misses)")
        output.append(f"  Evictions: {stats['evictions']}")
        output.append("")

        # Show cache keys if any
        keys = cache.keys()
        if len(keys) > 0:
            output.append(f"Cached entries ({len(keys)}):")
            for i, key in enumerate(keys[:10]):  # Show first 10
                output.append(f"  {i+1}. {key}")
            if len(keys) > 10:
                output.append(f"  ... and {len(keys) - 10} more")
        else:
            output.append("No entries in cache")

        output.append("=" * 60)

        # Add mode info
        mode = "MOCK" if agent.rosie_client.config.use_mock else "REAL"
        output.append(f"Mode: {mode}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Stats query failed: {e}")
        return f"Error: Failed to retrieve stats - {str(e)}"
