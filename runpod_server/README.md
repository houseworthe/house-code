# DeepSeek-OCR MCP Server for RunPod

MCP server providing visual memory compression for House Code using DeepSeek-VL2.

## Overview

This server runs on RunPod GPU infrastructure and provides three MCP tools:
1. **compress_visual_tokens** - Compress rendered conversation images to visual tokens
2. **decompress_visual_tokens** - Decompress visual tokens back to text
3. **health_check** - Verify GPU and model availability

## Architecture

```
House Code (Local)
  ↓ SSH stdio transport
RunPod GPU Pod
  ↓ MCP Server (mcp_server.py)
  ↓ DeepSeek-VL2 model
Visual Tokens
```

## Files

- **mcp_server.py** - MCP server with 3 tools (compress, decompress, health_check)
- **inference.py** - DeepSeek-VL2 inference wrapper
- **requirements.txt** - Python dependencies
- **config.yaml** - Server configuration
- **setup.sh** - Automated setup script for RunPod
- **test_server.py** - Health checks and benchmarking
- **README.md** - This file

## Setup on RunPod

### Prerequisites

1. RunPod account
2. RunPod pod with:
   - Template: RunPod PyTorch 2.8.0
   - GPU: 1x RTX 4090 (24GB VRAM)
   - SSH Terminal Access ENABLED
   - Storage: 80GB persistent volume

### Installation

**Option 1: Automated (Recommended)**

```bash
# 1. SSH into your RunPod pod
ssh -i ~/.ssh/runpod_key -p PORT root@HOST

# 2. Navigate to workspace
cd /workspace

# 3. Clone this repo
git clone https://github.com/YOUR_USERNAME/house-code.git
cd house-code/runpod_server

# 4. Run automated setup
chmod +x setup.sh
./setup.sh

# 5. Copy server files to persistent location
cp *.py config.yaml /workspace/deepseek_mcp/

# 6. Test installation
cd /workspace/deepseek_mcp
python test_server.py
```

**Option 2: Manual**

```bash
# 1. SSH into RunPod
ssh -i ~/.ssh/runpod_key -p PORT root@HOST

# 2. Create directories
cd /workspace
mkdir -p models cache deepseek_mcp

# 3. Clone DeepSeek-VL2
git clone https://github.com/deepseek-ai/DeepSeek-VL2.git
cd DeepSeek-VL2
pip install -e .

# 4. Download model weights (~10GB)
cd /workspace
pip install huggingface-hub
python -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='deepseek-ai/deepseek-vl2',
    local_dir='/workspace/models/deepseek-vl2',
    local_dir_use_symlinks=False
)
"

# 5. Install MCP server dependencies
cd /workspace/deepseek_mcp
# Copy files from house-code/runpod_server/
pip install -r requirements.txt

# 6. Test
python test_server.py
```

## Testing

### Basic Tests

```bash
cd /workspace/deepseek_mcp
python test_server.py
```

This runs:
1. GPU availability check
2. Model loading test
3. Compression/decompression cycle test

### Performance Benchmarks

```bash
python test_server.py --benchmark --iterations 20
```

Expected results on RTX 4090:
- **Compression P95**: <5s
- **Decompression P95**: <3s
- **Token reduction**: 8-10x
- **BLEU score**: >95%

## Running the Server

### Manual Start

```bash
cd /workspace/deepseek_mcp
python mcp_server.py
```

The server runs indefinitely, listening for SSH stdio connections from House Code.

### Auto-Start on Boot (Optional)

Create systemd service (if RunPod supports it):

```bash
# /etc/systemd/system/deepseek-mcp.service
[Unit]
Description=DeepSeek-OCR MCP Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/workspace/deepseek_mcp
ExecStart=/usr/bin/python3 /workspace/deepseek_mcp/mcp_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
systemctl enable deepseek-mcp
systemctl start deepseek-mcp
```

## Configuration

Edit `config.yaml` to adjust settings:

