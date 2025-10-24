"""
Mock compression/decompression for visual memory testing.

Simulates DeepSeek-OCR behavior without requiring real model or GPU.
Provides deterministic compression for reproducible testing.
"""

import hashlib
import time
from typing import List, Tuple

from .models import VisualTokens


def mock_compress(
    image_bytes: bytes,
    target_ratio: float = 8.0,
    latency_ms: int = 100
) -> VisualTokens:
    """
    Mock compression of image to visual tokens.

    Simulates DeepSeek-OCR compression:
    - 256 visual tokens (Base mode: 1024x1024)
    - ~8x compression ratio
    - Deterministic output based on image hash
    - Simulated network latency

    Args:
        image_bytes: PNG image bytes to compress
        target_ratio: Target compression ratio (default: 8.0)
        latency_ms: Simulated latency in milliseconds (default: 100)

    Returns:
        VisualTokens with fake compressed data
    """
    # Simulate latency (network + inference)
    if latency_ms > 0:
        time.sleep(latency_ms / 1000.0)

    # Generate deterministic tokens from image hash
    image_hash = hashlib.sha256(image_bytes).hexdigest()

    # Create 256 fake tokens (8 chars each from hash)
    # Base mode: 1024x1024 = 256 tokens
    fake_tokens = _generate_fake_tokens(image_hash, num_tokens=256)

    # Calculate compression metrics
    image_size_kb = len(image_bytes) / 1024
    estimated_text_tokens = int(image_size_kb * 4 * target_ratio)  # Rough estimate

    return VisualTokens(
        data=fake_tokens,
        metadata={
            "model": "mock-deepseek-ocr",
            "mode": "base",
            "resolution": "1024x1024",
            "compression_ratio": target_ratio,
            "visual_token_count": 256,
            "estimated_text_tokens": estimated_text_tokens,
            "image_hash": image_hash[:16],  # First 16 chars for reference
        }
    )


def mock_decompress(tokens: VisualTokens) -> str:
    """
    Mock decompression of visual tokens.

    Since we can't truly decompress without the real model,
    return a placeholder that indicates the content was compressed.

    Args:
        tokens: Visual tokens to "decompress"

    Returns:
        Placeholder text indicating compression
    """
    metadata = tokens.metadata
    model = metadata.get("model", "unknown")
    ratio = metadata.get("compression_ratio", 0)
    token_count = len(tokens)

    # Return a marker that shows this was compressed
    return (
        f"[COMPRESSED VISUAL MEMORY]\n"
        f"Model: {model}\n"
        f"Visual Tokens: {token_count}\n"
        f"Compression Ratio: ~{ratio}x\n"
        f"Original content compressed into visual representation.\n"
        f"Decompression requires real DeepSeek-OCR model."
    )


def estimate_compression_ratio(
    text_length: int,
    visual_token_count: int = 256,
    chars_per_text_token: int = 4
) -> float:
    """
    Estimate compression ratio for given text.

    Args:
        text_length: Length of original text in characters
        visual_token_count: Number of visual tokens (default: 256)
        chars_per_text_token: Average chars per text token (default: 4)

    Returns:
        Estimated compression ratio (e.g., 8.0 for 8x compression)
    """
    if visual_token_count == 0:
        return 1.0

    estimated_text_tokens = text_length / chars_per_text_token
    ratio = estimated_text_tokens / visual_token_count

    return max(1.0, ratio)  # At least 1x


def generate_mock_visual_memory_stats() -> dict:
    """
    Generate mock statistics for visual memory compression.

    Useful for testing and demos.

    Returns:
        Dictionary with mock performance stats
    """
    return {
        "model": "mock-deepseek-ocr",
        "mode": "base",
        "resolution": "1024x1024",
        "visual_tokens_per_image": 256,
        "avg_compression_ratio": 8.0,
        "compression_range": (5.0, 15.0),
        "latency_ms": 100,
        "accuracy": "simulated",
        "cost_per_1k_tokens": 0.0,  # Mock is free
    }


def _generate_fake_tokens(seed: str, num_tokens: int) -> List[str]:
    """
    Generate deterministic fake tokens from seed.

    Args:
        seed: Seed string (e.g., image hash)
        num_tokens: Number of tokens to generate

    Returns:
        List of fake token strings
    """
    tokens = []

    # Use seed to generate deterministic tokens
    for i in range(num_tokens):
        # Hash seed with index to get unique but deterministic token
        token_seed = f"{seed}_{i}"
        token_hash = hashlib.sha256(token_seed.encode()).hexdigest()

        # Take first 8 chars as token (mimics compact token representation)
        token = token_hash[:8]
        tokens.append(token)

    return tokens


def validate_mock_tokens(tokens: VisualTokens) -> Tuple[bool, str]:
    """
    Validate that tokens appear to be from mock compression.

    Args:
        tokens: Visual tokens to validate

    Returns:
        Tuple of (is_valid, message)
    """
    metadata = tokens.metadata

    # Check for mock indicator
    model = metadata.get("model", "")
    if "mock" not in model:
        return False, "Tokens do not appear to be from mock compression"

    # Check token count
    if len(tokens) != 256:
        return False, f"Expected 256 tokens, got {len(tokens)}"

    # Check token format (should be hex strings)
    for token in tokens.data:
        if not isinstance(token, str):
            return False, f"Token is not a string: {type(token)}"
        if len(token) != 8:
            return False, f"Token has wrong length: {len(token)} (expected 8)"
        try:
            int(token, 16)  # Should be hex
        except ValueError:
            return False, f"Token is not valid hex: {token}"

    return True, "Tokens are valid mock compressed data"


def mock_compress_with_error(
    image_bytes: bytes,
    error_probability: float = 0.0
) -> VisualTokens:
    """
    Mock compression with simulated random errors.

    Useful for testing error handling.

    Args:
        image_bytes: Image to compress
        error_probability: Probability of error (0.0-1.0)

    Returns:
        VisualTokens

    Raises:
        RuntimeError: If simulated error occurs
    """
    import random

    if random.random() < error_probability:
        raise RuntimeError("Simulated compression error (mock)")

    return mock_compress(image_bytes)
