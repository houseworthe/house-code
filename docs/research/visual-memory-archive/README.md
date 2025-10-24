# Visual Memory Archive

**Status:** Research abandoned (architectural incompatibility)
**Date:** October 2025
**Hardware:** Google Colab Pro, A100 GPU (40GB VRAM)
**Verdict:** Vision tokens cannot be transferred between model families

---

## Why This Research Exists

House Code faced a critical problem: conversation context accumulates garbage and hits token limits around 150k tokens. We explored visual memory compression as a solution - render conversation history as images, use DeepSeek-OCR to compress to vision tokens, then have Claude read them.

**The hypothesis:** If DeepSeek-OCR can compress documents at 10x ratio, it should work for code conversations too.

**The result:** It doesn't. Vision tokens are model-specific and can't be transferred between DeepSeek and Claude. The forced text conversion results in 59% accuracy.

---

## What Was Built

### 1. PNG Rendering Pipeline ✅
**Status:** Working perfectly

A complete system for converting conversation text to OCR-optimized PNG images:

- **Renderer** (`visual/renderer.py`) - Converts text to images
  - Syntax highlighting via Pygments
  - JetBrains Mono font at 11pt
  - 1024px fixed width, variable height
  - RGB 8-bit PNG output

- **Layout Engine** (`visual/layout.py`) - Arranges text in images
  - Square layout optimizer (1024×1024 base)
  - Multi-page stitching for long conversations
  - Fixed: Now creates single tall PNGs (1024×H) instead of paginating

- **Highlighter** (`visual/highlighter.py`) - Syntax highlighting
  - Language detection
  - Theme support (monokai, github, etc.)
  - Inline code vs code blocks

- **Models** (`visual/models.py`) - Data structures
  - VisualToken (image + metadata)
  - CompressionStats (metrics tracking)
  - Configuration management

- **Cache** (`visual/cache.py`) - Persistent storage
  - Save/load visual tokens to disk
  - Token ID generation
  - Metadata tracking

**Result:** Can render any conversation to beautiful, OCR-optimized PNGs. This works and might be useful for other purposes (debugging, exports, documentation).

### 2. MCP Server Integration ✅
**Status:** Implemented but unused (OCR failed)

RunPod GPU server with DeepSeek-OCR via Model Context Protocol:

- **MCP Server** (`runpod_server/mcp_server.py`) - GPU inference endpoint
  - SSH stdio transport
  - Three tools: compress, decompress, health_check
  - A100 GPU deployment ready

- **Client Wrapper** (`visual/rosie_client.py`) - MCP client
  - Async compression/decompression
  - Error handling and retries
  - Mock mode for testing

- **Mock Mode** (`visual/mock.py`) - Local testing
  - Simulates compression without GPU
  - No actual OCR, just placeholder logic

**Result:** Architecture works, but OCR accuracy makes it unusable.

### 3. Testing Framework ✅
**Status:** Comprehensive tests completed

Proof-of-concept scripts and validation:

- **Long Conversation POC** (`poc_long_conversation.py`)
  - Generates 4,509 character Python code conversation
  - Fixed multi-page stitching bug (critical fix!)
  - Creates 1024×2048 test image

- **Archive OCR POC** (`poc_archive_ocr.py`)
  - Early OCR experiments
  - Image archival testing

- **Colab Notebooks** (`deepseek_ocr_test_*.ipynb`)
  - Test 1: Default "Free OCR" prompt (59% accuracy)
  - Test 2: Grounding mode (returned XML, unusable)
  - Test 3: Custom preservation prompt (59% accuracy)

**Result:** Proved OCR doesn't work on code. Research complete.

---

## How Testing Was Done

### Test Setup
1. Generated realistic Python code conversation (4,509 chars)
2. Rendered to OCR-optimized PNG (1024×2048)
3. Uploaded to Google Colab Pro (A100 GPU)
4. Ran DeepSeek-OCR with 3 different prompts
5. Compared output to input (character-by-character)

### Test Image
- **Location:** `test_images/poc_long_conversation.png`
- **Dimensions:** 1024×2048 pixels
- **Size:** 156.6 KB
- **Content:** Python file I/O code with indentation
- **Font:** JetBrains Mono 11pt with syntax highlighting

### GPU Configuration
- **Hardware:** Google Colab Pro with A100 (40GB VRAM)
- **Model:** `deepseek-ai/DeepSeek-OCR` (latest checkpoint)
- **Inference Time:** 40-90 seconds per image
- **Memory:** ~20-30GB VRAM required

---

## Why It Failed

### Root Cause: Architectural Incompatibility

**Vision tokens cannot be transferred between different model families.**

DeepSeek-OCR's compression only works within DeepSeek's own ecosystem. When using Claude as the inference model, we're forced to convert DeepSeek's vision tokens to plain text, which is where the accuracy loss occurs.

**The Architectural Gap:**
```
What Works (DeepSeek Paper):
PNG → Vision Tokens (stay compressed) → DeepSeek LLM → Response
      ↑_____ 10x compression, 97% accuracy _____↑

What We Need (Claude-Based System):
PNG → Vision Tokens → TEXT → Claude → Response
                      ↑
              59% accuracy loss
              (forced cross-model conversion)
```

**Key insight from our tests:** The `model.infer()` API returns plain text strings, not vision token embeddings. There's no way to extract, store, or transfer vision tokens between models. They're model-specific internal representations.

### Secondary Issues (Symptoms of Text Conversion)

