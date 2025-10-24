"""
Data models for visual memory compression.

These models represent the core data structures for converting conversation
history into visual tokens and back.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class VisualTokens:
    """
    Represents compressed visual tokens from DeepSeek-OCR.

    The tokens are the compressed representation of rendered conversation
    images, achieving 7-20x compression over raw text.
    """
    data: List[Any]  # Raw token data from DeepSeek-OCR
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __len__(self) -> int:
        """Return token count."""
        return len(self.data)


@dataclass
class RenderedImage:
    """
    Represents a rendered conversation image ready for compression.

    Images are 1024x1024 PNG files with embedded metadata for
    reconstruction.
    """
    image_bytes: bytes
    message_ids: List[str]  # IDs of messages in this image
    resolution: tuple[int, int] = (1024, 1024)
    format: str = "PNG"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def size_kb(self) -> float:
        """Return image size in KB."""
        return len(self.image_bytes) / 1024


@dataclass
class VisualMemory:
    """
    Complete visual memory entry linking original messages to visual tokens.

    This is what gets stored in ConversationContext.visual_cache.
    """
    message_ids: List[str]  # Original message IDs
    visual_tokens: VisualTokens  # Compressed representation
    original_text_length: int  # Original text length in chars
    compression_ratio: float  # Actual compression achieved
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def token_count(self) -> int:
        """Return visual token count."""
        return len(self.visual_tokens)

    @property
    def savings_estimate(self) -> int:
        """Estimate token savings (rough: original_chars / 4 - visual_tokens)."""
        return (self.original_text_length // 4) - self.token_count


@dataclass
class RenderConfig:
    """
    Configuration for text-to-image rendering.

    Optimized for DeepSeek-OCR's Base mode (1024x1024, 256 tokens).
    """
    resolution: tuple[int, int] = (1024, 1024)
    font_family: str = "JetBrains Mono"
    font_size: int = 11  # Fits ~90 lines in 1024x1024
    background_color: tuple[int, int, int] = (255, 255, 255)  # White
    text_color: tuple[int, int, int] = (0, 0, 0)  # Black
    line_spacing: int = 2  # Pixels between lines
    padding: int = 20  # Pixels from edge
    enable_syntax_highlighting: bool = True
    max_lines_per_image: int = 90  # ~90 lines fits in 1024x1024 @ 11pt

    @property
    def effective_width(self) -> int:
        """Width available for text after padding."""
        return self.resolution[0] - (2 * self.padding)

    @property
    def effective_height(self) -> int:
        """Height available for text after padding."""
        return self.resolution[1] - (2 * self.padding)


@dataclass
class CompressionStats:
    """
    Statistics about visual compression performance.

    Tracked in ConversationContext for monitoring.
    """
    total_compressions: int = 0
    total_decompressions: int = 0
    total_tokens_saved: int = 0
    average_compression_ratio: float = 0.0
    total_latency_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    last_compression_at: Optional[str] = None

    def update_compression(self, tokens_saved: int, compression_ratio: float, latency_ms: float):
        """Update stats after successful compression."""
        self.total_compressions += 1
        self.total_tokens_saved += tokens_saved
        self.total_latency_ms += latency_ms

        # Update rolling average
        n = self.total_compressions
        self.average_compression_ratio = (
            (self.average_compression_ratio * (n - 1) + compression_ratio) / n
        )

        self.last_compression_at = datetime.now().isoformat()

    def update_decompression(self, latency_ms: float, from_cache: bool):
        """Update stats after decompression."""
        self.total_decompressions += 1
        self.total_latency_ms += latency_ms

        if from_cache:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    @property
    def average_latency_ms(self) -> float:
        """Average latency per operation."""
        total_ops = self.total_compressions + self.total_decompressions
        if total_ops == 0:
            return 0.0
        return self.total_latency_ms / total_ops

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate as percentage."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100


@dataclass
class ArchivedImage:
    """
    Minimal POC: PNG archive of conversation for OCR reconstruction.

    This is a simplified model to test the image archival concept.
    Stores the rendered PNG bytes along with original text for accuracy comparison.
    """
    image_bytes: bytes
    message_ids: List[str]
    original_text: str  # Keep for accuracy comparison in POC
    format: str = "PNG"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def size_kb(self) -> float:
        """Return image size in KB."""
        return len(self.image_bytes) / 1024