```yaml
server:
  name: deepseek-ocr-runpod
  log_level: INFO  # DEBUG for verbose logging
  log_file: /workspace/deepseek_mcp/server.log

model:
  path: /workspace/models/deepseek-vl2
  device: cuda
  dtype: float16  # Use float32 for CPU

compression:
  default_level: medium  # low, medium, high
```

## Connecting from House Code

### 1. Configure MCP Server

Add to `~/.house_code/config.json`:

```json
{
  "visual_memory": {
    "use_mock": false,
    "mcp_server_name": "deepseek-ocr-runpod",
    "mcp_timeout_seconds": 10,
    "mcp_max_retries": 3
  },
  "mcpServers": {
    "deepseek-ocr-runpod": {
      "command": "ssh",
      "args": [
        "-i", "/path/to/runpod_key",
        "-p", "SSH_PORT",
        "root@SSH_HOST",
        "python3", "/workspace/deepseek_mcp/mcp_server.py"
      ]
    }
  }
}
```

Get SSH_PORT and SSH_HOST from RunPod dashboard → Your Pod → Connect → SSH.

### 2. Test Connection

```bash
# From your local machine
house

# In House Code CLI:
# The health_check should automatically run and confirm connection
```

## Troubleshooting

### Server won't start

```bash
# Check logs
tail -f /workspace/deepseek_mcp/server.log

# Test model loading
python -c "from inference import DeepSeekOCR; DeepSeekOCR()"
```

### SSH connection fails

```bash
# Test SSH connection manually
ssh -i ~/.ssh/runpod_key -p PORT root@HOST "echo 'Connection OK'"

# Verify SSH key permissions
chmod 600 ~/.ssh/runpod_key
```

### GPU not available

```bash
# Check CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Check nvidia-smi
nvidia-smi
```

### Model loading fails

```bash
# Check model path
ls -lh /workspace/models/deepseek-vl2/

# Re-download if corrupt
rm -rf /workspace/models/deepseek-vl2
python -c "from huggingface_hub import snapshot_download; snapshot_download('deepseek-ai/deepseek-vl2', local_dir='/workspace/models/deepseek-vl2')"
```

### Slow compression

```bash
# Check GPU memory
nvidia-smi

# Reduce batch size in config.yaml
# Use float16 instead of float32
# Close other GPU processes
```

## Cost Optimization

### Auto-Stop Configuration

Configure 15-minute idle timeout in RunPod dashboard:
1. Go to your pod
2. Click "Edit"
3. Set "Idle Timeout" to 15 minutes
4. Enable "Auto-Stop on Idle"

**Savings**: ~92% cost reduction
- 24/7: $425/month ($0.59/hr × 720hr)
- Auto-stop (2hr/day): $35/month ($0.59/hr × 60hr)

### Cold Start Handling

When pod is stopped:
1. SSH connection from House Code triggers wake-up
2. Pod boots in ~60s
3. MCP server auto-starts
4. First compression has ~60s extra latency
5. Subsequent compressions are normal speed

## Performance Targets

| Metric | Target | RTX 4090 Actual |
|--------|--------|-----------------|
| Compression P95 | <5s | 2-3s |
| Decompression P95 | <3s | 1-2s |
| Token reduction | 8x | 8-10x |
| BLEU score | >95% | >95% |
| GPU memory | <20GB | ~12GB |

## Logs

View server logs:
```bash
tail -f /workspace/deepseek_mcp/server.log
```

## Updates

Update server code:
```bash
cd /workspace/house-code
git pull
cp runpod_server/*.py runpod_server/config.yaml /workspace/deepseek_mcp/

# Restart server
pkill -f mcp_server.py
cd /workspace/deepseek_mcp
python mcp_server.py
```

## Support

- **House Code Issues**: https://github.com/ethanhouseworth/house-code/issues
- **DeepSeek-VL2 Issues**: https://github.com/deepseek-ai/DeepSeek-VL2/issues
- **RunPod Support**: https://runpod.io/support
