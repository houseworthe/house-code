"""
Banner display for House Code CLI.

Shows a clean 5-line banner on startup.
"""

from .progress import ProgressIndicator


def show_banner():
    """Display the House Code banner with optional colors."""

    # Check if terminal supports colors
    supports_color = ProgressIndicator.supports_color()

    if supports_color:
        # Color codes
        CYAN = ProgressIndicator.BLUE  # Using blue as cyan
        BLUE = ProgressIndicator.BLUE
        GREEN = ProgressIndicator.GREEN
        GRAY = ProgressIndicator.GRAY
        RESET = ProgressIndicator.RESET

        banner = f"""{CYAN}╔═══════════════════════════════════════════════════════════════════════╗{RESET}
{CYAN}║{RESET}                                                                       {CYAN}║{RESET}
{CYAN}║{RESET}                  {BLUE}HOUSE{RESET}  🏠  {GREEN}CODE{RESET}  {GRAY}-  AI Coding Assistant{RESET}              {CYAN}║{RESET}
{CYAN}║{RESET}                                                                       {CYAN}║{RESET}
{CYAN}╚═══════════════════════════════════════════════════════════════════════╝{RESET}"""
    else:
        # Plain version without colors
        banner = """╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║                  HOUSE  🏠  CODE  -  AI Coding Assistant              ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝"""

    print(banner)
    print()  # Extra newline for spacing
