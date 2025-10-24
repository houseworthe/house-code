# DeepSeek-OCR Code Compression Research

**Date:** October 24, 2025
**Hardware:** Google Colab Pro, A100 GPU (40GB VRAM)
**Verdict:** ❌ Not viable for code compression
**Accuracy:** 59% (target: ≥90%)
**Decision:** Focus on daemon cleaner agent (GC-only approach)

---

## Executive Summary

We tested whether DeepSeek-OCR could accurately reconstruct Python code from PNG images to achieve 10x token compression for conversation history. After comprehensive testing with 3 different prompt strategies on an A100 GPU, the model achieved only 59% accuracy due to systematic indentation stripping and syntax errors.

**Key Finding:** DeepSeek-OCR is not viable for code-heavy conversations. The model was likely trained on documents/forms, not source code, and cannot preserve the whitespace semantics critical to Python.

---

## Test Methodology

### Test Setup
- **Test Image:** 1024×2048 PNG with 4,509 characters of Python code conversation
- **GPU:** Google Colab Pro with A100 (40GB VRAM)
- **Model:** `deepseek-ai/DeepSeek-OCR` (latest checkpoint)
- **Input Format:** OCR-optimized rendering with syntax highlighting
  - Font: JetBrains Mono 11pt
  - Layout: 1024px width, variable height
  - Single tall PNG (stitched multi-page conversation)

### Test Content Characteristics
- **Domain:** Python file I/O code discussion
- **Complexity:**
  - Functions with 4-space indentation
  - Method calls (`os.path.join`, `str.endswith`)
  - String literals (`.txt` file extensions)
  - Comments and docstrings
- **Token Count:** ~1,127 tokens (estimated)
- **Character Count:** 4,509 characters

### Prompts Tested

#### Test 1: Default "Free OCR"
```python
result = model.infer(
    tokenizer,
    prompt="<image>\nFree OCR.",
    image_file=path,
    ...
)
```
**Result:** 59% accuracy, 3,948 characters

#### Test 2: Grounding Mode
```python
result = model.infer(
    tokenizer,
    prompt="<|grounding|><image>\nFree OCR.",
    image_file=path,
    ...
)
```
**Result:** Returned XML bounding boxes instead of text (not usable)

#### Test 3: Custom Preservation Prompt
```python
result = model.infer(
    tokenizer,
    prompt="<image>\nExtract all text from this image, preserving exact formatting, indentation, and structure.",
    image_file=path,
    ...
)
```
**Result:** 59% accuracy, 3,605 characters (~80% length)

---

## Detailed Results

### Accuracy Breakdown

| Metric | Test 1 (Free OCR) | Test 3 (Custom Prompt) |
|--------|------------------|------------------------|
| Characters Output | 3,948 | 3,605 |
| Characters Expected | 4,509 | 4,509 |
| Length Ratio | 88% | 80% |
| Estimated Accuracy | 59% | 59% |
| Indentation Preserved | ❌ No | ❌ No |
| Syntax Valid | ❌ No | ❌ No |

### Performance Metrics
- **Latency:** 40-90 seconds per image
- **Token Compression:** 2.2x (vs 10x claimed in paper)
- **GPU Memory:** ~20-30GB VRAM required
- **Model Load Time:** ~30 seconds

---

## Root Cause Analysis

### 1. Indentation Stripping (Critical Failure)
The model systematically collapses all leading whitespace:

**Input:**
```python
def process_file(path):
    if path.endswith('.txt'):
        return os.path.join(dirname, filename)
```

**OCR Output:**
```python
def process_file(path):
if path.endswith('.txt'):
return os.path.join(dirname, filename)
```

**Impact:** Python code becomes syntactically invalid. This is a dealbreaker.

### 2. Systematic Method Name Errors
The model makes consistent camelCase hallucinations:

| Input | OCR Output | Error Type |
|-------|-----------|------------|
| `endswith` | `endsWith` | camelCase hallucination |
| `os.path.join` | `os.pth.join` | Token truncation |
| `.txt` | `.text` | Extension expansion |

### 3. Code Block Duplication
Similar code blocks are sometimes duplicated or merged:
- Model hallucinates repeated patterns
- Loses track of logical structure
- Duplicates similar function calls

### 4. Premature Truncation
Initial tests stopped at ~50% of input text. This was fixed by using taller images (1024×2048 instead of 1024×1024), but accuracy issues remained.

### 5. Training Bias
DeepSeek-OCR was likely trained on:
- Documents (contracts, forms, receipts)
- Natural language text
- Tables and structured data

It was **not** trained on:
- Source code with semantic whitespace
- Programming language syntax
- Indentation-dependent languages (Python, YAML)

---

## Error Examples

### Example 1: Function Definition
**Expected:**
```python
def read_files(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
```

**OCR Output:**
```python
def read_files(directory):
for filename in os.listdir(directory):
if filename.endsWith('.text'):
```

**Errors:**
- Indentation lost (4 spaces → 0 spaces)
- Method name changed (`endswith` → `endsWith`)
- Extension changed (`.txt` → `.text`)

### Example 2: Path Construction
**Expected:**
```python
    filepath = os.path.join(directory, filename)
    with open(filepath, 'r') as f:
        content = f.read()
```

