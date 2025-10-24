"""
Visual memory module for House Code.

Provides conversation history compression using DeepSeek-OCR visual tokens.

Main components:
- ConversationRenderer: Convert text to OCR-optimized images
- Models: Data structures for visual tokens and memory
- Layout: Square layout engine for 1024x1024 images
- Highlighter: Syntax highlighting for code

Example usage:
    from house_code.visual import create_renderer

    renderer = create_renderer()
    images = renderer.render_conversation(text, message_ids)

    # Later, with Rosie integration:
    from house_code.visual import RosieClient
    client = RosieClient()
    visual_tokens = client.compress(images[0].image_bytes)
"""

from .models import (
    VisualTokens,
    RenderedImage,
    VisualMemory,
    RenderConfig,
    CompressionStats,
)

from .renderer import (
    ConversationRenderer,
    create_renderer,
)

from .layout import (
    SquareLayoutEngine,
    Line,
    Page,
)

from .highlighter import (
    SyntaxHighlighter,
)

from .config import (
    VisualMemoryConfig,
    load_config,
    save_config,
    get_default_config,
    update_config,
    reset_config,
)

from .mock import (
    mock_compress,
    mock_decompress,
    estimate_compression_ratio,
    validate_mock_tokens,
)

from .cache import (
    VisualCache,
)

from .rosie_client import (
    RosieClient,
)


__all__ = [
    # Models
    'VisualTokens',
    'RenderedImage',
    'VisualMemory',
    'RenderConfig',
    'CompressionStats',

    # Renderer
    'ConversationRenderer',
    'create_renderer',

    # Layout
    'SquareLayoutEngine',
    'Line',
    'Page',

    # Highlighter
    'SyntaxHighlighter',

    # Config (Phase 4)
    'VisualMemoryConfig',
    'load_config',
    'save_config',
    'get_default_config',
    'update_config',
    'reset_config',

    # Mock (Phase 4)
    'mock_compress',
    'mock_decompress',
    'estimate_compression_ratio',
    'validate_mock_tokens',

    # Cache (Phase 4)
    'VisualCache',

    # Client (Phase 4)
    'RosieClient',
]

__version__ = '0.1.0'