These errors appear during the forced text conversion but aren't the root cause:

1. **Indentation stripping:** All leading whitespace removed (Python becomes invalid)
2. **Method name errors:** `endswith` → `endsWith` (camelCase hallucination)
3. **Token truncation:** `os.path.join` → `os.pth.join`
4. **Extension changes:** `.txt` → `.text`
5. **Training bias:** Model trained on documents, not code

**Critical point:** Even if we fixed all these error patterns, the architectural limitation remains. You cannot use one model's vision compression with a different model's LLM.

---

## Test Results Summary

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| OCR Accuracy | 59% | ≥90% | ❌ Failed |
| Indentation Preserved | No | Yes | ❌ Failed |
| Syntax Valid | No | Yes | ❌ Failed |
| Compression Ratio | 2.2x | 10x | ❌ Failed |
| Latency | 40-90s | <5s | ❌ Failed |

**Verdict:** Not viable for code compression.

---

## The Decision

### What We're Doing Instead
**Sticking with daemon cleaner agent (GC-only approach):**
- Prunes stale content automatically every 3 turns
- 100% accuracy (no reconstruction needed)
- <1s latency (instant pruning)
- Already working and reliable

### Why Not Keep Trying?
1. **Accuracy gap is too large:** 59% vs 90% isn't close
2. **Indentation loss is fundamental:** Not a prompting issue
3. **Better alternatives exist:** Summarization would give 5-10x with high accuracy
4. **Complexity doesn't justify benefit:** GC-only is simpler and works

---

## Lessons Learned

### What Worked
1. **Rendering pipeline** - Works perfectly, might be useful for:
   - Debugging visualizations
   - Conversation exports
   - Documentation generation
   - Screenshot sharing

2. **Multi-page stitching fix** - Critical bug found and fixed:
   - Original: Only saved first page (truncated content)
   - Fixed: Single tall PNG captures full conversation
   - Technique: Vertical stitching instead of pagination

3. **MCP architecture** - Clean separation of concerns:
   - Client-side rendering
   - Server-side inference
   - SSH stdio transport works well

### What Didn't Work
1. **OCR on code** - Fundamental limitation:
   - Model strips semantic whitespace
   - Not fixable with prompts
   - Need code-specific OCR models

2. **Compression claims** - Paper's 10x ratio didn't transfer:
   - Achieved only 2.2x in practice
   - Code has different characteristics than documents
   - Token savings negated by accuracy loss

3. **GPU latency** - 40-90s too slow:
   - Garbage collection needs to be instant
   - User shouldn't wait for compression
   - Better to use client-side pruning

---

## Future Possibilities

If someone wants to revisit this later:

### Alternative Approaches
1. **GPT-4 Vision / Claude Vision instead of OCR**
   - Better code understanding
   - Can preserve semantic structure
   - Might be accurate enough (test needed)

2. **Code-specific OCR training**
   - Fine-tune on GitHub code
   - Indentation-aware training
   - Syntax-preserving objectives

3. **Hybrid compression**
   - Summarize code blocks (Claude)
   - Render natural language as images (OCR)
   - Best of both worlds

4. **Non-code use cases**
   - Chat logs without syntax requirements
   - Natural language conversations
   - Documentation and markdown

### When to Reconsider
- New OCR models emerge with code training
- Vision models get cheaper (<$0.001 per image)
- Someone solves indentation preservation
- Use case shifts to non-code content

---

## Preserved Artifacts

### Source Code (All Working)
```
visual/
├── __init__.py          - Module exports
├── renderer.py          - PNG rendering with syntax highlighting
├── layout.py            - Layout engine (1024×H format)
├── highlighter.py       - Pygments integration
├── models.py            - Data structures
├── cache.py             - Persistent storage
├── config.py            - Configuration
├── rosie_client.py      - MCP client wrapper
└── mock.py              - Mock mode for testing
```

### Test Scripts
```
poc_long_conversation.py      - Multi-page stitching fix (working)
poc_archive_ocr.py           - Early OCR experiments
grounding_prompt_test.txt    - Prompt variations tested
```

### Test Results
```
deepseek_ocr_test_1.ipynb          - Default prompts (59% accuracy)
deepseek_ocr_test_2.ipynb          - Grounding mode (XML output)
deepseek_ocr_test_3_final.ipynb    - Custom prompts (59% accuracy)
test_images/poc_long_conversation.png - Test image (1024×2048)
```

### Documentation
```
VISUAL_MEMORY_PLAN.md              - Original implementation plan
../DEEPSEEK_OCR_CODE_RESEARCH.md   - Detailed research report
../VISUAL_RENDERING_VALIDATION.md  - Rendering tests (passed)
```

---

## Conclusion

Visual memory compression was a good idea worth testing, but **the fundamental limitation is architectural, not fixable.**

Vision tokens are model-specific internal representations that cannot be transferred between DeepSeek and Claude. The paper's 10x compression only works when the same model handles both compression and inference. Our hybrid approach (DeepSeek → Claude) requires converting vision tokens to text, which is where 59% accuracy loss occurs.

The rendering pipeline works beautifully and could be useful for other purposes. But the architectural incompatibility makes this approach unusable for Claude-based systems, regardless of any accuracy improvements we might make.

The daemon cleaner agent (3x compression, 100% accuracy, instant) is a better solution for House Code. All research materials are preserved here for future reference.

**Status:** Research complete. Approach abandoned due to architectural incompatibility. Artifacts archived.
