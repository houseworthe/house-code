# Phase 1 POC Findings: Image Archival for Context Window Compression

**Date**: October 24, 2025
**Status**: ✅ Phase 1 Complete - Ready for Phase 2 (OCR Testing)

---

## Critical Insight: We Were Measuring the Wrong Thing

### ❌ What I Initially Measured (WRONG)
- PNG file size vs text file size on disk
- "Compression ratio" based on bytes
- Concluded: PNG is 20x LARGER than text → doesn't work

### ✅ What Actually Matters (CORRECT)
**Goal: Save tokens in Claude's context window, not disk space**

The actual workflow:
```
Current State (No Compression):
Message 1-10: 2,500 text tokens in context
│
│ GC runs, compresses old messages
↓
With Visual Memory:
1. Render Messages 1-10 → PNG (store on disk)
2. Delete original text from context
3. When Claude needs that history:
   → Send PNG to Claude's vision API
   → Claude processes using ~256 vision tokens

Result: 2,500 text tokens → 256 vision tokens = 10x compression
```

**Disk size is irrelevant.** Disk is cheap ($0.10/GB). Context tokens are expensive ($3/million input tokens).

---

## Phase 1 Results

### ✅ What Works

**Test 1: Short Conversation (411 bytes)**
- Rendered: 1 image (1024×1024)
- PNG size: 22.5 KB
- File: `/tmp/poc_conversation.png`
- ✓ Rendering successful
- ✓ Code formatting preserved
- ✓ Human-readable

**Test 2: Long Conversation (4,509 bytes, ~1,127 text tokens)**
- Rendered: 2 images (1024×1024 each)
- PNG sizes: 88.9 KB + 65.8 KB
- File: `/tmp/poc_long_conversation.png`
- ✓ Multi-page rendering works
- ✓ Syntax highlighting visible
- ✓ Code blocks clear

### Token Savings Analysis (CORRECTED)

**Long Conversation Example**:
```
Original text:        1,127 text tokens
PNG (2 images):       512 vision tokens (256 × 2)
Token compression:    2.2x

Wait - this seems low? Expected 10x from DeepSeek-OCR paper.
```

**Question for Phase 2**: Why only 2.2x token compression?
- Paper claims: 10x compression
- Our result: 2.2x compression
- Hypothesis: Maybe need longer conversations (>50 lines)?

---

## DeepSeek-OCR Capabilities

From `external/deepseek-ocr/README.md`:

### Resolution Modes
- **Tiny**: 512×512 = 64 vision tokens
- **Small**: 640×640 = 100 vision tokens
- **Base**: 1024×1024 = **256 vision tokens** ← We're using this
- **Large**: 1280×1280 = 400 vision tokens
- **Gundam**: Dynamic (n×640×640 + 1×1024×1024)

### Prompts for Different Use Cases
```python
# Simple OCR (what we'll use)
"<image>\nFree OCR."

# Document with layout
"<image>\n<|grounding|>Convert the document to markdown."

# Code/figures
"<image>\n<|grounding|>OCR this image."
```

### Accuracy Claims
From paper (arxiv.org/abs/2510.18234):
- **General OCR**: 95-97% accuracy
- **Documents**: High accuracy with layout preservation
- **No specific code benchmarks found** ⚠️

**Key Unknown**: How well does it handle:
- Python/JavaScript code?
- Indentation?
- Syntax highlighting?
- Special characters (`, {}, [], <>)?

---

## Files Created

### Code
1. ✅ `house_code/visual/models.py` - Added `ArchivedImage` model
2. ✅ `house_code/visual/__init__.py` - Exported `ArchivedImage`
3. ✅ `tests/poc_archive_ocr.py` - Short conversation POC
4. ✅ `tests/poc_long_conversation.py` - Long conversation test

### Outputs
1. ✅ `/tmp/poc_conversation.png` - 22KB, simple test
2. ✅ `/tmp/poc_long_conversation.png` - 89KB, realistic code example

---

## Questions for Phase 2 (RunPod OCR Test)

### Critical Questions
1. **OCR Accuracy on Code**: Can DeepSeek-OCR accurately reconstruct:
   - Python function definitions?
   - Indentation (critical for Python)?
   - Code comments?
   - Special characters?

2. **Actual Token Compression**:
   - Why only 2.2x in our test vs 10x claimed?
   - Do we need longer conversations (100+ lines)?
   - Multi-page handling?

3. **Latency**:
   - Can we achieve <5s OCR reconstruction?
   - Acceptable for background GC operation?

### Test Plan for Phase 2
```python
# Deploy to RunPod
# Install DeepSeek-OCR
# Run OCR on /tmp/poc_long_conversation.png
# Measure:
# - Character-level accuracy (target: >90%)
# - Code accuracy (indentation, syntax)
# - Latency (target: <10s)
# - Compare to original text
```

---

## Phase 1 Success Criteria

| Criterion | Status | Notes |
|-----------|--------|-------|
| PNG renders correctly | ✅ PASS | Both images render cleanly |
| Code is visible | ✅ PASS | Syntax highlighting preserved |
| Multi-page support | ✅ PASS | 2-page render works |
| File size reasonable | ✅ PASS | ~90KB per page acceptable |
| Ready for OCR testing | ✅ PASS | PNGs saved to /tmp/ |

---

## Next Steps

### Immediate (Phase 2)
1. Deploy RunPod pod (RTX 4090, PyTorch 2.8.0)
2. Install DeepSeek-OCR via setup script
3. Copy `/tmp/poc_long_conversation.png` to RunPod
4. Run OCR accuracy test
5. Measure:
   - Character accuracy (difflib comparison)
   - Code indentation accuracy
   - Special character handling
   - Latency

### If Phase 2 Succeeds (≥90% accuracy)
1. Rewrite MCP server (`runpod_server/mcp_server.py`)
   - Replace `compress_visual_tokens` with `ocr_reconstruct_text`
2. Update client (`house_code/visual/rosie_client.py`)
   - `archive_image()` - stores PNG
   - `reconstruct_text()` - calls OCR
3. Update GC integration
4. Comprehensive tests

### If Phase 2 Fails (<90% accuracy)
**Iterate on rendering**:
- Try different fonts (DejaVu, Courier)
- Adjust font size (12pt, 14pt)
- Disable syntax highlighting (might confuse OCR)
- Test grayscale vs color

**Or pivot to alternatives**:
- Option B: Hybrid (PNG + embeddings)
- Option C: Pure summarization
- Option D: Skip visual compression

---

## Key Takeaways

1. ✅ **PNG rendering works perfectly**
2. ✅ **Multi-page support confirmed**
3. ⚠️ **Token compression unclear** (2.2x vs 10x claimed)
4. ❓ **OCR accuracy on code unknown** (Phase 2 needed)
5. 💡 **Disk size doesn't matter** (optimizing for context tokens, not storage)

---

## Resources

- **DeepSeek-OCR Paper**: `external/deepseek-ocr/DeepSeek_OCR_paper.pdf`
- **GitHub**: https://github.com/deepseek-ai/DeepSeek-OCR
- **Model**: `deepseek-ai/DeepSeek-OCR` on HuggingFace
- **Arxiv**: https://arxiv.org/abs/2510.18234
