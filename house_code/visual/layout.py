"""
Square layout engine for 1024x1024 image rendering.

Optimized for DeepSeek-OCR Base mode (1024x1024, 256 tokens).
Handles text wrapping, line breaking, and multi-page splitting.
"""

from typing import List, Tuple
from dataclasses import dataclass
from .models import RenderConfig


@dataclass
class Line:
    """Represents a single line of text in the layout."""
    text: str
    y_position: int
    is_code: bool = False
    language: str = ""


@dataclass
class Page:
    """Represents a single page (image) in the layout."""
    lines: List[Line]
    page_number: int
    total_pages: int


class SquareLayoutEngine:
    """
    Manages text layout in 1024x1024 square images.

    Handles:
    - Line wrapping at character boundaries
    - Multi-page splitting for long content
    - Preserving code block boundaries
    - Calculating optimal positioning
    """

    def __init__(self, config: RenderConfig):
        self.config = config
        self.max_chars_per_line = self._calculate_max_chars()

    def _calculate_max_chars(self) -> int:
        """
        Calculate maximum characters per line.

        For 1024px width with 11pt monospace:
        - Effective width: 1024 - (2 * 20) = 984px
        - 11pt monospace ≈ 7px per char
        - Max chars: 984 / 7 ≈ 140 chars

        Conservative: 120 chars to ensure no overflow.
        """
        char_width_estimate = 7  # pixels per char for 11pt monospace
        return self.config.effective_width // char_width_estimate - 10  # Safety margin

    def layout_text(self, text: str, message_ids: List[str]) -> List[Page]:
        """
        Convert text into pages of lines.

        Args:
            text: Raw conversation text to layout
            message_ids: Message IDs for metadata

        Returns:
            List of Page objects, each containing lines that fit in 1024x1024
        """
        # Split into lines first
        raw_lines = text.split('\n')

        # Wrap long lines
        wrapped_lines = []
        for line in raw_lines:
            if len(line) <= self.max_chars_per_line:
                wrapped_lines.append(line)
            else:
                # Wrap at character boundary
                wrapped_lines.extend(self._wrap_line(line))

        # Create pages
        return self._paginate(wrapped_lines, message_ids)

    def _wrap_line(self, line: str) -> List[str]:
        """
        Wrap a single long line into multiple lines.

        Preserves words where possible, but breaks at max_chars if needed.
        """
        if len(line) <= self.max_chars_per_line:
            return [line]

        wrapped = []
        current = ""

        words = line.split(' ')
        for word in words:
            # If word itself is too long, hard-break it
            if len(word) > self.max_chars_per_line:
                if current:
                    wrapped.append(current)
                    current = ""

                # Split long word into chunks
                for i in range(0, len(word), self.max_chars_per_line):
                    wrapped.append(word[i:i + self.max_chars_per_line])
                continue

            # Try adding word to current line
            test_line = f"{current} {word}".strip()
            if len(test_line) <= self.max_chars_per_line:
                current = test_line
            else:
                # Current line is full, start new line
                if current:
                    wrapped.append(current)
                current = word

        # Add remaining
        if current:
            wrapped.append(current)

        return wrapped

    def _paginate(self, lines: List[str], message_ids: List[str]) -> List[Page]:
        """
        Split lines into pages based on max_lines_per_image.

        Args:
            lines: All wrapped lines
            message_ids: Message IDs for metadata

        Returns:
            List of Page objects
        """
        max_lines = self.config.max_lines_per_image
        total_pages = (len(lines) + max_lines - 1) // max_lines  # Ceiling division

        pages = []
        for page_num in range(total_pages):
            start_idx = page_num * max_lines
            end_idx = min(start_idx + max_lines, len(lines))
            page_lines = lines[start_idx:end_idx]

            # Create Line objects with y positions
            line_objects = []
            y_position = self.config.padding

            for text in page_lines:
                # Detect if this is a code line (heuristic: starts with spaces/tabs or contains code markers)
                is_code = self._is_code_line(text)

                line_objects.append(Line(
                    text=text,
                    y_position=y_position,
                    is_code=is_code
                ))

                # Calculate next y position
                line_height = self.config.font_size + self.config.line_spacing
                y_position += line_height

            pages.append(Page(
                lines=line_objects,
                page_number=page_num + 1,
                total_pages=total_pages
            ))

        return pages

    def _is_code_line(self, text: str) -> bool:
        """
        Heuristic to detect if line is code.

        Code indicators:
        - Starts with spaces (indentation)
        - Starts with tabs
        - Contains common code symbols: {}, [], (), =>, ->, etc.
        - Starts with comment markers: //, #, /*
        """
        stripped = text.lstrip()
        has_indentation = len(text) > len(stripped)

        code_indicators = [
            '{', '}', '[', ']', '(', ')',
            '=>', '->', '===', '!==',
            '//', '/*', '#',
            'function', 'const', 'let', 'var',
            'def ', 'class ', 'import ', 'from ',
        ]

        has_code_symbols = any(indicator in text for indicator in code_indicators)

        return has_indentation or has_code_symbols

    def calculate_image_dimensions(self, num_lines: int) -> Tuple[int, int]:
        """
        Calculate required image dimensions for given number of lines.

        For now, always returns (1024, 1024) as we use fixed resolution.
        Future: Could support dynamic resolution based on content.
        """
        return self.config.resolution

    def estimate_pages_needed(self, text: str) -> int:
        """
        Estimate how many pages are needed for given text.

        Quick calculation without full layout.
        """
        lines = text.split('\n')

        # Account for wrapping (rough estimate)
        wrapped_lines = sum(
            max(1, len(line) // self.max_chars_per_line)
            for line in lines
        )

        return (wrapped_lines + self.config.max_lines_per_image - 1) // self.config.max_lines_per_image
