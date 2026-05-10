# window_manager.py — macOS-native implementation for Aura AI
#
# Replaces the Windows ctypes/Win32 implementation entirely.
# Uses Apple's AppKit (via pyobjc) for all window management:
#   - Transparency       → NSWindow.setAlphaValue_()
#   - Always-on-top      → NSWindow.setLevel_(NSFloatingWindowLevel)
#   - Screen-capture     → NSWindow.setSharingType_(NSWindowSharingNone)
#   - Click-through      → NSWindow.setIgnoresMouseEvents_()
#   - Show/hide          → NSWindow.orderOut_() / orderFrontRegardless()
#   - Global hotkeys     → pynput (requires Accessibility permission)
#
# Public API is identical to the Windows version so main.py and api/ need no changes.

import os
import platform
import time
import tempfile
from typing import Optional
from threading import Thread

import orjson
import webview
from pynput import keyboard

# ---------------------------------------------------------------------------
# Scroll configuration — read lazily so .env values are honoured
# (module-level os.environ reads happen before core.config loads .env)
# ---------------------------------------------------------------------------
def _get_scroll_amount_px() -> int:
    """Return SCROLL_SPEED_PX from settings, falling back to 200."""
    try:
        from core.config import settings
        return getattr(settings, "SCROLL_SPEED_PX", 200)
    except Exception:
        return int(os.environ.get("SCROLL_SPEED_PX", "200"))


def _get_scroll_interval_ms() -> int:
    """Return SCROLL_INTERVAL_MS from settings, falling back to 50."""
    try:
        from core.config import settings
        return getattr(settings, "SCROLL_INTERVAL_MS", 50)
    except Exception:
        return int(os.environ.get("SCROLL_INTERVAL_MS", "50"))

# ---------------------------------------------------------------------------
# macOS Accessibility permission check
# ---------------------------------------------------------------------------
def _has_accessibility_permission() -> bool:
    """Return True if the process already has macOS Accessibility permission.

    Uses AXIsProcessTrusted() from the ApplicationServices framework.
    Passing {'AXTrustedCheckOptionPrompt': False} checks silently without
    showing the system prompt — we handle messaging ourselves.
    """
    if not IS_MACOS:
        return True
    try:
        import ctypes
        import ctypes.util
        lib = ctypes.cdll.LoadLibrary(
            ctypes.util.find_library("ApplicationServices") or
            "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
        )
        # AXIsProcessTrustedWithOptions is available macOS 10.9+
        lib.AXIsProcessTrustedWithOptions.restype = ctypes.c_bool
        lib.AXIsProcessTrustedWithOptions.argtypes = [ctypes.c_void_p]
        return lib.AXIsProcessTrustedWithOptions(None)
    except Exception:
        # Fall back to always returning True so we don't block startup
        return True

IS_MACOS = platform.system() == "Darwin"

if IS_MACOS:
    from AppKit import (
        NSApp,
        NSFloatingWindowLevel,
        NSNormalWindowLevel,
        NSWindowSharingNone,
    )
    from Foundation import NSPoint
else:
    # Graceful degradation if somehow imported on another platform
    NSApp = None
    NSFloatingWindowLevel = 8
    NSNormalWindowLevel = 0
    NSWindowSharingNone = 0
    NSPoint = None


# ---------------------------------------------------------------------------
# Internal helper — locate the Aura NSWindow
# ---------------------------------------------------------------------------
def _get_aura_ns_window():
    """Return the NSWindow instance for the 'Aura' window, or None."""
    if not IS_MACOS or NSApp is None:
        return None
    try:
        for w in NSApp.windows():
            if w.title() == "Aura":
                return w
        # Fallback: use the key (active) window
        main = NSApp.mainWindow()
        if main:
            return main
    except Exception as exc:
        print(f"⚠️  Could not locate Aura NSWindow: {exc}")
    return None


