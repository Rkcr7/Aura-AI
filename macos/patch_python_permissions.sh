#!/bin/bash
# Adds NSMicrophoneUsageDescription / NSCameraUsageDescription to the Homebrew
# python@3.14 framework's bundled Python.app.
#
# Why this is necessary: Aura runs as `python main.py`, but Homebrew's
# framework Python unconditionally re-execs every invocation through its own
# Resources/Python.app/Contents/MacOS/Python — this happens even for a
# trivial `python3 -c "..."` with no GUI code involved. That means macOS's
# TCC always attributes microphone/camera requests to that exact bundle
# (org.python.python), no matter how Aura itself is launched or wrapped.
# Without NSMicrophoneUsageDescription/NSCameraUsageDescription declared in
# ITS Info.plist, TCC has no prompt text to show and silently denies access
# instead of asking the user.
#
# Re-run this script whenever `brew upgrade/reinstall python@3.14` wipes the
# keys back out (symptom: mic/camera permission denies with no system dialog,
# and `plutil -p` on the path below no longer shows the two Usage keys).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

REAL_PY="$("$PROJECT_ROOT/venv/bin/python3" -c 'import sys, os; print(os.path.realpath(sys.executable))')"
FRAMEWORK_VERSION_DIR="$(dirname "$(dirname "$REAL_PY")")"   # .../Python.framework/Versions/3.14
APP_BUNDLE="$FRAMEWORK_VERSION_DIR/Resources/Python.app"
INFO_PLIST="$APP_BUNDLE/Contents/Info.plist"

if [ ! -f "$INFO_PLIST" ]; then
    echo "❌ Could not find Python.app Info.plist at: $INFO_PLIST"
    exit 1
fi

echo "🔧 Patching: $INFO_PLIST"
/usr/libexec/PlistBuddy -c "Delete :NSMicrophoneUsageDescription" "$INFO_PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string Aura needs microphone access to transcribe your interview responses in real time." "$INFO_PLIST"

/usr/libexec/PlistBuddy -c "Delete :NSCameraUsageDescription" "$INFO_PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :NSCameraUsageDescription string Aura needs camera access for upcoming video-based features." "$INFO_PLIST"

echo "🔏 Re-signing: $APP_BUNDLE"
codesign --force --deep --sign - "$APP_BUNDLE"

echo "✅ Done. Fully quit Aura (and any running python main.py process) and relaunch to get the permission prompts."
