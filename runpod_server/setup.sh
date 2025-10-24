#!/bin/bash
set -e

echo "==================================="
echo "DeepSeek-OCR MCP Server Setup"
echo "==================================="
echo ""

# Check if running on RunPod
if [ ! -d "/workspace" ]; then
    echo "Warning: /workspace not found. Are you running on RunPod?"
    echo "This script is designed for RunPod environments."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Navigate to workspace
cd /workspace

# Step 1: Create directories
echo "[1/6] Creating directories..."
mkdir -p models cache deepseek_mcp
echo "✓ Directories created"

# Step 2: Clone DeepSeek-VL2 repository
echo ""
echo "[2/6] Cloning DeepSeek-VL2 repository..."
if [ ! -d "DeepSeek-VL2" ]; then
    git clone https://github.com/deepseek-ai/DeepSeek-VL2.git
    echo "✓ Repository cloned"
else
    echo "✓ Repository already exists"
fi

# Step 3: Install DeepSeek-VL2 dependencies
echo ""
echo "[3/6] Installing DeepSeek-VL2..."
cd DeepSeek-VL2
pip install -e . --quiet
cd /workspace
echo "✓ DeepSeek-VL2 installed"

# Step 4: Download model weights
echo ""
echo "[4/6] Downloading DeepSeek-VL2 model weights (~10GB)..."
echo "This may take several minutes..."
if [ ! -d "/workspace/models/deepseek-vl2" ]; then
    pip install huggingface-hub --quiet
    python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='deepseek-ai/deepseek-vl2',
    local_dir='/workspace/models/deepseek-vl2',
    local_dir_use_symlinks=False
)
"
    echo "✓ Model weights downloaded"
else
    echo "✓ Model weights already exist"
fi

# Step 5: Install MCP server dependencies
echo ""
echo "[5/6] Installing MCP server dependencies..."
cd /workspace/deepseek_mcp

# Copy server files if they exist locally
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
    echo "✓ MCP dependencies installed"
else
    echo "Warning: requirements.txt not found in /workspace/deepseek_mcp"
    echo "Please copy server files (mcp_server.py, inference.py, requirements.txt, config.yaml)"
    echo "to /workspace/deepseek_mcp/ before running the server."
fi

# Step 6: Test installation
echo ""
echo "[6/6] Testing installation..."
python3 << EOF
import sys
import torch

print("Python version:", sys.version)
print("PyTorch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("CUDA version:", torch.version.cuda)
    print("GPU:", torch.cuda.get_device_name(0))
    print("GPU memory:", f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

# Test model loading
try:
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        "/workspace/models/deepseek-vl2",
        trust_remote_code=True
    )
    print("✓ Model tokenizer loaded successfully")
except Exception as e:
    print(f"✗ Failed to load tokenizer: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "==================================="
    echo "✓ Setup completed successfully!"
    echo "==================================="
    echo ""
    echo "Next steps:"
    echo "1. Copy MCP server files to /workspace/deepseek_mcp/"
    echo "   - mcp_server.py"
    echo "   - inference.py"
    echo "   - config.yaml"
    echo ""
    echo "2. Test the server:"
    echo "   cd /workspace/deepseek_mcp"
    echo "   python test_server.py"
    echo ""
    echo "3. Run the server:"
    echo "   python mcp_server.py"
    echo ""
else
    echo ""
    echo "✗ Setup failed. Please check the error messages above."
    exit 1
fi
