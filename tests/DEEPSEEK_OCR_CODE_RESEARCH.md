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

### The Fundamental Limitation: Architectural Incompatibility

**The core issue is not fixable through prompt engineering or rendering improvements.**

#### What We Actually Tested
```
Text → PNG → DeepSeek-OCR model.infer() → Plain Text String → Claude
                                          ↑
                                   LOSSY CONVERSION (59% accuracy)
```

**Key insight from code analysis** (`deepseek_ocr_test_1.ipynb` cell 10):
```python
result = model.infer(
    tokenizer,
    prompt="<image>\nFree OCR.",
    image_file='/content/test_image.png',
    ...
)
# result is a plain text STRING, not vision token embeddings
```

#### Why This Architecture Fails

1. **Vision tokens are model-specific internal representations**
   - Created by DeepSeek's vision encoder
   - Only consumable by DeepSeek's LLM decoder
   - Not accessible via API (no extraction or injection endpoints)
   - Can't be transferred to Claude

2. **The paper's approach only works within DeepSeek's ecosystem**
   - Same model compresses and decompresses
   - Vision tokens stay internal, never converted to text
   - No accuracy loss from OCR conversion
   - Claude can't consume DeepSeek's vision tokens

3. **Our hybrid approach requires text conversion**
   - DeepSeek must convert vision tokens → text
   - Claude only accepts text input (or its own vision tokens)
   - This conversion is where 59% accuracy comes from
   - No way to "store vision tokens" and use them with Claude later

#### Why 59% Accuracy Occurs

**The model.infer() API returns decoded text, not compressed representations.** This means:
- Vision tokens are created internally
- LLM decoder generates text output
- We measure accuracy on the text output
- The compression benefit is lost when converting to text for Claude

**This is fundamentally different from the paper's approach:**
- Paper: Vision tokens stay compressed in context
- Our test: Vision tokens → text (decompression happens immediately)

### Secondary Issues: Observed Error Patterns

These are **symptoms of the text conversion**, not the root cause:

#### 1. Indentation Stripping
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

**Impact:** Python code becomes syntactically invalid.

#### 2. Systematic Method Name Errors
The model makes consistent camelCase hallucinations:

| Input | OCR Output | Error Type |
|-------|-----------|------------|
| `endswith` | `endsWith` | camelCase hallucination |
| `os.path.join` | `os.pth.join` | Token truncation |
| `.txt` | `.text` | Extension expansion |

#### 3. Code Block Duplication
Similar code blocks are sometimes duplicated or merged:
- Model hallucinates repeated patterns
- Loses track of logical structure
- Duplicates similar function calls

#### 4. Training Bias
DeepSeek-OCR was likely trained on:
- Documents (contracts, forms, receipts)
- Natural language text
- Tables and structured data

It was **not** trained on:
- Source code with semantic whitespace
- Programming language syntax
- Indentation-dependent languages (Python, YAML)

**Note:** Even if these error patterns were fixed, the architectural limitation remains. Vision tokens cannot be transferred between models.

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

### Why DeepSeek-OCR's Approach Doesn't Work for Claude-Based Systems

#### The Fundamental Architectural Limitation

**Vision tokens cannot be transferred between different model families.**

1. **Vision tokens are model-specific internal representations**
   - DeepSeek's vision encoder creates embeddings only DeepSeek's LLM can interpret
   - Claude cannot consume DeepSeek's vision tokens (and vice versa)
   - No API exists to extract, store, or inject raw vision token embeddings
   - The only output from DeepSeek-OCR is decoded plain text

2. **The paper's 10x compression only works within DeepSeek's ecosystem**
   - **Their approach:** Vision tokens stay compressed in DeepSeek's context window
   - **Our requirement:** Convert DeepSeek output → text → send to Claude
   - **The gap:** Text conversion is where 59% accuracy comes from

3. **Our architecture requires lossy conversion**
   ```
   DeepSeek Paper (works):
   PNG → Vision Tokens (stay compressed) → DeepSeek LLM → Response

   Our Test (fails):
   PNG → Vision Tokens → TEXT (59% loss) → Claude → Response
                         ↑
                    FORCED CONVERSION
   ```

4. **No way to "defer" the conversion**
   - We tested: Store PNG, decompress on-demand via DeepSeek API
   - Problem: DeepSeek API returns text, not vision tokens
   - Result: Still 59% accuracy, just delayed
   - Vision tokens never leave DeepSeek's internal memory

#### Why 59% Accuracy Occurs

**Not primarily an OCR quality issue** - it's an architectural mismatch:
- The paper achieves 97% at 10x compression **within DeepSeek's own models**
- We achieve 59% because we're **forcing a cross-model conversion**
- The model.infer() API immediately decodes vision tokens to text
- This text must then be sent to Claude (which can't read DeepSeek's vision tokens)

#### Secondary Issues: Code-Specific Errors

These symptoms appear during the forced text conversion:

1. **Training bias toward documents:** DeepSeek-OCR was trained on forms, contracts, and receipts - not source code. It doesn't understand that whitespace is semantic in code.

2. **Indentation stripping:** The model systematically removes all leading whitespace, making Python code syntactically invalid.

3. **Systematic errors:** Consistent camelCase hallucinations (`endswith` → `endsWith`), token truncations (`os.path.join` → `os.pth.join`), and extension modifications (`.txt` → `.text`) suggest the model's vocabulary is biased toward natural language.

4. **Accuracy far below threshold:** 59% accuracy is unacceptable for production. Even minor syntax errors break code execution.

**Critical insight:** Even if these error patterns were fixed (better prompts, fine-tuning on code), the architectural limitation remains. You cannot use DeepSeek's vision compression with Claude as the inference model.

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

This research demonstrates that **DeepSeek-OCR's vision compression approach is fundamentally incompatible with Claude-based coding assistants** due to architectural limitations, not merely code-specific accuracy issues.

### The Fundamental Problem: Cross-Model Vision Token Transfer

DeepSeek-OCR achieves 10x compression **within its own model ecosystem** by keeping vision tokens compressed in context. However:

1. **Vision tokens cannot cross model boundaries** - DeepSeek's vision embeddings are only consumable by DeepSeek's LLM, not Claude
2. **APIs only expose decoded text** - The model.infer() function returns plain text strings, not vision token embeddings
3. **Forced conversion causes accuracy loss** - We achieve 59% accuracy because we must convert DeepSeek's vision tokens → text → Claude
4. **No way to "defer" conversion** - Even storing PNGs and decompressing on-demand still hits 59% accuracy when calling DeepSeek's API

### The Architectural Gap

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

### Secondary Issues

Code-specific errors (indentation stripping, camelCase hallucinations, training bias) are **symptoms** of the forced text conversion, not the root cause. Even if these were fixed through fine-tuning on code, the architectural limitation remains: **you cannot use one model's vision compression with a different model's LLM.**

### Key Takeaways

1. **For Claude-based systems:** DeepSeek-OCR compression is not viable. Stick with context pruning (daemon cleaner agent).

2. **For DeepSeek-based systems:** Vision compression works as advertised within their ecosystem.

3. **For future research:** Vision compression only works when the same model handles both compression and inference. Cross-model vision token transfer is not currently possible via any API.

**Status:** Research complete. Vision compression via DeepSeek-OCR not viable for Claude-based systems due to architectural incompatibility. Artifacts preserved for future reference.