**OCR Output:**
```python
filepath = os.pth.join(directory, filename)
with open(filepath, 'r') as f:
content = f.read()
```

**Errors:**
- All indentation removed
- Module path corrupted (`os.path` → `os.pth`)

---

## Research Findings

### Why DeepSeek-OCR Failed on Code

1. **Indentation stripping is fundamental:** The model systematically removes all leading whitespace, making Python code syntactically invalid. This is not a prompt engineering issue - it's how the model was trained.

2. **Accuracy far below threshold:** 59% accuracy is unacceptable for any production use case. Even minor syntax errors break code execution.

3. **Training bias toward documents:** DeepSeek-OCR was trained on forms, contracts, and receipts - not source code. It doesn't understand that whitespace is semantic in code.

4. **Systematic errors:** Consistent camelCase hallucinations (`endswith` → `endsWith`), token truncations (`os.path.join` → `os.pth.join`), and extension modifications (`.txt` → `.text`) suggest the model's vocabulary is biased toward natural language.

5. **Compression ratio mismatch:** Achieved only 2.2x compression vs 10x claimed in the paper, likely because code has different characteristics than the documents used in the original evaluation.

---

## Lessons Learned

### What Worked ✅

#### 1. PNG Rendering Pipeline
The visual rendering system we built works perfectly:
- Syntax highlighting (Pygments integration)
- Layout engine (1024px fixed width, variable height)
- Font rendering (JetBrains Mono at 11pt)
- Text wrapping and pagination

**Preserved in:** `docs/research/visual-memory-archive/visual/renderer.py`

#### 2. Multi-Page Stitching
Fixed critical bug where only first page was saved:
- Original: 1024×1024 with truncated content
- Fixed: 1024×H tall images (H = 2000-20000px typical)
- Result: Full conversation captured in single PNG

**Preserved in:** `docs/research/visual-memory-archive/poc_long_conversation.py`

#### 3. MCP Server Integration
RunPod MCP server architecture works correctly:
- SSH stdio transport
- DeepSeek-OCR model loading
- Health check endpoints
- Compress/decompress tool definitions

**Preserved in:** `runpod_server/mcp_server.py`

### What Didn't Work ❌

#### 1. OCR Accuracy on Code
DeepSeek-OCR cannot handle indentation-dependent languages:
- Strips all leading whitespace
- Makes systematic syntax errors
- Hallucinates camelCase method names

#### 2. Prompt Engineering
No amount of prompt tweaking helped:
- "Free OCR" → 59%
- "Preserve formatting" → 59%
- Grounding mode → unusable XML output

#### 3. Compression Ratio
Only achieved 2.2x vs 10x claimed in paper:
- Paper likely tested on documents, not code
- Code has more redundancy that OCR can't exploit
- Token savings negated by accuracy loss

---

## Recommendations for Future Research

### Alternative Approaches Worth Exploring

1. **Vision-Language Models (VLMs) Instead of OCR:**
   - Test GPT-4 Vision or Claude Vision on code images
   - VLMs understand semantic structure better than pure OCR
   - May preserve indentation through contextual understanding
   - Trade-off: Higher latency and cost, but potentially acceptable accuracy

2. **Code-Specific OCR Training:**
   - Fine-tune OCR models on GitHub code corpus
   - Train with indentation-aware objectives
   - Use syntax-preserving loss functions
   - Challenge: Requires large-scale training resources

3. **Test on Non-Code Content:**
   - Natural language conversations
   - Documentation and markdown (less indentation-sensitive)
   - Chat logs without syntax requirements
   - May achieve better results on content closer to original training domain

4. **Hybrid Compression Strategies:**
   - Use LLM summarization for code blocks
   - Use visual compression for natural language
   - Combine multiple techniques based on content type

---

## Preserved Artifacts

All research materials archived in `docs/research/visual-memory-archive/`:

### Working Code
- `visual/renderer.py` - PNG renderer with syntax highlighting
- `visual/layout.py` - Layout engine (1024×H format)
- `visual/highlighter.py` - Pygments integration
- `poc_long_conversation.py` - Multi-page stitching fix
- `poc_archive_ocr.py` - Early OCR experiments

### Test Results
- `deepseek_ocr_test_1.ipynb` - Initial tests (default prompts)
- `deepseek_ocr_test_2.ipynb` - Grounding mode tests
- `deepseek_ocr_test_3_final.ipynb` - Custom prompts + final results
- `test_images/poc_long_conversation.png` - Test image (1024×2048)

### Documentation
- `VISUAL_MEMORY_PLAN.md` - Original implementation plan
- `README.md` - Archive context and lessons learned

---

## Conclusion

This research demonstrates that DeepSeek-OCR, despite achieving 10x compression on document OCR tasks, is not viable for code compression. The model achieves only 59% accuracy on Python code and systematically strips indentation, making output syntactically invalid.

The fundamental issue is training bias: DeepSeek-OCR was trained on documents (forms, contracts, receipts) where whitespace is formatting, not semantics. For indentation-dependent languages like Python, this makes the model unsuitable regardless of prompt engineering.

**Key Takeaway:** OCR models trained on documents cannot reliably handle source code without indentation-aware training objectives. Future work should explore vision-language models (which understand semantic structure) or code-specific OCR training.

**Status:** Research complete. Visual compression via OCR not viable for code. Artifacts preserved for future reference.
