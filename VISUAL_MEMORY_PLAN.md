# DeepSeek-OCR Visual Memory Integration Plan

## Architecture

### Overview
```
Local (House Code) → SSH stdio → Rosie (MCP Server) → DeepSeek-OCR
```

### MCP Integration
- House Code already has MCP client support
- SSH stdio transport (no persistent server)
- 3 server files vs 7 with FastAPI

### Configuration
```json
{
  "mcpServers": {
    "deepseek-ocr-rosie": {
      "command": "ssh",
      "args": ["username@rosie.msoe.edu", "python3", "/path/to/mcp_server.py"]
    }
  }
}
```

### Data Flow

**Compression:**
1. GC identifies compressible messages
2. Text→Image renderer converts to PNG
3. MCP call to Rosie compresses image
4. Visual tokens stored in ConversationContext.visual_cache
5. Original messages pruned

**Decompression:**
1. Retrieve visual tokens from cache
2. MCP call to Rosie decompresses
3. Return reconstructed text

---

## Implementation Phases

### Phase 1: Rosie Setup
1. SSH into Rosie, check environment (SLURM, CUDA, storage)
2. Clone DeepSeek-OCR repository
3. Install dependencies
4. Download model weights
5. Create inference script
6. Test compression/decompression
7. Validate latency (<5s) and accuracy (>95%)

### Phase 2: MCP Server
```python
# rosie_server/mcp_server.py
from mcp.server import Server
from inference import DeepSeekOCR

server = Server("deepseek-ocr-rosie")

@server.tool()
async def compress_visual_tokens(image_base64: str, compression_level: str = "medium") -> dict:
    model = DeepSeekOCR()
    result = model.compress(image_base64, level=compression_level)
    return {
        "tokens": result.tokens,
        "compression_ratio": result.ratio,
        "metadata": {"model": "deepseek-ocr", "level": compression_level}
    }

@server.tool()
async def decompress_visual_tokens(tokens: list) -> dict:
    model = DeepSeekOCR()
    text = model.decompress(tokens)
    return {"text": text, "confidence": model.last_confidence}

@server.tool()
async def health_check() -> dict:
    import torch
    return {
        "status": "healthy",
        "gpu_available": torch.cuda.is_available(),
        "gpu_count": torch.cuda.device_count()
    }

if __name__ == "__main__":
    server.run()
```

**Files:**
- `rosie_server/mcp_server.py`
- `rosie_server/inference.py`
- `rosie_server/requirements.txt`

### Phase 3: Text→Image Renderer

**Rendering specs:**
- Resolution: 1920x1080 per page (~100 lines of code)
- Font: JetBrains Mono 14pt
- Format: PNG (lossless)
- Metadata: Embed message IDs in EXIF

**Files:**
- `house_code/visual/renderer.py`
- `house_code/visual/layout.py`
- `house_code/visual/highlighter.py`

### Phase 4: MCP Client Wrapper

```python
# house_code/visual/rosie_client.py
import base64

class RosieClient:
    def __init__(self):
        self.mcp_server = "deepseek-ocr-rosie"

    def compress(self, image: bytes) -> VisualTokens:
        image_b64 = base64.b64encode(image).decode()
        result = self._call_mcp_tool(
            server=self.mcp_server,
            tool="compress_visual_tokens",
            arguments={"image_base64": image_b64}
        )
        return VisualTokens(data=result["tokens"], metadata=result["metadata"])

    def decompress(self, tokens: VisualTokens) -> str:
        result = self._call_mcp_tool(
            server=self.mcp_server,
            tool="decompress_visual_tokens",
            arguments={"tokens": tokens.data}
        )
        return result["text"]

    def health_check(self) -> bool:
        try:
            result = self._call_mcp_tool(
                server=self.mcp_server,
                tool="health_check",
                arguments={}
            )
            return result["status"] == "healthy"
        except:
            return False

    def _call_mcp_tool(self, server: str, tool: str, arguments: dict):
        # Use House Code's existing MCP client
        pass
```

**Files:**
- `house_code/visual/rosie_client.py`
- `house_code/visual/cache.py`

### Phase 5: Visual Memory Tool

**Extend ConversationContext:**
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

