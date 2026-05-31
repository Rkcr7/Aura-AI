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

# ── SSL Certificate Fix (macOS) ─────────────────────────────────────────────
# macOS Python doesn't bundle CA certificates, causing:
#   [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
# on all HTTPS/WSS connections (Deepgram WebSocket, AI providers, etc.)
# We point Python at certifi's bundle (already in requirements.txt).
SSL_CERT="$(python3 -c 'import certifi; print(certifi.where())' 2>/dev/null)"
if [ -n "$SSL_CERT" ]; then
    export SSL_CERT_FILE="$SSL_CERT"
    export REQUESTS_CA_BUNDLE="$SSL_CERT"
    echo "🔐 SSL certificates: $SSL_CERT"
else
    # Fallback: macOS system certificate store
    SYS_CERT="/etc/ssl/cert.pem"
    if [ -f "$SYS_CERT" ]; then
        export SSL_CERT_FILE="$SYS_CERT"
        export REQUESTS_CA_BUNDLE="$SYS_CERT"
        echo "🔐 SSL certificates: $SYS_CERT (system fallback)"
    else
        echo "⚠️  Could not locate CA bundle — SSL connections may fail"
    fi
fi
# ────────────────────────────────────────────────────────────────────────────

# Kill any stale process on port 8002 (silent when nothing is bound)
pids=$(lsof -ti :8002 2>/dev/null)
if [ -n "$pids" ]; then
    echo "$pids" | xargs kill -9 2>/dev/null && echo "🧹 Cleared stale process on :8002"
fi

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
echo "╔══════════════════════════════════════════╗"
echo "║           Aura AI — macOS                ║"
echo "║  Hotkeys need: Input Monitoring           ║"
echo "║  System Settings → Privacy → Input Mon.  ║"
echo "╚══════════════════════════════════════════╝"
echo ""

python main.py
