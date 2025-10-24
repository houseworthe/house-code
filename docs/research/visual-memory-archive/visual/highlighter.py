"""
Syntax highlighting for code in rendered images.

Uses Pygments for syntax highlighting with OCR-friendly color scheme.
High contrast, minimal colors for better OCR accuracy.
"""

from typing import Optional, Tuple
import re


class SyntaxHighlighter:
    """
    Provides syntax highlighting for code blocks.

    Uses simple, high-contrast color scheme optimized for OCR:
    - Keywords: Bold
    - Strings: Italic
    - Comments: Gray
    - Numbers: Keep black
    - Operators: Keep black

    Note: Full Pygments integration will come later. For now, we use
    simple heuristic-based highlighting that works without external deps.
    """

    # High-contrast OCR-friendly colors (RGB)
    COLORS = {
        'keyword': (0, 0, 139),      # Dark blue
        'string': (139, 0, 0),       # Dark red
        'comment': (128, 128, 128),  # Gray
        'number': (0, 0, 0),         # Black
        'default': (0, 0, 0),        # Black
    }

    # Common keywords across languages
    KEYWORDS = {
        'python': [
            'def', 'class', 'import', 'from', 'as', 'if', 'elif', 'else',
            'for', 'while', 'return', 'try', 'except', 'finally', 'with',
            'lambda', 'yield', 'async', 'await', 'raise', 'assert', 'pass',
            'break', 'continue', 'in', 'is', 'not', 'and', 'or', 'None',
            'True', 'False', 'self', 'cls',
        ],
        'javascript': [
            'function', 'const', 'let', 'var', 'if', 'else', 'for', 'while',
            'return', 'class', 'extends', 'import', 'export', 'default',
            'async', 'await', 'try', 'catch', 'finally', 'throw', 'new',
            'this', 'super', 'static', 'typeof', 'instanceof', 'true', 'false',
            'null', 'undefined',
        ],
        'typescript': [
            'function', 'const', 'let', 'var', 'if', 'else', 'for', 'while',
            'return', 'class', 'extends', 'import', 'export', 'default',
            'async', 'await', 'try', 'catch', 'finally', 'throw', 'new',
            'this', 'super', 'static', 'typeof', 'instanceof', 'interface',
            'type', 'enum', 'namespace', 'module', 'declare', 'public',
            'private', 'protected', 'readonly', 'abstract',
        ],
        'rust': [
            'fn', 'let', 'mut', 'const', 'static', 'if', 'else', 'match',
            'for', 'while', 'loop', 'return', 'struct', 'enum', 'impl',
            'trait', 'pub', 'use', 'mod', 'crate', 'self', 'super',
            'async', 'await', 'move', 'ref', 'true', 'false',
        ],
        'go': [
            'func', 'var', 'const', 'if', 'else', 'for', 'range', 'return',
            'struct', 'interface', 'type', 'package', 'import', 'defer',
            'go', 'chan', 'select', 'case', 'default', 'fallthrough',
            'true', 'false', 'nil',
        ],
    }

    def __init__(self):
        # Combine all keywords for generic detection
        self.all_keywords = set()
        for keywords in self.KEYWORDS.values():
            self.all_keywords.update(keywords)

    def detect_language(self, text: str) -> Optional[str]:
        """
        Detect programming language from code text.

        Returns language name or None if not detected.
        """
        # Language-specific patterns
        patterns = {
            'python': [r'def\s+\w+', r'import\s+\w+', r'from\s+\w+\s+import', r':\s*$'],
            'javascript': [r'function\s+\w+', r'const\s+\w+\s*=', r'=>', r'console\.log'],
            'typescript': [r'interface\s+\w+', r':\s*\w+\s*=', r'export\s+type'],
            'rust': [r'fn\s+\w+', r'let\s+mut', r'impl\s+\w+', r'::'],
            'go': [r'func\s+\w+', r'package\s+\w+', r':=', r'fmt\.Print'],
        }

        # Count pattern matches for each language
        scores = {}
        for lang, lang_patterns in patterns.items():
            score = sum(1 for pattern in lang_patterns if re.search(pattern, text, re.MULTILINE))
            if score > 0:
                scores[lang] = score

        # Return language with highest score
        if scores:
            return max(scores, key=scores.get)

        return None

    def highlight_line(self, line: str, language: Optional[str] = None) -> list[Tuple[str, Tuple[int, int, int]]]:
        """
        Apply syntax highlighting to a line of code.

        Returns list of (text, color) tuples for rendering.

        Args:
            line: Line of code to highlight
            language: Programming language (optional)

        Returns:
            List of (text_segment, rgb_color) tuples
        """
        if not line.strip():
            return [(line, self.COLORS['default'])]

        # Check if it's a comment
        stripped = line.lstrip()
        if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('/*'):
            return [(line, self.COLORS['comment'])]

        # Simple tokenization
        tokens = self._tokenize(line, language)
        return tokens

    def _tokenize(self, line: str, language: Optional[str]) -> list[Tuple[str, Tuple[int, int, int]]]:
        """
        Tokenize line into (text, color) segments.

        Simple regex-based approach for now.
        """
        result = []

        # String patterns (single and double quotes)
        string_pattern = r'(["\'])(?:(?=(\\?))\2.)*?\1'

        # Find all strings first
        strings = []
        for match in re.finditer(string_pattern, line):
            strings.append((match.start(), match.end(), match.group()))

        # Number pattern
        number_pattern = r'\b\d+\.?\d*\b'

        # Process line character by character
        i = 0
        current_token = ""
        current_color = self.COLORS['default']

        while i < len(line):
            # Check if we're in a string
            in_string = False
            for start, end, text in strings:
                if start <= i < end:
                    # We're in a string
                    if current_token:
                        result.append((current_token, current_color))
                        current_token = ""

                    result.append((text, self.COLORS['string']))
                    i = end
                    in_string = True
                    break

            if in_string:
                continue

            char = line[i]

            # Word boundary
            if char in ' \t()[]{},.;:=+-*/&|!<>':
                # Check if current_token is a keyword
                if current_token:
                    if current_token in self.all_keywords:
                        result.append((current_token, self.COLORS['keyword']))
                    elif re.match(r'\d+\.?\d*', current_token):
                        result.append((current_token, self.COLORS['number']))
                    else:
                        result.append((current_token, self.COLORS['default']))

                    current_token = ""

                # Add the separator
                result.append((char, self.COLORS['default']))
            else:
                current_token += char

            i += 1

        # Remaining token
        if current_token:
            if current_token in self.all_keywords:
                result.append((current_token, self.COLORS['keyword']))
            elif re.match(r'\d+\.?\d*', current_token):
                result.append((current_token, self.COLORS['number']))
            else:
                result.append((current_token, self.COLORS['default']))

        return result if result else [(line, self.COLORS['default'])]

    def should_highlight(self, text: str) -> bool:
        """
        Determine if text should be syntax highlighted.

        Returns True if text looks like code.
        """
        # Check for code indicators
        code_indicators = [
            r'def\s+\w+',
            r'function\s+\w+',
            r'class\s+\w+',
            r'import\s+\w+',
            r'fn\s+\w+',
            r'=>',
            r'{\s*$',
            r'}\s*$',
        ]

        return any(re.search(pattern, text, re.MULTILINE) for pattern in code_indicators)
