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
# Scroll configuration (read from .env via os.environ)
# ---------------------------------------------------------------------------
SCROLL_AMOUNT_PX = int(os.environ.get("SCROLL_SPEED_PX", "200"))
SCROLL_INTERVAL_MS = int(os.environ.get("SCROLL_INTERVAL_MS", "50"))

# ---------------------------------------------------------------------------
# macOS AppKit / Quartz imports
# ---------------------------------------------------------------------------
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
        return self.current_transparency

    def set_transparency_percent(self, percent: int) -> bool:
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
        interval = SCROLL_INTERVAL_MS / 1000.0
        while self.scrolling_up or self.scrolling_down:
            try:
                if webview.windows:
                    win = webview.windows[0]
                    if self.scrolling_up:
                        win.evaluate_js(
                            f'document.getElementById("conversation-stream")'
                            f'?.scrollBy({{top:-{SCROLL_AMOUNT_PX},behavior:"smooth"}})'
                        )
                    elif self.scrolling_down:
                        win.evaluate_js(
                            f'document.getElementById("conversation-stream")'
                            f'?.scrollBy({{top:{SCROLL_AMOUNT_PX},behavior:"smooth"}})'
                        )
            except Exception:
                pass
            time.sleep(interval)

    def _start_scroll(self, direction: str) -> None:
        self.scrolling_up = direction == "up"
        self.scrolling_down = direction == "down"
        if not self.scroll_thread or not self.scroll_thread.is_alive():
            self.scroll_thread = Thread(
                target=self._continuous_scroll_loop, daemon=True
            )
            self.scroll_thread.start()

    def _stop_scroll(self) -> None:
        self.scrolling_up = False
        self.scrolling_down = False

    # ------------------------------------------------------------------ #
    # Global hotkey listener                                               #
    # ------------------------------------------------------------------ #

    def start_hotkey_listener(self) -> None:
        """
        Start listening for global keyboard shortcuts using pynput.

        macOS requirement: the app (or terminal running it) must have
        Accessibility permission.
        Grant it in:  System Settings → Privacy & Security → Accessibility

        Hotkeys use the Option key (⌥), which pynput maps as keyboard.Key.alt.
        This matches the original Windows Alt+key shortcuts exactly.
        """
        print("⌨️  Starting global hotkey listener (pynput)…")
        print("   ℹ️  macOS: Accessibility permission required for global hotkeys.")
        print("      Grant in: System Settings → Privacy & Security → Accessibility")

        # ── Command file bridge (for commands that need the browser) ──────
        def _send_command(data: dict) -> None:
            try:
                cmd_file = os.path.join(tempfile.gettempdir(), "aura_command.json")
                data["source"] = "global_hotkey"
                with open(cmd_file, "wb") as fh:
                    fh.write(orjson.dumps(data))
            except Exception as exc:
                print(f"⚠️  Could not write hotkey command: {exc}")

        # ── Hotkey → action map ──────────────────────────────────────────
        HOTKEYS = {
            # Visibility & ghost
            "<alt>z": lambda: self.toggle_visibility(),
            "<alt>x": lambda: self.toggle_ghost_mode(),

            # Transparency presets  (⌥1 opaque → ⌥3 most transparent)
            "<alt>1": lambda: self.set_transparency(1.0),
            "<alt>2": lambda: self.set_transparency(0.7),
            "<alt>3": lambda: self.set_transparency(0.4),

            # Microphone / mute
            "<alt>m": lambda: _send_command({"command": "toggle_mic_mute"}),
            "<alt>u": lambda: _send_command({"command": "toggle_universal_mute"}),

            # AI preset switching
            "<alt>q": lambda: _send_command({"command": "switch_preset", "preset_key": "primary"}),
            "<alt>w": lambda: _send_command({"command": "switch_preset", "preset_key": "secondary"}),
            "<alt>e": lambda: _send_command({"command": "switch_preset", "preset_key": "auto"}),

            # Vision mode
            "<alt>f": lambda: _send_command({"command": "toggle_vision_mode"}),
            "<alt>v": lambda: _send_command({"command": "switch_vision_model"}),

            # Screenshot queue
            "<alt>s": lambda: _send_command({"command": "capture_screenshot"}),
            "<alt>a": lambda: _send_command({"command": "process_screenshots"}),
            "<alt>d": lambda: _send_command({"command": "reset_screenshot_queue"}),

            # Reset interview
            "<alt>r": lambda: _send_command({"command": "reset_interview"}),
        }

        # ── Separate listener for held-key scrolling ─────────────────────
        _active_keys: set = set()

        def _on_press(key) -> None:
            _active_keys.add(key)
            is_alt = any(
                k in _active_keys
                for k in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r)
            )
            if is_alt:
                if key == keyboard.Key.up:
                    self._start_scroll("up")
                elif key == keyboard.Key.down:
                    self._start_scroll("down")

        def _on_release(key) -> None:
            _active_keys.discard(key)
            if key in (keyboard.Key.up, keyboard.Key.down):
                self._stop_scroll()

        try:
            self.hotkey_listener = keyboard.GlobalHotKeys(HOTKEYS)
            self.hotkey_listener.start()

            self._scroll_listener = keyboard.Listener(
                on_press=_on_press, on_release=_on_release
            )
            self._scroll_listener.start()

            print("✅ Global hotkey listener active")
            print("   ⌥Z=hide  ⌥X=ghost  ⌥1-3=opacity  ⌥M=mute  ⌥S=screenshot  ⌥A=analyze")
        except Exception as exc:
            print(f"❌ Failed to start hotkey listener: {exc}")
            print("   💡 Grant Accessibility permission and restart the app.")

    # ------------------------------------------------------------------ #
    # Screen-share indicator stubs (Windows-only feature — not on macOS)  #
    # ------------------------------------------------------------------ #

    def find_window_by_title(self, title: str):
        return None

    def find_screen_share_indicators(self) -> list:
        return []

    def hide_screen_share_indicator(self, hwnd) -> bool:
        return False

    def hide_all_screen_share_indicators(self) -> int:
        return 0

    def start_screen_share_monitor(self) -> None:
        print("ℹ️  Screen-share indicator monitor: not applicable on macOS")

    def stop_screen_share_monitor(self) -> None:
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
    return window_manager.set_always_on_top(on_top)


def set_app_transparency(transparency: float) -> bool:
    return window_manager.set_transparency(transparency)


def set_app_transparency_percent(percent: int) -> bool:
    return window_manager.set_transparency_percent(percent)


def make_app_transparent() -> bool:
    return window_manager.make_transparent()


def make_app_semi_transparent() -> bool:
    return window_manager.make_semi_transparent()


def make_app_opaque() -> bool:
    return window_manager.make_opaque()


def get_transparency_info() -> dict:
    return window_manager.get_window_info()
