#!/bin/bash
# setup.sh — One-click setup for RAG Visual Chatbot
# Run: chmod +x setup.sh && ./setup.sh

set -e
echo "========================================"
echo "  RAG Visual Chatbot - Setup Script"
echo "========================================"

# ── 1. Python virtual environment ────────────────────────────────────────────
echo ""
echo "[1/5] Creating Python virtual environment..."
cd backend
python3 -m venv venv
source venv/bin/activate

# ── 2. Install Python packages ────────────────────────────────────────────────
echo ""
echo "[2/5] Installing Python dependencies (this may take a few minutes)..."
pip install --upgrade pip
pip install -r requirements.txt

# ── 3. Generate extension icons ───────────────────────────────────────────────
echo ""
echo "[3/5] Generating extension icons..."
cd ..
python3 scripts/generate_icons.py

# ── 4. Install Ollama ─────────────────────────────────────────────────────────
echo ""
echo "[4/5] Installing Ollama (local LLM runtime)..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama already installed."
fi

# ── 5. Pull LLM model ─────────────────────────────────────────────────────────
echo ""
echo "[5/5] Downloading Llama 3.2 model (~2GB, free & unlimited)..."
ollama pull llama3.2

echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "NEXT STEPS:"
echo ""
echo "1. Start the backend:"
echo "   cd backend && source venv/bin/activate && python app.py"
echo ""
echo "2. Load Chrome Extension:"
echo "   - Open Chrome → chrome://extensions/"
echo "   - Enable 'Developer mode' (top right toggle)"
echo "   - Click 'Load unpacked'"
echo "   - Select the 'extension/' folder"
echo ""
echo "3. Visit any webpage, hover over an image, click 'Analyze Image'!"
echo ""
echo "Models downloaded automatically on first run:"
echo "  • BLIP (image captioning) — ~990MB from HuggingFace"
echo "  • all-MiniLM-L6-v2 (embeddings) — ~80MB from HuggingFace"
echo "  • llama3.2 (LLM) — ~2GB via Ollama"
echo ""
