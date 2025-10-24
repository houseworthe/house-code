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
]

__version__ = '0.1.0'