# ---------------------------------------------------------------------------
# WindowManager — core class
# ---------------------------------------------------------------------------
class WindowManager:
    """
    macOS-native window manager.
    Exposes the same public interface as the Windows version so that
    main.py and the REST API layer (api/config_api.py) work unchanged.
    """

    def __init__(self):
        """Initialise state for transparency, ghost mode, scrolling, and hotkey listeners."""
        self.is_macos = IS_MACOS
        self.current_transparency: float = 1.0
        self.is_ghost_mode: bool = False
        self.screen_share_monitor_active: bool = False
        self.hidden_screen_share_windows: set = set()

        # Continuous scroll state
        self.scrolling_up: bool = False
        self.scrolling_down: bool = False
        self.scroll_thread: Optional[Thread] = None

        # Hotkey listeners
        self.hotkey_listener = None
        self._scroll_listener = None

    # ------------------------------------------------------------------ #
    # Transparency                                                         #
    # ------------------------------------------------------------------ #

    def _enable_transparency(self) -> bool:
        """macOS windows support transparency natively — always True."""
        return True

    def set_window_handle(self, handle) -> None:
        """No-op: macOS uses NSApp to locate the window directly."""
        pass

    def set_transparency(self, transparency: float) -> bool:
        """
        Set window alpha (0.0 = invisible, 1.0 = fully opaque).
        Uses NSWindow.setAlphaValue_ — true native macOS transparency.
        """
        transparency = max(0.0, min(1.0, transparency))
        self.current_transparency = transparency
        try:
            ns_win = _get_aura_ns_window()
            if ns_win:
                ns_win.setAlphaValue_(transparency)
                ns_win.setOpaque_(transparency >= 1.0)
                print(f"✅ Window transparency set to {transparency * 100:.0f}%")
                return True
            print("⚠️  NSWindow not found for transparency change")
            return False
        except Exception as exc:
            print(f"❌ Error setting transparency: {exc}")
            return False

    def get_transparency(self) -> float:
        """Return the last-set alpha value (0.0 = invisible, 1.0 = opaque)."""
        return self.current_transparency

    def set_transparency_percent(self, percent: int) -> bool:
        """Set transparency from a 0–100 integer percentage."""
        return self.set_transparency(percent / 100.0)

    def make_transparent(self) -> bool:
        """40% opacity — ideal for stealth interview overlay."""
        return self.set_transparency(0.4)

    def make_semi_transparent(self) -> bool:
        """70% opacity."""
        return self.set_transparency(0.7)

    def make_opaque(self) -> bool:
        """Fully opaque."""
        return self.set_transparency(1.0)

    # ------------------------------------------------------------------ #
    # Always-on-top                                                        #
    # ------------------------------------------------------------------ #

    def set_always_on_top(self, on_top: bool) -> bool:
        """
        Float the window above all others using NSFloatingWindowLevel.
        This is the macOS equivalent of HWND_TOPMOST.
        """
        try:
            ns_win = _get_aura_ns_window()
            if ns_win:
                level = NSFloatingWindowLevel if on_top else NSNormalWindowLevel
                ns_win.setLevel_(level)
                status = "always-on-top" if on_top else "normal stacking"
                print(f"📌 Window set to {status}")
                return True
            print("⚠️  NSWindow not found for always-on-top")
            return False
        except Exception as exc:
            print(f"❌ Error setting always-on-top: {exc}")
            return False

    # ------------------------------------------------------------------ #
    # Screen-capture protection                                            #
    # ------------------------------------------------------------------ #

    def apply_capture_protection(self) -> bool:
        """
        Prevent this window from appearing in screen recordings and sharing.
        Uses NSWindowSharingNone — the macOS native equivalent of
        Windows' WDA_EXCLUDEFROMCAPTURE (SetWindowDisplayAffinity).

        Works with: QuickTime, screenshot tools, Zoom, Teams, Google Meet,
        OBS (when not using display capture), and most capture APIs that
        respect NSWindowSharingType.
        """
        try:
            ns_win = _get_aura_ns_window()
            if ns_win:
                ns_win.setSharingType_(NSWindowSharingNone)
                print("🛡️  Screen capture protection applied (NSWindowSharingNone)")
                return True
            print("⚠️  NSWindow not found for capture protection")
            return False
        except Exception as exc:
            print(f"❌ Error applying capture protection: {exc}")
            return False

    # ------------------------------------------------------------------ #
    # Ghost / click-through mode                                           #
    # ------------------------------------------------------------------ #

    def set_ghost_mode(self, enabled: bool) -> None:
        """
        Enable or disable click-through mode.
        Uses NSWindow.setIgnoresMouseEvents_ — native macOS pass-through.
        """
        try:
            ns_win = _get_aura_ns_window()
            if ns_win:
                ns_win.setIgnoresMouseEvents_(enabled)
                self.is_ghost_mode = enabled
                label = "Enabled (click-through)" if enabled else "Disabled (normal)"
                icon = "👻" if enabled else "🖱️"
                print(f"{icon} Ghost Mode {label}")
        except Exception as exc:
            print(f"❌ Error setting ghost mode: {exc}")

    def toggle_ghost_mode(self) -> None:
        """Flip ghost/click-through mode between enabled and disabled."""
        self.set_ghost_mode(not self.is_ghost_mode)

    # ------------------------------------------------------------------ #
    # Visibility (show / hide)                                             #
    # ------------------------------------------------------------------ #

    def toggle_visibility(self) -> None:
        """Toggle window visibility without changing focus order."""
        try:
            ns_win = _get_aura_ns_window()
            if ns_win:
                if ns_win.isVisible():
                    ns_win.orderOut_(None)
                    print("🕵️  Window hidden (stealth)")
                else:
                    ns_win.orderFrontRegardless()
                    self.set_always_on_top(True)
                    print("✨ Window shown (stealth — no focus steal)")
        except Exception as exc:
            print(f"❌ Error toggling visibility: {exc}")

    def hide_from_taskbar(self) -> bool:
        """
        macOS: Dock entries are controlled by the Info.plist LSUIElement key,
        not at runtime. pywebview sets this correctly by default.
        This is a deliberate no-op — the app already won't show in the Dock
        during stealth mode (window level handles that).
        """
        print("ℹ️  hide_from_taskbar: macOS handles this via window level (no-op)")
        return True

    # ------------------------------------------------------------------ #
    # Window movement                                                      #
    # ------------------------------------------------------------------ #

    def move_window(self, dx: int, dy: int) -> bool:
        """Move the window by (dx, dy) pixels without activating it."""
        try:
            ns_win = _get_aura_ns_window()
            if ns_win:
                frame = ns_win.frame()
                # macOS origin is bottom-left; dy is intentionally inverted
                new_x = frame.origin.x + dx
                new_y = frame.origin.y - dy
                ns_win.setFrameOrigin_(NSPoint(new_x, new_y))
                print(f"🎯 Window moved ({dx:+d}px, {dy:+d}px)")
                return True
            return False
        except Exception as exc:
            print(f"❌ Error moving window: {exc}")
            return False

    # ------------------------------------------------------------------ #
    # Proctoring stealth mode                                              #
    # ------------------------------------------------------------------ #

    def enable_proctoring_stealth_mode(self) -> bool:
        """Combine ghost mode + capture protection + always-on-top + 70% opacity."""
        try:
            print("🎯 Enabling PROCTORING STEALTH MODE…")
            self.set_ghost_mode(True)
            self.apply_capture_protection()
            self.set_always_on_top(True)
            self.set_transparency(0.7)
            print("✅ PROCTORING STEALTH MODE ENABLED")
            print("   📌 Option+Z  — Toggle visibility")
            print("   📌 Option+X  — Toggle ghost mode")
            print("   📌 Option+1/2/3 — Transparency presets")
            print("   ⚠️  DO NOT click the window — focus change may be detected!")
            return True
        except Exception as exc:
            print(f"❌ Error enabling proctoring stealth mode: {exc}")
            return False

    # ------------------------------------------------------------------ #
    # Window info                                                          #
    # ------------------------------------------------------------------ #

    def get_window_info(self) -> dict:
        """Return a snapshot of the current window state as a plain dict."""
        return {
            "transparency": self.current_transparency,
            "transparency_percent": int(self.current_transparency * 100),
            "is_transparent": self.current_transparency < 1.0,
            "platform_supported": self.is_macos,
            "window_handle": None,
            "screen_share_monitor_active": self.screen_share_monitor_active,
            "hidden_screen_share_windows": len(self.hidden_screen_share_windows),
        }

    # ------------------------------------------------------------------ #
    # Continuous scrolling (key-held)                                      #
    # ------------------------------------------------------------------ #

    def _continuous_scroll_loop(self) -> None:
        """Background thread — smooth scroll while key is held."""
        interval = _get_scroll_interval_ms() / 1000.0
        while self.scrolling_up or self.scrolling_down:
            try:
                amount = _get_scroll_amount_px()
                if webview.windows:
                    win = webview.windows[0]
                    if self.scrolling_up:
                        win.evaluate_js(
                            f'document.getElementById("conversation-stream")'
                            f'?.scrollBy({{top:-{amount},behavior:"smooth"}})'
                        )
                    elif self.scrolling_down:
                        win.evaluate_js(
                            f'document.getElementById("conversation-stream")'
                            f'?.scrollBy({{top:{amount},behavior:"smooth"}})'
                        )
            except Exception:
                pass
            time.sleep(interval)

    def _start_scroll(self, direction: str) -> None:
        """Begin continuous scrolling in *direction* ('up' or 'down') on a daemon thread."""
        self.scrolling_up = direction == "up"
        self.scrolling_down = direction == "down"
        if not self.scroll_thread or not self.scroll_thread.is_alive():
            self.scroll_thread = Thread(
                target=self._continuous_scroll_loop, daemon=True
            )
            self.scroll_thread.start()

    def _stop_scroll(self) -> None:
        """Signal the scroll thread to stop at the next iteration."""
        self.scrolling_up = False
        self.scrolling_down = False

    # ------------------------------------------------------------------ #
    # Global hotkey listener                                               #
    # ------------------------------------------------------------------ #

    def start_hotkey_listener(self) -> None:
        """Start global keyboard shortcuts using AppKit NSEvent monitors.

        NSEvent.addGlobalMonitorForEventsMatchingMask_handler_ is the native
        macOS API for system-wide key monitoring.  It runs inside the existing
        NSApplication run loop (started by pywebview) so there is no CFRunLoop
        conflict and no SIGTRAP.

        event.charactersIgnoringModifiers() returns the base letter regardless
        of which modifier keys are held, so Option+Z always yields 'z' — no
        unicode translation table is required.

        Requires Accessibility permission in
        System Settings → Privacy & Security → Accessibility.
        """
        print("⌨️  Starting global hotkey listener (NSEvent)…")
        if _has_accessibility_permission():
            print("   ✅ Accessibility permission granted — hotkeys active")
        else:
            print("   ⚠️  Accessibility permission NOT granted — hotkeys will not work!")
            print("      Fix: System Settings → Privacy & Security → Accessibility")
            print("      Add Terminal (or your IDE) to the list, then restart the app.")

        # ── Command file bridge ──────────────────────────────────────────
        def _send_command(data: dict) -> None:
            """Atomically write a command to the temp file (tmp → os.replace).
            Prevents main.py's polling reader from seeing a half-written JSON blob.
            """
            try:
                cmd_file = os.path.join(tempfile.gettempdir(), "aura_command.json")
                tmp_file = f"{cmd_file}.tmp"
                data["source"] = "global_hotkey"
                with open(tmp_file, "wb") as fh:
                    fh.write(orjson.dumps(data))
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(tmp_file, cmd_file)
            except Exception as exc:
                print(f"⚠️  Could not write hotkey command: {exc}")

        # ── Action map keyed by base character ───────────────────────────
        _HOTKEY_ACTIONS: dict = {
            'z': lambda: self.toggle_visibility(),
            'x': lambda: self.toggle_ghost_mode(),
            '1': lambda: self.set_transparency(1.0),
            '2': lambda: self.set_transparency(0.7),
            '3': lambda: self.set_transparency(0.4),
            'm': lambda: _send_command({"command": "toggle_mic_mute"}),
            'u': lambda: _send_command({"command": "toggle_universal_mute"}),
            'q': lambda: _send_command({"command": "switch_preset", "preset_key": "primary"}),
            'w': lambda: _send_command({"command": "switch_preset", "preset_key": "secondary"}),
            'e': lambda: _send_command({"command": "switch_preset", "preset_key": "auto"}),
            'f': lambda: _send_command({"command": "toggle_vision_mode"}),
            'v': lambda: _send_command({"command": "switch_vision_model"}),
            's': lambda: _send_command({"command": "capture_screenshot"}),
            'a': lambda: _send_command({"command": "process_screenshots"}),
            'd': lambda: _send_command({"command": "reset_screenshot_queue"}),
            'r': lambda: _send_command({"command": "reset_interview"}),
        }

        # ── NSEvent mask constants ────────────────────────────────────────
        _NSKeyDownMask    = 1 << 10   # 1024
        _NSKeyUpMask      = 1 << 11   # 2048
        _NSAltKeyMask     = 1 << 19   # NSAlternateKeyMask
        _KEY_ARROW_UP     = 126       # kVK_UpArrow
        _KEY_ARROW_DOWN   = 125       # kVK_DownArrow

        # ── Key-down handler ─────────────────────────────────────────────
        def _on_key_down(event) -> None:
            """Dispatch hotkeys and start scroll on ⌥↑ / ⌥↓."""
            if not (event.modifierFlags() & _NSAltKeyMask):
                return

            key_code = event.keyCode()

            # Scroll ─────────────────────────────────────────────────────
            if key_code == _KEY_ARROW_UP:
                self._start_scroll("up")
                return
            if key_code == _KEY_ARROW_DOWN:
                self._start_scroll("down")
                return

            # Hotkey ─────────────────────────────────────────────────────
            # charactersIgnoringModifiers() gives 'z' even for Option+Z
            chars = event.charactersIgnoringModifiers()
            if chars:
                action = _HOTKEY_ACTIONS.get(chars.lower())
                if action:
                    Thread(target=action, daemon=True).start()

        # ── Key-up handler ───────────────────────────────────────────────
        def _on_key_up(event) -> None:
            """Stop scroll when ↑/↓ or Option is released."""
            key_code = event.keyCode()
            flags    = event.modifierFlags()

            if key_code in (_KEY_ARROW_UP, _KEY_ARROW_DOWN):
                self._stop_scroll()
            # Option released → stop any ongoing scroll
            if not (flags & _NSAltKeyMask):
                self._stop_scroll()

        # ── Register monitors ────────────────────────────────────────────
        try:
            from AppKit import NSEvent  # already imported at module level; re-bind locally
            self._key_down_monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
                _NSKeyDownMask, _on_key_down
            )
            self._key_up_monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
                _NSKeyUpMask, _on_key_up
            )
            print("✅ Global hotkey listener active (NSEvent)")
            print("   ⌥Z=hide  ⌥X=ghost  ⌥1-3=opacity  ⌥M=mute  ⌥S=screenshot  ⌥A=analyze")
        except Exception as exc:
            print(f"❌ Failed to register NSEvent monitors: {exc}")
            print("   💡 Grant Accessibility permission and restart the app.")

    # ------------------------------------------------------------------ #
    # Screen-share indicator stubs (Windows-only feature — not on macOS)  #
    # ------------------------------------------------------------------ #

    def find_window_by_title(self, title: str):
        """Stub — Windows-only feature, not applicable on macOS."""
        return None

    def find_screen_share_indicators(self) -> list:
        """Stub — screen-share indicator detection is Windows-only."""
        return []

    def hide_screen_share_indicator(self, hwnd) -> bool:
        """Stub — hiding screen-share indicators is Windows-only."""
        return False

    def hide_all_screen_share_indicators(self) -> int:
        """Stub — hiding all screen-share indicators is Windows-only."""
        return 0

    def start_screen_share_monitor(self) -> None:
        """Stub — screen-share indicator monitor is Windows-only; prints a notice on macOS."""
        print("ℹ️  Screen-share indicator monitor: not applicable on macOS")

    def stop_screen_share_monitor(self) -> None:
        """Stub — screen-share monitor is Windows-only; no-op on macOS."""
        pass


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------
window_manager = WindowManager()


