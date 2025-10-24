# House Code

![House Code Demo](demo.png)

Work in progress. Use at your own risk.

## Quick Start (Claude Code)

Want to check this out? Paste this into Claude Code:

```
Clone the house-code repo, set up a Python virtual environment, install dependencies,
and run `house` in interactive mode so I can see the banner and try it out.
```

## Problems We're Solving

**1. Context pollution**
Claude Code reads the same files multiple times, keeps old todo lists, accumulates errors. After 50 turns your context is full of garbage. It doesn't clean up after itself.

**2. Token limits kill long sessions**
Hit 150k tokens and Claude Code just dies. You lose all your early context or the conversation becomes useless.

## Innovations

**1. Daemon Cleaner Agent**
Every 3 turns, Claude analyzes its own conversation history and prunes stale content. Superseded file reads, completed todos, old errors - gone. Uses Claude to clean Claude's context. See `house_code/core.py:389`.

**2. Visual Memory (planned)**
Compress conversation history into images, process with [DeepSeek-OCR](https://github.com/deepseek-ai/DeepSeek-VL2) for 10x token reduction. Offload heavy inference to Rosie supercomputer via MCP. See `VISUAL_MEMORY_PLAN.md`

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
