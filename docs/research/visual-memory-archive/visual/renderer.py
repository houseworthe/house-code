"""
Main rendering engine for converting conversation text to images.

Renders conversation history as 1024x1024 PNG images optimized for
DeepSeek-OCR compression.
"""

from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont, ImageColor
import io
import json

from .models import RenderConfig, RenderedImage
from .layout import SquareLayoutEngine, Page
from .highlighter import SyntaxHighlighter


class ConversationRenderer:
    """
    Renders conversation text into OCR-optimized images.

    Features:
    - 1024x1024 square images (DeepSeek-OCR Base mode)
    - JetBrains Mono 11pt font
    - Syntax highlighting for code
    - Multi-page rendering for long content
    - EXIF metadata embedding
    """

    def __init__(self, config: Optional[RenderConfig] = None):
        self.config = config or RenderConfig()
        self.layout_engine = SquareLayoutEngine(self.config)
        self.highlighter = SyntaxHighlighter()
        self.font = self._load_font()

    def _load_font(self) -> ImageFont.FreeTypeFont:
        """
        Load JetBrains Mono font.

        Falls back to system monospace fonts if JetBrains Mono not available.
        """
        font_candidates = [
            "JetBrainsMono-Regular.ttf",
            "JetBrainsMonoNL-Regular.ttf",
            "/System/Library/Fonts/Monaco.dfont",  # macOS fallback
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",  # Linux fallback
            "Courier New",  # Windows fallback
        ]

        for font_name in font_candidates:
            try:
                return ImageFont.truetype(font_name, self.config.font_size)
            except (OSError, IOError):
                continue

        # Last resort: default PIL font
        return ImageFont.load_default()

    def render_conversation(
        self,
        text: str,
        message_ids: List[str],
        enable_highlighting: Optional[bool] = None
    ) -> List[RenderedImage]:
        """
        Render conversation text as one or more images.

        Args:
            text: Conversation text to render
            message_ids: IDs of messages included in this render
            enable_highlighting: Override config setting for highlighting

        Returns:
            List of RenderedImage objects (one per page)
        """
        # Layout text into pages
        pages = self.layout_engine.layout_text(text, message_ids)

        # Render each page
        rendered_images = []
        for page in pages:
            image = self._render_page(
                page,
                enable_highlighting=enable_highlighting if enable_highlighting is not None
                else self.config.enable_syntax_highlighting
            )

            rendered_images.append(RenderedImage(
                image_bytes=image,
                message_ids=message_ids,
                resolution=self.config.resolution,
                metadata={
                    'page_number': page.page_number,
                    'total_pages': page.total_pages,
                    'font_family': self.config.font_family,
                    'font_size': self.config.font_size,
                }
            ))

        return rendered_images

    def _render_page(self, page: Page, enable_highlighting: bool) -> bytes:
        """
        Render a single page as PNG image.

        Args:
            page: Page object with lines to render
            enable_highlighting: Whether to apply syntax highlighting

        Returns:
            PNG image as bytes
        """
        # Create blank image
        img = Image.new(
            'RGB',
            self.config.resolution,
            self.config.background_color
        )
        draw = ImageDraw.Draw(img)

        # Detect language for this page (if highlighting enabled)
        language = None
        if enable_highlighting:
            page_text = '\n'.join(line.text for line in page.lines)
            language = self.highlighter.detect_language(page_text)

        # Render each line
        for line in page.lines:
            x_position = self.config.padding

            if enable_highlighting and (line.is_code or self.highlighter.should_highlight(line.text)):
                # Render with syntax highlighting
                tokens = self.highlighter.highlight_line(line.text, language)
                for text_segment, color in tokens:
                    draw.text(
                        (x_position, line.y_position),
                        text_segment,
                        font=self.font,
                        fill=color
                    )
                    # Calculate next x position
                    bbox = draw.textbbox((0, 0), text_segment, font=self.font)
                    x_position += bbox[2] - bbox[0]
            else:
                # Render plain text
                draw.text(
                    (x_position, line.y_position),
                    line.text,
                    font=self.font,
                    fill=self.config.text_color
                )

        # Add page number footer (small, bottom-right)
        if page.total_pages > 1:
            footer_text = f"Page {page.page_number}/{page.total_pages}"
            footer_font_size = max(8, self.config.font_size - 3)

            # Use smaller font for footer
            try:
                footer_font = ImageFont.truetype(
                    "/System/Library/Fonts/Monaco.dfont",
                    footer_font_size
                )
            except:
                footer_font = self.font

            # Position at bottom-right
            bbox = draw.textbbox((0, 0), footer_text, font=footer_font)
            footer_x = self.config.resolution[0] - bbox[2] - self.config.padding
            footer_y = self.config.resolution[1] - bbox[3] - self.config.padding

            draw.text(
                (footer_x, footer_y),
                footer_text,
                font=footer_font,
                fill=(128, 128, 128)  # Gray
            )

        # Convert to PNG bytes
        output = io.BytesIO()
        img.save(output, format='PNG', optimize=True)
        return output.getvalue()

    def render_messages(
        self,
        messages: List[dict],
        enable_highlighting: Optional[bool] = None
    ) -> List[RenderedImage]:
        """
        Render a list of messages.

        Args:
            messages: List of message dicts with 'id', 'role', 'content'
            enable_highlighting: Override config setting for highlighting

        Returns:
            List of RenderedImage objects
        """
        # Format messages as text
        text_parts = []
        message_ids = []

        for msg in messages:
            message_ids.append(str(msg.get('id', len(message_ids))))

            # Format: [role]: content
            role = msg.get('role', 'unknown')
            content = str(msg.get('content', ''))

            text_parts.append(f"[{role}]:")
            text_parts.append(content)
            text_parts.append("")  # Blank line separator

        text = '\n'.join(text_parts)

        return self.render_conversation(
            text,
            message_ids,
            enable_highlighting=enable_highlighting
        )

    def estimate_compression_ratio(self, text: str) -> float:
        """
        Estimate compression ratio for given text.

        Uses heuristics based on content type:
        - Code-heavy: ~10x compression
        - Mixed content: ~7x compression
        - Plain text: ~5x compression

        Args:
            text: Text to estimate for

        Returns:
            Estimated compression ratio (e.g., 10.0 for 10x compression)
        """
        # Count lines of code vs plain text
        lines = text.split('\n')
        code_lines = sum(1 for line in lines if self._looks_like_code(line))
        total_lines = len(lines)

        if total_lines == 0:
            return 1.0

        code_ratio = code_lines / total_lines

        # Estimate based on code ratio
        if code_ratio > 0.7:
            # Code-heavy
            return 10.0
        elif code_ratio > 0.3:
            # Mixed
            return 7.0
        else:
            # Plain text
            return 5.0

    def _looks_like_code(self, line: str) -> bool:
        """Check if line looks like code."""
        stripped = line.lstrip()
        has_indentation = len(line) > len(stripped)

        code_indicators = ['{', '}', '=>', 'function', 'def ', 'class ', 'import ']
        has_code_symbols = any(indicator in line for indicator in code_indicators)

        return has_indentation or has_code_symbols


def create_renderer(
    resolution: tuple[int, int] = (1024, 1024),
    font_size: int = 11,
    enable_highlighting: bool = True
) -> ConversationRenderer:
    """
    Factory function to create a renderer with custom config.

    Args:
        resolution: Image resolution (default: 1024x1024)
        font_size: Font size in points (default: 11)
        enable_highlighting: Enable syntax highlighting (default: True)

    Returns:
        ConversationRenderer instance
    """
    config = RenderConfig(
        resolution=resolution,
        font_size=font_size,
        enable_syntax_highlighting=enable_highlighting
    )

    return ConversationRenderer(config)