**Tool definition:**
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

**Files:**
- `house_code/core.py` (modify)
- `house_code/tools/visual_memory.py` (new)
- `house_code/tools/registry.py` (modify)
- `house_code/visual/models.py` (new)

### Phase 6: Garbage Collector Integration

**Compression heuristics:**
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

**GC flow:**
1. `analyze()` identifies compressible messages
2. Estimate visual compression savings (80% reduction)
3. If savings > threshold AND Rosie available:
   - Render messages to images
   - Call Rosie for compression
   - Store visual tokens in visual_cache
   - Mark original messages as compressed
   - Remove compressed messages from context
4. Return new context + savings

**Files:**
- `house_code/garbage_collector.py` (modify)
- `house_code/visual/gc_integration.py` (new)

### Phase 7: Sub-Agent Awareness

**Context transfer strategy:**
```python
def prepare_subagent_context(parent_context):
    # For compressed messages, send:
    # - Message metadata (timestamp, type)
    # - Short summary (50 tokens)
    # - Reference ID for full decompression
```

**Files:**
- `house_code/subagents.py` (modify)

### Phase 8: Persistence

**Cache structure:**
```
.house_code/
├── visual_cache.json
├── cache_metadata.json
└── rendered_images/
```

**Cache policies:**
- LRU eviction when cache > 50 entries
- Persist to disk
- <100MB size limit

**Files:**
- `house_code/visual/cache.py` (enhance)

### Phase 9: Benchmarking

**Test datasets:**
- Code-heavy (1000 lines Python)
- Mixed content (text + code)
- Long session (500+ turns)

**Metrics:**
- Token reduction %
- Reconstruction accuracy (BLEU, edit distance)
- Latency (p50, p95, p99)
- Cache hit rate

---

## File Structure

```
house-code/
├── house_code/
│   ├── core.py                          # MODIFY: Add visual_cache
│   ├── cli.py                           # MODIFY: Add visual memory stats
│   ├── garbage_collector.py             # MODIFY: Add visual compression
│   ├── subagents.py                     # MODIFY: Visual memory awareness
│   ├── tools/
│   │   ├── registry.py                  # MODIFY: Register visual_memory
│   │   └── visual_memory.py             # NEW
│   └── visual/                          # NEW
│       ├── __init__.py
│       ├── models.py
│       ├── renderer.py
│       ├── layout.py
│       ├── highlighter.py
│       ├── rosie_client.py
│       ├── cache.py
│       ├── config.py
│       └── gc_integration.py
├── rosie_server/                        # NEW
│   ├── mcp_server.py
│   ├── inference.py
│   ├── requirements.txt
│   └── README.md
├── tests/test_visual_memory/            # NEW
├── benchmarks/                          # NEW
└── .house_code/                         # NEW (cache directory)
```

---

## Success Metrics

- **Token reduction:** 80%+ for code-heavy content
- **Accuracy:** 95%+ reconstruction (BLEU score)
- **Latency:** <5s p95 end-to-end
- **Reliability:** 99%+ success rate
- **Storage:** <100MB cache, ~1MB per session

---

## Key Questions Answered

**Q: Where does House Code store conversation context?**
A: `ConversationContext.messages` in `/house_code/core.py:23-45`

**Q: Compression threshold?**
A: 100k tokens (before GC's 150k limit), adaptive based on Rosie latency

**Q: Handle async Rosie calls?**
A: Synchronous by default (block during GC). 10s timeout with local fallback.

**Q: Cache or recompute visual tokens?**
A: Cache with LRU eviction. Persist to `.house_code/visual_cache.json`

**Q: Failure mode?**
A: Retry 3x → Local summarization → Keep original text → Continue operation

---

## Risk Mitigation

**Rosie quota exhaustion:**
- Batch requests
- Monitor usage daily
- Fallback: Local summarization or cloud GPU

**Latency too high:**
- Optimize resolution
- Compress during idle time
- Only compress old messages (>1000 turns)

**Accuracy below target:**
- Optimize rendering (font, layout)
- Higher resolution
- Keep original as backup

**Rosie access lost:**
- Graceful degradation built-in
- Local fallback always available
- Deploy to personal cloud GPU if needed
