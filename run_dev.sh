#!/usr/bin/env bash
# ============================================================
# Aura AI — macOS DEV MODE launcher
# Enables verbose logging; screen capture protection is OFF
# ============================================================
set -e
cd "$(dirname "$0")"

VENV=".venv"
if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"
pip install -q --upgrade pip
pip install -q -r requirements.txt

export DEV_MODE=true
echo "⚠️  DEV_MODE=true — screen capture protection disabled"
echo "   Window WILL appear in screen recordings."
echo ""

python main.py
