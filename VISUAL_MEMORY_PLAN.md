# DeepSeek-OCR Visual Memory Integration Plan

## Context Summary

**Project:** House Code - Python-based agentic coding assistant (Claude Code clone)
**Repository Status:** Not a git repository (standalone project directory)
**Current State:** 6 phases complete, fully functional with 7 core tools and garbage collector

**Key Architecture Points:**
- ConversationContext stores messages in-memory (List[Message])
- Garbage collector prunes at 150k tokens
- Tool registry pattern for extensions
- Sub-agent system with parent context access
- Clean dataclass-based architecture

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    LOCAL LAPTOP (House Code)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐         ┌──────────────────────┐          │
│  │ ConversationCtx │────────>│  Garbage Collector   │          │
│  │  - messages     │         │  - analyze()         │          │
│  │  - file_cache   │         │  - prune()           │          │
│  │  - visual_cache │ NEW     │  - compress_visual() │ NEW     │
│  └─────────────────┘         └──────────────────────┘          │
│           │                              │                       │
│           │                              │                       │
│           ▼                              ▼                       │
│  ┌─────────────────┐         ┌──────────────────────┐          │
│  │ Visual Memory   │         │  Text→Image Renderer │          │
│  │ Tool            │────────>│  - markdown_to_image()│          │
│  │ (registry)      │         │  - syntax_highlight() │          │
│  └─────────────────┘         │  - layout_engine()    │          │
│           │                   └──────────────────────┘          │
│           │                              │                       │
│           │                              │ PNG/JPEG             │
│           │                              ▼                       │
│           │                   ┌──────────────────────┐          │
│           └──────────────────>│  Rosie API Client    │          │
│                                │  - compress()        │          │
│                                │  - decompress()      │          │
│                                │  - health_check()    │          │
│                                └──────────────────────┘          │
│                                           │                       │
└───────────────────────────────────────────┼───────────────────────┘
                                            │
                                            │ SSH/HTTPS API
                                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              ROSIE SUPERCOMPUTER (Inference Only)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────┐         │
│  │         DeepSeek-OCR Inference Server              │         │
│  │                                                     │         │
│  │  ┌──────────────────┐      ┌──────────────────┐  │         │
│  │  │ FastAPI Endpoint │─────>│ Model Inference  │  │         │
│  │  │ /compress        │      │ (H100 GPUs)      │  │         │
│  │  │ /decompress      │      └──────────────────┘  │         │
│  │  │ /health          │               │             │         │
│  │  └──────────────────┘               │             │         │
│  │           │                          │             │         │
│  │           │                          ▼             │         │
│  │           │                 ┌───────────────────┐ │         │
│  │           └────────────────>│ Visual Tokens     │ │         │
│  │                              │ (compressed repr) │ │         │
│  │                              └───────────────────┘ │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                   │
│  Security: Sandboxed, no bash access, job queue only             │
│  Resources: 2x DGX H100s (16 GPUs), shared queue                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

**Compression Flow:**
```
1. Conversation reaches threshold (e.g., 100k tokens)
2. Garbage Collector identifies compressible messages
3. Text→Image Renderer converts text to visual format
4. Rosie API Client sends image to inference server
5. DeepSeek-OCR returns visual tokens (~10x compressed)
6. Visual tokens stored in ConversationContext.visual_cache
7. Original messages marked as compressed, pruned from context
```

**Decompression Flow (on-demand):**
```
1. User requests context from compressed section
2. Retrieve visual tokens from visual_cache
3. Rosie API Client sends to /decompress endpoint
4. DeepSeek-OCR reconstructs text (97% accuracy)
5. Reconstructed text returned to user/agent
6. Optional: Re-cache decompressed text temporarily
```

---

## 2. Key Questions Answered

### Q: Where does House Code store conversation context?
**A:** `ConversationContext.messages` (List[Message] dataclass) in `/house_code/core.py:23-45`
- In-memory storage only
- No persistence across sessions
- Token count estimated via chars/4
- Extension point: Add `visual_cache: Dict[str, VisualMemory]` to dataclass