# ---------------------------------------------------------------------------
# Module-level convenience functions
# Identical public interface as the Windows version — main.py / config_api.py
# call these without any modification.
# ---------------------------------------------------------------------------

def apply_capture_protection(pywebview_window=None) -> bool:
    """Apply macOS-native screen-capture protection (NSWindowSharingNone)."""
    return window_manager.apply_capture_protection()


def find_aura_window() -> bool:
    """Confirm the Aura NSWindow is reachable via NSApp."""
    ns_win = _get_aura_ns_window()
    if ns_win:
        print(f"🔍 Aura NSWindow located: '{ns_win.title()}'")
        return True
    print("⚠️  Aura NSWindow not yet available")
    return False


def set_app_always_on_top(on_top: bool) -> bool:
    """Module-level alias: set or clear the always-on-top window level."""
    return window_manager.set_always_on_top(on_top)


def set_app_transparency(transparency: float) -> bool:
    """Module-level alias: set window alpha (0.0–1.0)."""
    return window_manager.set_transparency(transparency)


def set_app_transparency_percent(percent: int) -> bool:
    """Module-level alias: set window transparency from a 0–100 integer."""
    return window_manager.set_transparency_percent(percent)


def make_app_transparent() -> bool:
    """Module-level alias: set window to 40% opacity (stealth overlay)."""
    return window_manager.make_transparent()


def make_app_semi_transparent() -> bool:
    """Module-level alias: set window to 70% opacity."""
    return window_manager.make_semi_transparent()


def make_app_opaque() -> bool:
    """Module-level alias: set window to fully opaque (100%)."""
    return window_manager.make_opaque()


def get_transparency_info() -> dict:
    """Module-level alias: return the current window state snapshot."""
    return window_manager.get_window_info()
