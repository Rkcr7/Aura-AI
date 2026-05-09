#!/usr/bin/env bash
# ============================================================
# Aura AI — macOS launcher
# ============================================================
set -e
cd "$(dirname "$0")"

VENV=".venv"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV" ]; then
    echo "📦 Creating Python virtual environment…"
    python3 -m venv "$VENV"
fi

# Activate
source "$VENV/bin/activate"

# Install / update dependencies
echo "📥 Installing dependencies…"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Copy .env.example → .env if missing
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp ".env.example" ".env"
    echo "📄 Created .env from .env.example — fill in your API keys!"
fi

# Copy ai_providers.example.json → ai_providers.json if missing
if [ ! -f "ai_providers.json" ] && [ -f "ai_providers.example.json" ]; then
    cp "ai_providers.example.json" "ai_providers.json"
    echo "📄 Created ai_providers.json — add your AI provider API keys!"
fi

echo ""
echo "╔══════════════════════════════════════╗"
echo "║          Aura AI — macOS             ║"
echo "║  Global hotkeys require Accessibility║"
echo "║  System Settings → Privacy → Access. ║"
echo "╚══════════════════════════════════════╝"
echo ""

python main.py