### Q: Best threshold to trigger visual compression?
**A:** Multi-tier strategy:
- **Primary threshold:** 100k tokens (before GC's 150k limit)
- **Message age:** Messages >500 turns old
- **Content type:** Prioritize code blocks, file reads, tool outputs
- **Adaptive:** Lower threshold if Rosie latency < 2s, raise if > 5s
- **User override:** Manual compression via tool call

### Q: How to handle async nature of Rosie calls?
**A:** Hybrid approach:
- **Synchronous mode (default):** Block on compression during GC, acceptable latency
- **Async mode (future):** Queue compression jobs, continue with placeholder tokens
- **Batching:** Compress multiple messages in single API call
- **Timeout:** 10s timeout, fallback to local text summarization
- **Background:** Periodic compression during agent idle time

### Q: Cache old visual tokens or recompute?
**A:** **Cache with smart eviction:**
- Store visual tokens in `ConversationContext.visual_cache`
- LRU eviction when cache > 50 entries
- Persist cache to disk (`.house_code/visual_cache.json`)
- Recompute only if:
  - Original text modified
  - Cache corrupted
  - Explicit user request
- **Trade-off:** Storage (~1MB per 10k tokens compressed) vs recompute latency (2-5s)

### Q: Failure mode if DeepSeek-OCR errors?
**A:** Graceful degradation with fallback stack:
1. **Retry:** 3 attempts with exponential backoff (1s, 2s, 4s)
2. **Local fallback:** Simple text summarization (extractive)
3. **No compression:** Keep original text, skip compression
4. **User notification:** Warning in CLI, continue operation
5. **Health monitoring:** Track Rosie availability, disable if <50% success rate
6. **Offline mode:** Work entirely locally if Rosie unreachable

---

## 3. Phased Implementation Plan

### Phase 1: Rosie Infrastructure Setup & Validation
**Goal:** Get DeepSeek-OCR running on Rosie, validate inference works

**Tasks:**
1. Contact buddy for Rosie access credentials
2. SSH into Rosie, explore environment (SLURM, modules, storage)
3. Clone DeepSeek-OCR repository to Rosie workspace
4. Install dependencies in conda/venv environment
5. Download DeepSeek-OCR model weights (~10GB)
6. Create inference script (`rosie_inference.py`)
7. Submit test SLURM job with sample image
8. Validate output quality (visual tokens + reconstruction)

**Deliverables:**
- Working DeepSeek-OCR inference on Rosie
- Test script demonstrating compression/decompression
- Latency benchmarks (target: <5s per image)

**Effort:** 8-12 hours
**Risk:** Medium (depends on Rosie environment, model compatibility)

---

### Phase 2: Rosie API Server
**Goal:** Create FastAPI server on Rosie for remote inference calls

**Tasks:**
1. Design API contract (JSON schema for requests/responses)
2. Implement FastAPI server (`/compress`, `/decompress`, `/health`)
3. Add request validation, rate limiting, authentication
4. Integrate with SLURM job submission (or direct GPU if allowed)
5. Add logging, error handling, timeout management
6. Deploy to Rosie compute node (persistent service or job queue)
7. Test from local laptop via SSH tunnel/port forwarding

**File Structure:**
```
rosie_server/
├── api.py              # FastAPI endpoints
├── inference.py        # DeepSeek-OCR wrapper
├── auth.py             # API key validation
├── config.yaml         # Model paths, GPU settings
├── requirements.txt
└── submit_job.sh       # SLURM submission script
```

**Deliverables:**
- Running API server on Rosie
- OpenAPI documentation
- Client authentication working
- <5s average latency

**Effort:** 12-16 hours
**Risk:** Medium-high (SLURM job management, persistent services)

---

### Phase 3: Local Text→Image Renderer
**Goal:** Convert conversation text to high-quality images for compression

**Tasks:**
1. Design image format (layout, fonts, syntax highlighting)
2. Implement markdown→image converter using PIL/Cairo
3. Add syntax highlighting for code blocks (pygments)
4. Handle multi-column layout for efficiency
5. Optimize for OCR readability (font size, contrast, resolution)
6. Add metadata overlay (timestamp, message ID)
7. Benchmark image sizes vs text token counts

**File Structure:**
```
house_code/visual/
├── __init__.py
├── renderer.py         # Main rendering logic
├── layout.py           # Multi-column layout engine
├── highlighter.py      # Syntax highlighting
├── fonts/              # Monospace fonts for code
└── templates/          # Image templates
```

**Key Decisions:**
- **Resolution:** 1920x1080 per "page" (fits ~100 lines of code)
- **Font:** JetBrains Mono 14pt (optimal for OCR)
- **Format:** PNG (lossless) for compression, JPEG for storage
- **Metadata:** Embed message IDs in image EXIF

**Deliverables:**
- Renderer converting text→PNG
- Visual quality validation
- 100+ lines of code per image

**Effort:** 10-14 hours
**Risk:** Low (well-understood problem)

---

### Phase 4: Rosie API Client
**Goal:** Local client library for calling Rosie inference server

**Tasks:**
1. Implement client class with retry logic
2. Add async support (optional for v1)
3. Implement health checking, circuit breaker
4. Add request batching for multiple images
5. Handle authentication, SSL/TLS
6. Add caching layer (avoid redundant calls)
7. Implement fallback strategies on failure

**File Structure:**
```
house_code/visual/
├── rosie_client.py     # Main client class
├── auth.py             # API key management
├── cache.py            # Local response cache
└── config.py           # Rosie endpoint config
```

**API Interface:**
```python
class RosieClient:
    def compress(self, image: bytes) -> VisualTokens
    def decompress(self, tokens: VisualTokens) -> str
    def health_check(self) -> bool
    def batch_compress(self, images: List[bytes]) -> List[VisualTokens]
```

**Deliverables:**
- Working client library
- <5s latency for compression
- Graceful degradation on errors
- 95%+ success rate

**Effort:** 8-10 hours
**Risk:** Low-medium (network reliability)

---

### Phase 5: Visual Memory Tool
**Goal:** Integrate visual memory into House Code's tool system

**Tasks:**
1. Extend `ConversationContext` with `visual_cache`
2. Create VisualMemory dataclass (tokens, metadata, original_msg_ids)
3. Implement visual memory tool definition
4. Implement tool executor (orchestrates renderer + client)
5. Register tool in registry
6. Add compression status tracking
7. Update system prompt to document capability

**File Structure:**
```
house_code/
├── core.py                      # MODIFY: Add visual_cache to ConversationContext
├── tools/
│   ├── visual_memory.py         # NEW: Tool implementation
│   └── registry.py              # MODIFY: Register new tool
└── visual/                      # NEW: Visual memory subsystem
    ├── __init__.py
    ├── models.py                # VisualMemory dataclass
    ├── renderer.py              # From Phase 3
    ├── rosie_client.py          # From Phase 4
    └── cache.py
```

**ConversationContext Extension:**
```python
@dataclass
class ConversationContext:
    messages: List[Message]
    file_cache: Dict[str, str]
    current_todos: List[Dict]
    critical_state: Dict[str, Any]
    visual_cache: Dict[str, VisualMemory]  # NEW
    compression_stats: CompressionStats    # NEW
```

**Tool Definition:**
```python
{
    "name": "visual_memory",
    "description": "Compress conversation history into visual tokens",
    "input_schema": {
        "message_ids": ["list of message IDs to compress"],
        "compression_level": ["low", "medium", "high"],
        "force": [bool, "force recompression"]
    }
}
```

**Deliverables:**
- Working visual memory tool
- Integration with existing tools
- Manual compression capability
- Token reduction validation

**Effort:** 10-12 hours
**Risk:** Low (follows existing patterns)

---

### Phase 6: Garbage Collector Integration
**Goal:** Automatic visual compression during GC pruning

**Tasks:**
1. Add `_find_compressible_messages()` to GarbageCollector
2. Implement `_compress_to_visual()` method
3. Update `analyze()` to estimate visual compression savings
4. Update `prune()` to apply visual compression
5. Add heuristics for what to compress (code blocks, file reads)
6. Preserve critical state (don't compress recent messages)
7. Update token counting to account for visual tokens

**File Structure:**
```
house_code/
├── garbage_collector.py         # MODIFY: Add visual compression
└── visual/
    └── gc_integration.py        # NEW: GC-specific compression logic
```

**Compression Heuristics:**
```python
def should_compress(message: Message) -> bool:
    # Compress if:
    # - Message age > 500 turns
    # - Contains code blocks > 50 lines
    # - Is superseded file read
    # - Is old tool output
    # AND:
    # - Not in critical_state
    # - Not recent (last 100 turns)
    # - Rosie available
```

**GC Flow Update:**
```
1. analyze() identifies compressible messages
2. Estimate visual compression savings (80% reduction)
3. If savings > threshold AND Rosie available:
   4. Render messages to images
   5. Call Rosie for compression
   6. Store visual tokens in visual_cache
   7. Mark original messages as compressed
   8. Remove compressed messages from context
9. Return new context + savings
```

**Deliverables:**
- Automatic visual compression in GC
- 80%+ token reduction for code-heavy messages
- Seamless integration with existing GC
- Compression stats in analyze() output

**Effort:** 12-15 hours
**Risk:** Medium (integration complexity)

---

### Phase 7: Sub-Agent Visual Memory Awareness
**Goal:** Sub-agents can reference visual memories without full decompression

**Tasks:**
1. Add visual memory summaries to sub-agent context
2. Implement lazy decompression (on-demand)
3. Update sub-agent system prompts
4. Add visual memory references to parent context transfer
5. Implement smart context transfer (summaries vs full decompress)

**File Structure:**
```
house_code/
└── subagents.py                 # MODIFY: Visual memory awareness
```

**Context Transfer Strategy:**
```python
def prepare_subagent_context(parent_context):
    # For compressed messages, send:
    # - Message metadata (timestamp, type)
    # - Short summary (50 tokens)
    # - Reference ID for full decompression
    #
    # Sub-agent can request full decompression if needed
```

**Deliverables:**
- Sub-agents aware of visual memories
- Reduced token transfer to sub-agents
- On-demand decompression working

**Effort:** 6-8 hours
**Risk:** Low

---

### Phase 8: Persistence & Caching
**Goal:** Persist visual cache across sessions, optimize performance

**Tasks:**
1. Implement visual cache serialization (JSON/MessagePack)
2. Add cache loading on startup
3. Implement cache eviction policies (LRU, size limits)
4. Add cache statistics and monitoring
5. Implement cache corruption recovery
6. Add cache pruning command

**File Structure:**
```
.house_code/                     # NEW: User cache directory
├── visual_cache.json            # Serialized visual tokens
├── cache_metadata.json          # Cache stats, indexes
└── rendered_images/             # Optional: Keep rendered images
```

**Deliverables:**
- Persistent visual cache
- Fast startup with cached data
- <100MB cache size limit
- Cache health monitoring

**Effort:** 6-8 hours
**Risk:** Low

---

### Phase 9: Benchmarking & Optimization
**Goal:** Validate compression targets, optimize performance

**Tasks:**
1. Create benchmark suite (various conversation types)
2. Measure token reduction rates
3. Measure accuracy (reconstruction vs original)
4. Measure latency (end-to-end compression time)
5. Optimize rendering (parallel, caching)
6. Optimize Rosie calls (batching, connection pooling)
7. Profile and fix bottlenecks

**Benchmarks:**
```
Test Cases:
1. Code-heavy conversation (1000 lines Python)
2. Mixed text/code conversation
3. Sub-agent delegation heavy
4. File read heavy (100+ files)
5. Long-running session (500+ turns)

Metrics:
- Token reduction %
- Reconstruction accuracy %
- Latency (p50, p95, p99)
- Cache hit rate
- Rosie availability
```

**Deliverables:**
- Benchmark report
- Performance optimizations applied
- Target metrics achieved

**Effort:** 10-12 hours
**Risk:** Low

---

## 4. Complete File Structure

```
house-code/
│
├── house_code/                           # Main package
│   │
│   ├── core.py                          # MODIFY: Add visual_cache to ConversationContext
│   │                                    #         Update token estimation
│   │                                    #         Add compression status tracking
│   │
│   ├── cli.py                           # MODIFY: Add visual memory stats to output
│   │                                    #         Add --no-visual flag
│   │
│   ├── garbage_collector.py             # MODIFY: Add visual compression methods
│   │                                    #         _find_compressible_messages()
│   │                                    #         _compress_to_visual()
│   │                                    #         Update analyze() and prune()
│   │
│   ├── subagents.py                     # MODIFY: Visual memory awareness
│   │                                    #         Smart context transfer
│   │
│   ├── tools/
│   │   ├── registry.py                  # MODIFY: Register visual_memory tool
│   │   ├── visual_memory.py             # NEW: Visual memory tool implementation
│   │   └── (existing tools...)
│   │
│   └── visual/                          # NEW: Visual memory subsystem
│       │
│       ├── __init__.py                  # Package exports
│       │
│       ├── models.py                    # NEW: Data models
│       │                                #   - VisualMemory dataclass
│       │                                #   - VisualTokens dataclass
│       │                                #   - CompressionStats dataclass
│       │                                #   - RenderConfig dataclass
│       │
│       ├── renderer.py                  # NEW: Text→Image rendering
│       │                                #   - markdown_to_image()
│       │                                #   - render_code_block()
│       │                                #   - render_conversation()
│       │                                #   - apply_syntax_highlighting()
│       │
│       ├── layout.py                    # NEW: Image layout engine
│       │                                #   - MultiColumnLayout class
│       │                                #   - calculate_dimensions()
│       │                                #   - fit_text_to_page()
│       │
│       ├── highlighter.py               # NEW: Syntax highlighting
│       │                                #   - PygmentsHighlighter wrapper
│       │                                #   - Language detection
│       │
│       ├── rosie_client.py              # NEW: Rosie API client
│       │                                #   - RosieClient class
│       │                                #   - compress()
│       │                                #   - decompress()
│       │                                #   - batch_compress()
│       │                                #   - health_check()
│       │
│       ├── auth.py                      # NEW: Authentication
│       │                                #   - API key management
│       │                                #   - Token validation
│       │
│       ├── cache.py                     # NEW: Local caching
│       │                                #   - VisualCache class
│       │                                #   - LRU eviction
│       │                                #   - Persistence (JSON)
│       │
│       ├── config.py                    # NEW: Configuration
│       │                                #   - Rosie endpoint URL
│       │                                #   - Compression thresholds
│       │                                #   - Rendering settings
│       │
│       ├── gc_integration.py            # NEW: GC-specific logic
│       │                                #   - Compression heuristics
│       │                                #   - Message selection
│       │                                #   - Savings estimation
│       │
│       ├── fonts/                       # NEW: Embedded fonts
│       │   ├── JetBrainsMono-Regular.ttf
│       │   └── JetBrainsMono-Bold.ttf
│       │
│       └── templates/                   # NEW: Image templates
│           ├── code_page.png           # Base template for code
│           └── text_page.png           # Base template for text
│
├── rosie_server/                        # NEW: Rosie inference server (deployed to Rosie)
│   │
│   ├── api.py                          # FastAPI application
│   │                                    #   - POST /compress
│   │                                    #   - POST /decompress
│   │                                    #   - GET /health
│   │                                    #   - GET /stats
│   │
│   ├── inference.py                    # DeepSeek-OCR wrapper
│   │                                    #   - load_model()
│   │                                    #   - encode_image()
│   │                                    #   - decode_tokens()
│   │
│   ├── models.py                       # Pydantic models
│   │                                    #   - CompressRequest
│   │                                    #   - CompressResponse
│   │                                    #   - DecompressRequest
│   │
│   ├── auth.py                         # API authentication
│   │                                    #   - API key validation
│   │                                    #   - Rate limiting
│   │
│   ├── config.yaml                     # Server configuration
│   │                                    #   - Model paths
│   │                                    #   - GPU device IDs
│   │                                    #   - Batch sizes
│   │
│   ├── requirements.txt                # Python dependencies
│   │                                    #   - fastapi
│   │                                    #   - uvicorn
│   │                                    #   - torch
│   │                                    #   - transformers
│   │                                    #   - deepseek-ocr
│   │
│   ├── submit_job.sh                   # SLURM job submission
│   │                                    #   - Request H100 GPU
│   │                                    #   - Set memory/time limits
│   │                                    #   - Launch server
│   │
│   └── README.md                       # Deployment instructions
│
├── tests/                              # NEW/MODIFY: Test suite
│   │
│   ├── test_visual_memory/            # NEW: Visual memory tests
│   │   ├── test_renderer.py
│   │   ├── test_rosie_client.py
│   │   ├── test_cache.py
│   │   ├── test_gc_integration.py
│   │   └── fixtures/
│   │       ├── sample_conversations.json
│   │       └── expected_compressions.json
│   │
│   └── (existing tests...)
│
├── benchmarks/                         # NEW: Performance benchmarks
│   ├── compression_benchmark.py        # Token reduction tests
│   ├── accuracy_benchmark.py           # Reconstruction accuracy
│   ├── latency_benchmark.py            # E2E latency tests
│   └── test_data/                      # Benchmark datasets
│       ├── code_heavy.json
│       ├── mixed_content.json
│       └── long_session.json
│
├── docs/                               # NEW: Documentation
│   ├── VISUAL_MEMORY.md                # Feature overview
│   ├── ROSIE_SETUP.md                  # Rosie deployment guide
│   ├── API.md                          # API documentation
│   └── TROUBLESHOOTING.md              # Common issues
│
├── scripts/                            # NEW: Utility scripts
│   ├── setup_rosie.sh                  # Rosie environment setup
│   ├── test_rosie_connection.py        # Connectivity test
│   ├── benchmark_runner.py             # Run all benchmarks
│   └── cache_manager.py                # Cache maintenance
│
├── .house_code/                        # NEW: User cache directory (gitignored)
│   ├── visual_cache.json               # Serialized visual tokens
│   ├── cache_metadata.json             # Cache indexes
│   ├── rendered_images/                # Optional: Cached images
│   └── logs/                           # Debug logs
│
├── pyproject.toml                      # MODIFY: Add dependencies
│                                        #   - Pillow (image rendering)
│                                        #   - pygments (syntax highlighting)
│                                        #   - httpx (async HTTP)
│                                        #   - pydantic (validation)
│
├── VISUAL_MEMORY_PLAN.md               # THIS FILE
├── README.md                           # MODIFY: Document visual memory
└── ARCHITECTURE.md                     # MODIFY: Add visual memory section
```

### Files to Create (New)
**Total: 30 new files**

**Core Integration (5 files):**
- `house_code/tools/visual_memory.py`
- `house_code/visual/__init__.py`
- `house_code/visual/models.py`
- `house_code/visual/config.py`
- `house_code/visual/gc_integration.py`

**Rendering System (4 files):**
- `house_code/visual/renderer.py`
- `house_code/visual/layout.py`
- `house_code/visual/highlighter.py`
- `house_code/visual/fonts/` (+ font files)

**Rosie Integration (4 files):**
- `house_code/visual/rosie_client.py`
- `house_code/visual/auth.py`
- `house_code/visual/cache.py`
- `house_code/visual/templates/` (+ template images)

**Rosie Server (7 files):**
- `rosie_server/api.py`
- `rosie_server/inference.py`
- `rosie_server/models.py`
- `rosie_server/auth.py`
- `rosie_server/config.yaml`
- `rosie_server/requirements.txt`
- `rosie_server/submit_job.sh`

**Testing & Benchmarks (5 files):**
- `tests/test_visual_memory/test_renderer.py`
- `tests/test_visual_memory/test_rosie_client.py`
- `tests/test_visual_memory/test_cache.py`
- `tests/test_visual_memory/test_gc_integration.py`
- `benchmarks/` (3 benchmark scripts)

**Documentation & Scripts (5 files):**
- `docs/VISUAL_MEMORY.md`
- `docs/ROSIE_SETUP.md`
- `scripts/setup_rosie.sh`
- `scripts/test_rosie_connection.py`
- `.house_code/` (cache directory structure)

### Files to Modify (Existing)
**Total: 6 modified files**

1. `house_code/core.py` - Add visual_cache to ConversationContext
2. `house_code/cli.py` - Add visual memory stats
3. `house_code/garbage_collector.py` - Visual compression methods
4. `house_code/subagents.py` - Visual memory awareness
5. `house_code/tools/registry.py` - Register new tool
6. `pyproject.toml` - Add dependencies

---

## 5. Success Metrics & Validation

### Primary Success Metrics

#### 1. Token Reduction
**Target: 80%+ reduction for code-heavy content**

**Acceptance Criteria:**
- Code-heavy conversations: ≥85% reduction
- Mixed content: ≥70% reduction
- Text-heavy: ≥60% reduction
- Overall average: ≥80% reduction

---

#### 2. Reconstruction Accuracy
**Target: 95%+ accuracy (original vs reconstructed)**

**Acceptance Criteria:**
- Character-level accuracy: ≥97%
- BLEU score: ≥0.95
- Code validity: ≥99% (syntax preserved)
- Overall semantic accuracy: ≥95%

---

#### 3. Latency
**Target: <5s end-to-end compression latency (p95)**

**Acceptance Criteria:**
- Rendering (p95): ≤1s
- Network transfer (p95): ≤1s
- Inference on Rosie (p95): ≤3s
- Total latency (p95): ≤5s
- Total latency (p50): ≤3s

---

#### 4. System Reliability
**Target: 99% uptime, <1% error rate**

**Acceptance Criteria:**
- Success rate: ≥99%
- Error rate: ≤1%
- Rosie availability: ≥95%
- Graceful degradation: 100% (always falls back)
- Cache hit rate: ≥50% (after warmup)

---

#### 5. Storage Efficiency
**Target: <100MB cache size, <1MB per compressed session**

**Acceptance Criteria:**
- Total cache size: ≤100MB
- Average compressed memory: ≤1MB
- Cache overhead: ≤20% (metadata vs data)
- Eviction works: Cache never exceeds 100MB

---

#### 6. Integration Quality
**Target: No breaking changes, seamless UX**

**Acceptance Criteria:**
- All existing tools work: 100%
- No breaking changes: 0
- Performance overhead: ≤5% (when visual memory disabled)
- Backward compatible: 100%
- Documentation complete: 100%

---

### Validation Dashboard

**Real-time Monitoring:**
```
$ house --visual-memory-status

Visual Memory System Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Compression Stats:
  Total Compressed:      487 messages
  Tokens Saved:          127,453 tokens (82.3% reduction)
  Cache Size:            47.2 MB
  Avg Accuracy:          96.8%

Performance (last 100 requests):
  Latency p50:           2.1s
  Latency p95:           4.3s
  Latency p99:           6.8s
  Success Rate:          99.2%

Rosie Status:
  Health:                ✓ Healthy
  Availability:          98.7% (last 24h)
  Queue Time:            0.3s avg

Cache:
  Entries:               243
  Hit Rate:              67.4%
  Evictions:             12 (LRU)
  Last Pruned:           2h ago

Recent Errors:
  [None in last 24h]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 6. Risk Mitigation

### High-Priority Risks

#### Risk 1: Rosie Compute Quotas
**Impact:** High | **Likelihood:** Medium

**Mitigation:**
- Coordinate with buddy on quota limits
- Implement request batching (compress multiple messages at once)
- Add queue management (throttle requests)
- Local fallback if quota exceeded
- Monitor usage daily

**Contingency:**
- Use local summarization instead of visual compression
- Deploy to personal cloud GPU (Runpod/Lambda Labs) if needed

---

#### Risk 2: DeepSeek-OCR Model Compatibility
**Impact:** High | **Likelihood:** Low

**Mitigation:**
- Test on Rosie during Phase 1 (early validation)
- Check CUDA version compatibility
- Verify model weights download correctly
- Have alternative models ready (LLaVA, Qwen-VL)

**Contingency:**
- Use alternative vision-language model
- Fallback to simple image captioning + text compression

---

#### Risk 3: Latency Too High
**Impact:** Medium | **Likelihood:** Medium

**Mitigation:**
- Optimize image resolution (trade quality for speed)
- Batch compression requests
- Use async processing (don't block main loop)
- Cache aggressively
- Compress during idle time

**Contingency:**
- Only compress very old messages (>1000 turns)
- User opts into compression manually
- Disable auto-compression, keep manual only

---

#### Risk 4: Reconstruction Accuracy Below Target
**Impact:** High | **Likelihood:** Low

**Mitigation:**
- Test rendering quality early (Phase 3)
- Optimize font/layout for OCR readability
- Use higher resolution images if needed
- Validate on diverse content types
- Keep original text as backup

**Contingency:**
- Use visual compression only for less critical content
- Always keep original for recent messages
- Provide "verify decompression" tool for users

---

#### Risk 5: Rosie Access Lost
**Impact:** High | **Likelihood:** Low

**Mitigation:**
- Graceful degradation built-in from start
- Local fallback always available
- Cache compressed tokens locally
- Document alternative deployment options

**Contingency:**
- Deploy to personal cloud GPU (~$1/hour)
- Use Claude API for summarization instead
- Disable visual memory, rely on existing GC only

---

## 7. Implementation Timeline

### Total Estimated Effort: 90-110 hours (~2.5-3 weeks full-time)

**Week 1: Infrastructure (Phases 1-4)**
- Days 1-2: Rosie setup + validation (Phase 1)
- Days 3-4: API server deployment (Phase 2)
- Day 5: Text→Image renderer (Phase 3)
- Days 6-7: Rosie client + testing (Phase 4)

**Week 2: Integration (Phases 5-7)**
- Days 1-2: Visual memory tool (Phase 5)
- Days 3-4: Garbage collector integration (Phase 6)
- Day 5: Sub-agent awareness (Phase 7)

**Week 3: Polish & Launch (Phases 8-9)**
- Days 1-2: Persistence + caching (Phase 8)
- Days 3-4: Benchmarking + optimization (Phase 9)
- Day 5: Documentation + cleanup
- Days 6-7: Testing + launch

**Part-time Schedule (10-15 hrs/week):**
- ~6-8 weeks to completion

---

## 8. Next Steps

### Immediate Actions (Before Coding)

**1. Validate Rosie Access (Critical)**
```bash
# Contact buddy, get:
- Rosie login credentials
- SLURM account name
- Compute quota limits
- SSH connection details
- Preferred communication for status updates
```

**2. Environment Survey**
```bash
# SSH into Rosie, document:
ssh username@rosie.msoe.edu

# Check available resources
squeue -u $USER
sinfo
module avail cuda
module avail python
nvidia-smi

# Check storage quotas
quota
df -h $HOME
```

**3. DeepSeek-OCR Research**
```bash
# Validate model availability:
- Model size (download time/storage)
- CUDA compatibility
- Published benchmarks
- Alternative models if needed
```

**4. Prototype Quick Win**
Before full implementation, create proof-of-concept:
```bash
# Local: Render single message to image
python -c "from PIL import Image, ImageDraw, ImageFont
img = Image.new('RGB', (1920, 1080), 'white')
# ... render test message ...
img.save('test.png')"

# Upload to Rosie, run inference, validate accuracy
# This validates the entire pipeline end-to-end
```

**5. Create Project Tracking**
```bash
# Create GitHub project board or equivalent:
- Columns: Backlog, In Progress, Testing, Done
- Import all 9 phases as issues
- Assign priorities
- Set milestones
```

---

### Recommended Start Sequence

**Option A: Fast Track (Rosie available immediately)**
1. Start with Phase 1 today (Rosie setup)
2. Parallel develop Phase 3 locally (renderer)
3. Merge in Phase 2 (API server)
4. Continue sequentially

**Option B: Rosie Delayed (waiting on access)**
1. Start with Phase 3 (renderer) - fully local
2. Create mock Rosie client for testing
3. Implement Phase 5 (tool) with mock
4. Swap in real Rosie when available

**Option C: Research First (de-risk)**
1. Literature review on DeepSeek-OCR
2. Alternative model evaluation
3. Latency/accuracy benchmarks from papers
4. Then proceed with Phase 1

---

## Summary

**What You Have Now:**

✅ **Comprehensive Architecture** - Visual memory system integrated with House Code's garbage collector
✅ **9-Phase Implementation Plan** - 90-110 hours total effort, well-scoped
✅ **35 Files to Create/Modify** - Clear file structure, separation of concerns
✅ **Testing Strategy** - Unit, integration, E2E, benchmarks
✅ **Success Metrics** - 80%+ compression, 95%+ accuracy, <5s latency
✅ **Risk Mitigation** - Graceful degradation, fallback strategies
✅ **Rosie Integration Design** - Secure, sandboxed, API-based

**Key Innovations:**

1. **Remote Inference Only** - House Code stays local, Rosie does compression
2. **GC Integration** - Automatic compression at 100k tokens
3. **Visual Token Caching** - Persistent, LRU eviction
4. **Sub-Agent Awareness** - Summaries instead of full decompression
5. **Graceful Degradation** - Works offline, falls back to text summarization

**Critical Path:**

```
Rosie Access → Phase 1 (Validation) → Phase 2 (API) →
Phase 3 (Renderer) → Phase 5 (Tool) → Phase 6 (GC) →
Benchmarking → Launch
```

**Expected Outcomes:**

- **Token Reduction:** 80-85% for code-heavy conversations
- **Accuracy:** 95-97% reconstruction
- **Latency:** 2-4s average, <5s p95
- **Reliability:** 99%+ uptime with fallback
- **Storage:** <100MB cache, ~1MB per session
- **Impact:** 10x longer conversations before context limits

---

**Ready to build something novel.**

**Recommended first command:**
```bash
# Contact buddy for Rosie access, then:
ssh username@rosie.msoe.edu
# Begin Phase 1 validation
```
