# House Code

![House Code Demo](demo.png)

Work in progress. Use at your own risk.

## Quick Start (Claude Code)

Want to check this out? Paste this into Claude Code:

```
Clone the house-code repo, set up a Python virtual environment, install dependencies,
and give me the next steps so I can try it out.
```

## Problems We're Solving

**1. Context pollution**
Claude Code reads the same files multiple times, keeps old todo lists, accumulates errors. After 50 turns your context is full of garbage. It doesn't clean up after itself.

**2. Token limits kill long sessions**
Hit 150k tokens and Claude Code just dies. You lose all your early context or the conversation becomes useless.

## Innovation

**Daemon Cleaner Agent**
Every 3 turns, Claude analyzes its own conversation history and prunes stale content. Superseded file reads, completed todos, old errors - gone. Uses Claude to clean Claude's context. Keeps conversations lean without manual intervention. See `house_code/core.py:389`.

*Note: We explored visual memory compression via DeepSeek-OCR but found it unsuitable for code (59% accuracy, indentation stripping). Research archived in `docs/research/visual-memory-archive/`.*

## Setup

```bash
# Clone the repo
git clone https://github.com/ethanhouseworth/house-code.git
cd house-code

# Set up Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Set your API key
export ANTHROPIC_API_KEY="your-key-here"

# Run it
house
```
