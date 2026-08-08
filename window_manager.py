# --- window_manager.py ---
# This module contains the core logic for managing the application's desktop window.
# Its primary responsibility is to apply the necessary settings to prevent the window
# from being captured by screen recording or sharing software (e.g., Teams, Zoom, OBS).
# This is the "stealth" feature of the Aura application.

import os
import ctypes
import ctypes.wintypes as wintypes
import webview
import time
import tkinter as tk
import platform
from typing import Optional
from threading import Thread
from pynput import keyboard

# --- Scroll Configuration ---
# Configurable via .env — controls Alt+Up/Down scroll behaviour
# SCROLL_SPEED_PX: pixels per scroll tick (higher = faster). Default: 200
# SCROLL_INTERVAL_MS: milliseconds between ticks while key is held. Default: 50
SCROLL_AMOUNT_PX = int(os.environ.get("SCROLL_SPEED_PX", "200"))
SCROLL_INTERVAL_MS = int(os.environ.get("SCROLL_INTERVAL_MS", "50"))

# --- Win32 API Constants ---
# These flags are used with the SetWindowDisplayAffinity function.
# WDA_EXCLUDEFROMCAPTURE is a comprehensive flag that prevents the window from being
# captured by most common methods, rendering it as a black rectangle in recordings.
WDA_EXCLUDEFROMCAPTURE = 0x00000011
SW_HIDE = 0
SW_SHOW = 5
SW_SHOWNOACTIVATE = 4  # Show window without giving it focus - crucial for stealth

# --- Win32 Function Loading ---
# We use the ctypes library to load functions directly from user32.dll, a core
# Windows library for UI management. This gives us low-level control over the window.

# Load the user32 library
_user32 = ctypes.windll.user32

# Define the function signature for SetWindowDisplayAffinity
# This tells ctypes what kind of arguments the function expects (a window handle and a flag)
# and what it returns (a boolean indicating success).
_user32.SetWindowDisplayAffinity.restype  = wintypes.BOOL
_user32.SetWindowDisplayAffinity.argtypes = (wintypes.HWND, wintypes.DWORD)

# Define the function signature for FindWindowW
# This is a fallback method to find a window by its title if the primary method fails.
_user32.FindWindowW.restype               = wintypes.HWND
_user32.FindWindowW.argtypes              = (wintypes.LPCWSTR, wintypes.LPCWSTR)

# Define function signatures for ShowWindow and IsWindowVisible
_user32.ShowWindow.argtypes = (wintypes.HWND, wintypes.INT)
_user32.ShowWindow.restype = wintypes.BOOL
_user32.IsWindowVisible.argtypes = (wintypes.HWND,)
_user32.IsWindowVisible.restype = wintypes.BOOL

# Define the function signature for GetWindowDisplayAffinity
#   BOOL GetWindowDisplayAffinity(HWND hWnd, DWORD *pdwAffinity)
# This is the read-back counterpart of SetWindowDisplayAffinity: it lets us
# actually confirm the protection took effect instead of assuming it did.
# The lookup is guarded so an older/unusual Windows build that does not export
# the symbol keeps working with the previous best-effort check.
try:
    _user32.GetWindowDisplayAffinity.restype = wintypes.BOOL
    _user32.GetWindowDisplayAffinity.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    _HAS_GET_DISPLAY_AFFINITY = True
except AttributeError:
    _HAS_GET_DISPLAY_AFFINITY = False

# IsWindow is used as the fallback verification check
_user32.IsWindow.argtypes = (wintypes.HWND,)
_user32.IsWindow.restype = wintypes.BOOL

# Screen sharing indicator detection constants
SCREEN_SHARE_INDICATORS = [
    # Generic Windows indicators
    "Screen sharing indicator",
    "You're sharing your screen",
    "Screen Share Notification", 
    "Screen Recording Indicator",
    "Sharing indicator",
    "Recording indicator",
    "You are sharing your screen",
    "Screen share active",
    "Recording in progress",
    
    # Browser-specific indicators
    "Chrome is sharing your screen",
    "Microsoft Edge is sharing your screen", 
    "Firefox is sharing your screen",
    "Safari is sharing your screen",
    "Opera is sharing your screen",
    "Brave is sharing your screen",
    "is sharing your screen",
    "wants to share your screen",
    "Screen capture in progress",
    "Display capture active",
    
    # Video conferencing platforms
    "Zoom is sharing your screen",
    "Microsoft Teams is sharing your screen",
    "Google Meet is sharing your screen",
    "Skype is sharing your screen",
    "Discord is sharing your screen",
    "Slack is sharing your screen",
    "WebEx is sharing your screen",
    "GoToMeeting is sharing your screen",
    "BlueJeans is sharing your screen",
    "Jitsi is sharing your screen",
    "BigBlueButton is sharing your screen",
    
    # Screen recording software
    "OBS is recording your screen",
    "OBS Studio is recording",
    "Camtasia is recording",
    "Bandicam is recording",
    "Fraps is recording",
    "XSplit is recording",
    "Streamlabs is recording",
    "Action! is recording",
    "Nvidia ShadowPlay",
    "AMD ReLive",
    "Windows Game Bar recording",
    "Xbox Game Bar recording",
    
    # Remote desktop and sharing tools
    "TeamViewer is sharing your screen",
    "AnyDesk is sharing your screen", 
    "Chrome Remote Desktop",
    "Windows Remote Desktop",
    "VNC is sharing your screen",
    "LogMeIn is sharing your screen",
    "Splashtop is sharing your screen",
    "Parsec is sharing your screen",
    
    # Generic patterns
    "sharing your desktop",
    "recording your desktop", 
    "capturing your screen",
    "desktop sharing active",
    "screen capture active",
    "display recording",
    "monitor sharing",
    "window sharing",
    "application sharing",
    "presentation mode active",
    
    # Notification variations
    "Screen share notification",
    "Recording notification", 
    "Capture notification",
    "Privacy indicator",
    "Camera and microphone access",
    "Microphone access",
    "Screen access granted",
    
    # Development and testing tools
    "Selenium is controlling",
    "Puppeteer is controlling",
    "Playwright is controlling",
    "Automated testing in progress",
    "Browser automation active"
]

# Window classes that can host a sharing/recording indicator. A class match
# alone is not enough: several of these are generic shells, so the title must
# also carry one of the verification keywords below.
SCREEN_SHARE_CLASSES = [
    # Browser notifications
    "Chrome_WidgetWin_1",  # Chrome screen share notification
    "MozillaDialogClass",  # Firefox screen share notification
    "EdgeWebView2",        # Edge screen share notification
    "OperaWindowClass",    # Opera browser
    "BraveWindowClass",    # Brave browser
    
    # Windows system notifications
    "NotificationPresenterHost",  # Windows notification
    "Windows.UI.Core.CoreWindow",  # Windows 10/11 notifications
    "ApplicationFrameHost",        # Windows 10/11 app frame
    "Shell_TrayWnd",              # System tray notifications
    
    # Video conferencing
    "ZPContentViewWndClass",      # Zoom
    "ZPFloatToolbarClass",        # Zoom toolbar
    "TeamsWebView",               # Microsoft Teams
    "SkypeWindowClass",           # Skype
    "DiscordWindowClass",         # Discord
    "SlackWindowClass",           # Slack
    
    # Screen recording software
    "Qt5QWindowIcon",             # OBS Studio
    "OBSWindowClass",             # OBS
    "CamtasiaStudioWindowClass",  # Camtasia
    "BandicamWindowClass",        # Bandicam
    "XSplitWindowClass",          # XSplit
    "StreamlabsWindowClass",      # Streamlabs
    "FrapsWindowClass",           # Fraps
    "ActionWindowClass",          # Mirillis Action!
    
    # Remote desktop tools
    "TeamViewer_DesktopWindowClass",  # TeamViewer
    "AnyDeskWindowClass",             # AnyDesk
    "VNCWindowClass",                 # VNC viewers
    "LogMeInWindowClass",             # LogMeIn
    "SplashtopWindowClass",           # Splashtop
    "ParsecWindowClass",              # Parsec
    
    # System recording indicators
    "GameBarDisplayCaptureIndicator", # Xbox Game Bar
    "NvidiaGeForceExperience",        # Nvidia ShadowPlay
    "AMDReliveWindowClass",           # AMD ReLive
    
    # Generic Windows classes
    "NotifyIconOverflowWindow",       # System tray overflow
    "ToolbarWindow32",                # Toolbar notifications
    "Static",                         # Static text windows
    "Button"                          # Button controls
]

# A class match only counts as an indicator when the title contains one of these.
SCREEN_SHARE_VERIFICATION_KEYWORDS = [
    "sharing", "screen", "record", "capture", "desktop",
    "monitor", "display", "streaming", "broadcast", "meeting",
    "presentation", "remote", "control", "access"
]

# Precomputed lowercase needles. find_screen_share_indicators() matches these
# against every top-level window on every scan tick, so lowercasing them once at
# import removes ~110 redundant .lower() calls per window per tick.
_INDICATORS_LOWER = tuple(text.lower() for text in SCREEN_SHARE_INDICATORS)
_SHARE_CLASSES_LOWER = tuple(name.lower() for name in SCREEN_SHARE_CLASSES)
_VERIFICATION_KEYWORDS_LOWER = tuple(k.lower() for k in SCREEN_SHARE_VERIFICATION_KEYWORDS)

class WindowManager:
    def __init__(self):
        self.hwnd: Optional[int] = None
        self.is_windows = platform.system() == "Windows"
        self.current_transparency = 1.0
        self.is_ghost_mode = False
        self.screen_share_monitor_active = False
        self.hidden_screen_share_windows = set()
        
        # Continuous scrolling state
        self.scrolling_up = False
        self.scrolling_down = False
        self.scroll_thread = None
        self.hotkey_listener = None
        self.alt_pressed = False

        if self.is_windows:
            self._setup_win32_api_definitions()

    def _setup_win32_api_definitions(self):
        """Defines all necessary Win32 API functions, constants, and types."""
        # Constants
        self.GWL_EXSTYLE = -20
        self.WS_EX_LAYERED = 0x80000
        self.WS_EX_TOPMOST = 0x8
        self.WS_EX_TRANSPARENT = 0x20
        self.WS_EX_TOOLWINDOW = 0x80  # Added for taskbar hiding
        self.LWA_ALPHA = 0x2
        self.HWND_TOPMOST = -1
        self.HWND_NOTOPMOST = -2
        self.SWP_NOMOVE = 0x2
        self.SWP_NOSIZE = 0x1
        self.SWP_NOACTIVATE = 0x10  # Don't activate the window when moving
        self.SWP_NOZORDER = 0x4     # Don't change Z-order

        self.user32 = ctypes.windll.user32
        
        # Correctly define SetWindowLongPtr and GetWindowLongPtr for 32/64-bit
        is_64bit = platform.architecture()[0] == '64bit'
        if is_64bit:
            self.GetWindowLongPtr = self.user32.GetWindowLongPtrW
            self.SetWindowLongPtr = self.user32.SetWindowLongPtrW
        else:
            self.GetWindowLongPtr = self.user32.GetWindowLongW
            self.SetWindowLongPtr = self.user32.SetWindowLongW

        self.GetWindowLongPtr.restype = wintypes.LPARAM
        self.GetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int]
        self.SetWindowLongPtr.restype = wintypes.LPARAM
        self.SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LPARAM]

        # SetLayeredWindowAttributes
        self.SetLayeredWindowAttributes = self.user32.SetLayeredWindowAttributes
        self.SetLayeredWindowAttributes.argtypes = [wintypes.HWND, wintypes.COLORREF, wintypes.BYTE, wintypes.DWORD]
        self.SetLayeredWindowAttributes.restype = wintypes.BOOL

        # SetWindowPos
        self.SetWindowPos = self.user32.SetWindowPos
        self.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        self.SetWindowPos.restype = wintypes.BOOL

        # EnumWindows for finding all windows
        self.EnumWindows = self.user32.EnumWindows
        self.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
        self.EnumWindows.restype = wintypes.BOOL

        # GetWindowText for getting window titles
        self.GetWindowTextW = self.user32.GetWindowTextW
        self.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.GetWindowTextW.restype = ctypes.c_int

        # GetClassName for getting window class names
        self.GetClassNameW = self.user32.GetClassNameW
        self.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.GetClassNameW.restype = ctypes.c_int

        # Define RECT structure for GetWindowRect
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)
            ]
        
        self.RECT = RECT

        # GetWindowRect for getting window position and size
        self.GetWindowRect = self.user32.GetWindowRect
        self.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
        self.GetWindowRect.restype = wintypes.BOOL
            
    def set_window_handle(self, window_handle: int):
        """Set the window handle for transparency operations"""
        self.hwnd = window_handle
        if self.is_windows and self.hwnd:
            self._enable_transparency()
        
    def _enable_transparency(self):
        """Enable transparency capability for the window"""
        if not self.is_windows or not self.hwnd:
            return False
            
        try:
            # Get current window style
            ex_style = self.GetWindowLongPtr(self.hwnd, self.GWL_EXSTYLE)
            
            # Add layered window style if not present
            if not (ex_style & self.WS_EX_LAYERED):
                new_style = ex_style | self.WS_EX_LAYERED
                self.SetWindowLongPtr(self.hwnd, self.GWL_EXSTYLE, new_style)
                
            return True
        except Exception as e:
            print(f"Error enabling transparency: {e}")
            return False
    
    def set_transparency(self, transparency: float) -> bool:
        """
        Set window transparency level
        Args:
            transparency: Float between 0.0 (fully transparent) and 1.0 (fully opaque)
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_windows or not self.hwnd:
            print("Transparency not supported on this platform or no window handle")
            return False
            
        # Clamp transparency value
        transparency = max(0.0, min(1.0, transparency))
        self.current_transparency = transparency
        
        try:
            # Convert to Windows alpha value (0-255)
            alpha = int(transparency * 255)
            
            # Apply transparency
            result = self.SetLayeredWindowAttributes(
                self.hwnd,
                0,  # colorkey (not used)
                alpha,  # alpha value
                self.LWA_ALPHA  # use alpha
            )
            
            if result:
                print(f"✅ Window transparency set to {transparency*100:.0f}%")
                return True
            else:
                print("❌ Failed to set window transparency")
                return False
                
        except Exception as e:
            print(f"❌ Error setting transparency: {e}")
            return False
    
    def get_transparency(self) -> float:
        """Get current transparency level"""
        return self.current_transparency
    
    def set_transparency_percent(self, percent: int) -> bool:
        """
        Set transparency as percentage
        Args:
            percent: Integer between 0 (fully transparent) and 100 (fully opaque)
        """
        transparency = percent / 100.0
        return self.set_transparency(transparency)
    
    def make_transparent(self) -> bool:
        """Make window 60% transparent (40% opacity) - good for interviews"""
        return self.set_transparency(0.4)
    
    def make_semi_transparent(self) -> bool:
        """Make window semi-transparent (70% opacity)"""
        return self.set_transparency(0.7)
    
    def make_opaque(self) -> bool:
        """Make window fully opaque"""
        return self.set_transparency(1.0)
    
    def find_window_by_title(self, title: str) -> Optional[int]:
        """Find window handle by title"""
        if not self.is_windows:
            return None
            
        try:
            FindWindowW = self.user32.FindWindowW
            FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
            FindWindowW.restype = wintypes.HWND
            
            hwnd = FindWindowW(None, title)
            if hwnd:
                self.set_window_handle(hwnd)
                return hwnd
            return None
        except Exception as e:
            print(f"Error finding window: {e}")
            return None

    def find_screen_share_indicators(self) -> list:
        """Find all screen sharing indicator windows"""
        if not self.is_windows:
            return []
        
        found_windows = []
        
        def enum_windows_callback(hwnd, lparam):
            try:
                # Get window title
                title_buffer = ctypes.create_unicode_buffer(512)
                title_length = self.GetWindowTextW(hwnd, title_buffer, 512)
                title = title_buffer.value if title_length > 0 else ""
                
                # Get window class name
                class_buffer = ctypes.create_unicode_buffer(256)
                class_length = self.GetClassNameW(hwnd, class_buffer, 256)
                class_name = class_buffer.value if class_length > 0 else ""
                
                # Check if this looks like a screen sharing indicator
                is_indicator = False
                
                # Check title for screen sharing keywords
                title_lower = title.lower()
                for indicator_text in _INDICATORS_LOWER:
                    if indicator_text in title_lower:
                        is_indicator = True
                        break
                
                # Check class name for known screen sharing/recording classes
                if not is_indicator:
                    class_name_lower = class_name.lower()
                    for share_class in _SHARE_CLASSES_LOWER:
                        if share_class in class_name_lower:
                            # Additional verification for these classes
                            if any(keyword in title_lower for keyword in _VERIFICATION_KEYWORDS_LOWER):
                                is_indicator = True
                                break
                
                if is_indicator and _user32.IsWindowVisible(hwnd):
                    found_windows.append({
                        'hwnd': hwnd,
                        'title': title,
                        'class': class_name
                    })
                    print(f"🔍 Found screen share indicator: '{title}' (Class: {class_name})")
                
            except Exception as e:
                # Continue enumeration even if one window fails
                pass
            
            return True  # Continue enumeration
        
        try:
            callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            callback = callback_type(enum_windows_callback)
            self.EnumWindows(callback, 0)
        except Exception as e:
            print(f"❌ Error enumerating windows: {e}")
        
        return found_windows

    def hide_screen_share_indicator(self, hwnd: int) -> bool:
        """Hide a specific screen sharing indicator window"""
        if not self.is_windows:
            return False
        
        try:
            # Method 1: Try to hide the window completely
            result = _user32.ShowWindow(hwnd, SW_HIDE)
            if result:
                print(f"✅ Hidden screen share indicator (HWND: {hex(hwnd)})")
                self.hidden_screen_share_windows.add(hwnd)
                return True
            
            # Method 2: Try to move it off-screen if hiding failed
            try:
                self.SetWindowPos(
                    hwnd, 0, 
                    -10000, -10000,  # Move far off-screen
                    0, 0,  # Don't change size
                    self.SWP_NOSIZE
                )
                print(f"✅ Moved screen share indicator off-screen (HWND: {hex(hwnd)})")
                return True
            except:
                pass
            
            # Method 3: Try to minimize the window
            try:
                _user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
                print(f"✅ Minimized screen share indicator (HWND: {hex(hwnd)})")
                return True
            except:
                pass
                
            print(f"❌ Failed to hide screen share indicator (HWND: {hex(hwnd)})")
            return False
            
        except Exception as e:
            print(f"❌ Error hiding screen share indicator: {e}")
            return False

    def hide_all_screen_share_indicators(self) -> int:
        """Find and hide all screen sharing indicators"""
        if not self.is_windows:
            return 0
        
        indicators = self.find_screen_share_indicators()
        hidden_count = 0
        
        for indicator in indicators:
            hwnd = indicator['hwnd']
            if hwnd not in self.hidden_screen_share_windows:
                if self.hide_screen_share_indicator(hwnd):
                    hidden_count += 1
        
        if hidden_count > 0:
            print(f"🕵️ Successfully hidden {hidden_count} screen sharing indicator(s)")
        
        return hidden_count

    def start_screen_share_monitor(self):
        """Start monitoring for screen sharing indicators and auto-hide them"""
        if not self.is_windows or self.screen_share_monitor_active:
            return
        
        print("🔍 Starting screen sharing indicator monitor...")
        self.screen_share_monitor_active = True
        
        def monitor_thread():
            while self.screen_share_monitor_active:
                try:
                    self.hide_all_screen_share_indicators()
                    time.sleep(1.0)  # Check every second
                except Exception as e:
                    print(f"❌ Error in screen share monitor: {e}")
                    time.sleep(2.0)  # Wait longer on error
        
        monitor = Thread(target=monitor_thread, daemon=True)
        monitor.start()
        print("✅ Screen sharing indicator monitor started")

    def stop_screen_share_monitor(self):
        """Stop monitoring for screen sharing indicators"""
        if self.screen_share_monitor_active:
            self.screen_share_monitor_active = False
            print("🛑 Screen sharing indicator monitor stopped")
    
    def set_always_on_top(self, on_top: bool) -> bool:
        """
        Set window to always stay on top
        Args:
            on_top: True to set always on top, False to remove
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_windows or not self.hwnd:
            print("Always on top not supported on this platform or no window handle")
            return False
            
        try:
            # Add debugging
            print(f"🔧 Attempting to set always on top: {on_top}, HWND: {self.hwnd}")
            
            hwnd_insert_after = self.HWND_TOPMOST if on_top else self.HWND_NOTOPMOST
            
            # Call SetWindowPos with proper error handling
            result = self.SetWindowPos(
                self.hwnd,
                hwnd_insert_after,
                0, 0, 0, 0,  # x, y, width, height (ignored due to flags)
                self.SWP_NOMOVE | self.SWP_NOSIZE  # Don't move or resize
            )
            
            if result:
                status = "on top" if on_top else "normal"
                print(f"✅ Window set to {status}")
                return True
            else:
                # Get the last error code for debugging
                error_code = ctypes.windll.kernel32.GetLastError()
                print(f"❌ SetWindowPos failed (Error {error_code}), trying alternative method...")
                
                # Try alternative method using window style
                return self._set_always_on_top_alternative(on_top)
                
        except Exception as e:
            print(f"❌ Error setting always on top: {e}")
            return False

    def _set_always_on_top_alternative(self, on_top: bool) -> bool:
        """
        Alternative method to set always on top using window extended styles
        """
        try:
            # Get current extended window style
            ex_style = self.GetWindowLongPtr(self.hwnd, self.GWL_EXSTYLE)
            
            if on_top:
                # Add topmost style
                new_style = ex_style | self.WS_EX_TOPMOST
            else:
                # Remove topmost style
                new_style = ex_style & ~self.WS_EX_TOPMOST
            
            # Set the new style
            result = self.SetWindowLongPtr(self.hwnd, self.GWL_EXSTYLE, new_style)
            
            if result or ex_style != new_style:
                # Force window update
                self.user32.SetWindowPos(
                    self.hwnd, 0, 0, 0, 0, 0,
                    self.SWP_NOMOVE | self.SWP_NOSIZE | 0x0020  # SWP_FRAMECHANGED
                )
                status = "on top" if on_top else "normal"
                print(f"✅ Window set to {status} (alternative method)")
                return True
            else:
                print("❌ Alternative method also failed")
                return False
                
        except Exception as e:
            print(f"❌ Error in alternative always-on-top method: {e}")
            return False

    def get_window_info(self) -> dict:
        """Get current window transparency info"""
        return {
            "transparency": self.current_transparency,
            "transparency_percent": int(self.current_transparency * 100),
            "is_transparent": self.current_transparency < 1.0,
            "platform_supported": self.is_windows,
            "window_handle": self.hwnd,
            "screen_share_monitor_active": self.screen_share_monitor_active,
            "hidden_screen_share_windows": len(self.hidden_screen_share_windows)
        }

    def set_ghost_mode(self, enabled: bool):
        """Enable or disable 'click-through' (ghost) mode."""
        if not self.is_windows or not self.hwnd:
            return

        try:
            current_style = self.GetWindowLongPtr(self.hwnd, self.GWL_EXSTYLE)
            if enabled:
                new_style = current_style | self.WS_EX_TRANSPARENT
                print("👻 Ghost Mode Enabled (click-through)")
            else:
                new_style = current_style & ~self.WS_EX_TRANSPARENT
                print("🖱️ Ghost Mode Disabled (normal interaction)")

            self.SetWindowLongPtr(self.hwnd, self.GWL_EXSTYLE, new_style)
            self.is_ghost_mode = enabled
            
            # Force re-apply always-on-top after style change
            self.set_always_on_top(True)
            
        except Exception as e:
            print(f"❌ Error setting ghost mode: {e}")

    def toggle_ghost_mode(self):
        """Toggles the ghost mode on or off."""
        self.set_ghost_mode(not self.is_ghost_mode)

    def enable_proctoring_stealth_mode(self):
        """
        Enable complete stealth mode for proctoring environments.
        
        This mode combines multiple stealth features:
        - Ghost mode (click-through) to prevent accidental focus
        - Screen capture protection
        - Always on top but without focus
        - Hidden from taskbar
        
        Use global hotkeys (Alt+Z, Alt+X, etc.) to interact safely.
        """
        if not self.is_windows or not self.hwnd:
            print("❌ Proctoring stealth mode requires Windows and valid window handle")
            return False
        
        try:
            print("🎯 Enabling PROCTORING STEALTH MODE...")
            
            # 1. Enable ghost mode (click-through)
            self.set_ghost_mode(True)
            
            # 2. Hide from taskbar
            self.hide_from_taskbar()
            
            # 3. Set always on top but without focus
            self.set_always_on_top(True)
            
            # 4. Make semi-transparent for visibility without being obvious
            self.set_transparency(0.7)
            
            print("✅ PROCTORING STEALTH MODE ENABLED")
            print("   🚨 IMPORTANT: Use ONLY global hotkeys to interact:")
            print("   📌 Alt+Z: Toggle visibility (no focus change)")
            print("   📌 Alt+X: Toggle ghost mode")
            print("   📌 Alt+1/2/3: Adjust transparency")
            print("   📌 DO NOT click on the window - it will trigger focus detection!")
            
            return True
            
        except Exception as e:
            print(f"❌ Error enabling proctoring stealth mode: {e}")
            return False

    def move_window(self, dx: int, dy: int) -> bool:
        """
        Move window by specified offset without changing focus (stealth movement).
        
        Args:
            dx: Horizontal offset in pixels (positive = right, negative = left)
            dy: Vertical offset in pixels (positive = down, negative = up)
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_windows or not self.hwnd:
            print("❌ Window movement requires Windows and valid window handle")
            return False
        
        try:
            # Get current window position
            rect = self.RECT()
            if not self.GetWindowRect(self.hwnd, ctypes.byref(rect)):
                print("❌ Failed to get current window position")
                return False
            
            # Calculate new position
            new_x = rect.left + dx
            new_y = rect.top + dy
            
            # Move window without activating it
            result = self.SetWindowPos(
                self.hwnd,
                0,  # hwndInsertAfter (ignored due to SWP_NOZORDER)
                new_x, new_y,  # new position
                0, 0,  # width, height (ignored due to SWP_NOSIZE)
                self.SWP_NOSIZE | self.SWP_NOACTIVATE | self.SWP_NOZORDER
            )
            
            if result:
                direction = ""
                if dx > 0:
                    direction += f"right {dx}px "
                elif dx < 0:
                    direction += f"left {abs(dx)}px "
                if dy > 0:
                    direction += f"down {dy}px"
                elif dy < 0:
                    direction += f"up {abs(dy)}px"
                
                print(f"🎯 Window moved {direction.strip()} (stealth - no focus change)")
                return True
            else:
                print("❌ Failed to move window")
                return False
                
        except Exception as e:
            print(f"❌ Error moving window: {e}")
            return False


    def toggle_visibility(self):
        """Toggle the window's visibility without changing focus (stealth mode)."""
        if not self.is_windows or not self.hwnd:
            print("Window visibility control not supported or no window handle.")
            return

        if _user32.IsWindowVisible(self.hwnd):
            _user32.ShowWindow(self.hwnd, SW_HIDE)
            print("🕵️‍ Window hidden via global hotkey.")
        else:
            # Use SW_SHOWNOACTIVATE to show window without giving it focus
            # This prevents proctoring software from detecting focus changes
            _user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)
            print("✨ Window shown via global hotkey (stealth - no focus change).")
            # Re-apply always-on-top state when showing the window
            self.set_always_on_top(True)

    def hide_from_taskbar(self) -> bool:
        """Hide the window from the taskbar by setting WS_EX_TOOLWINDOW."""
        if not self.is_windows or not self.hwnd:
            print("Cannot hide from taskbar: Not on Windows or no window handle")
            return False
        try:
            # Get current extended style
            ex_style = self.GetWindowLongPtr(self.hwnd, self.GWL_EXSTYLE)
            # Add WS_EX_TOOLWINDOW and remove WS_EX_APPWINDOW (0x40000) if present
            new_style = (ex_style | self.WS_EX_TOOLWINDOW) & ~0x40000
            # Set the new style
            self.SetWindowLongPtr(self.hwnd, self.GWL_EXSTYLE, new_style)
            print("✅ Window hidden from taskbar")
            return True
        except Exception as e:
            print(f"❌ Error hiding from taskbar: {e}")
            return False

    def _start_hotkey_listener_thread(self):
        """The actual listener thread for global hotkeys."""
        print("🎧 Starting global hotkey listener thread...")

        def on_hide_show():
            self.toggle_visibility()
            return False

        def on_toggle_ghost():
            self.toggle_ghost_mode()
            return False

        def on_toggle_vision_mode():
            """Toggle vision mode (Alt+V)"""
            self.send_vision_command("toggle_vision_mode")
            return False

        def on_capture_screenshot():
            """Capture screenshot (Alt+S)"""
            self.send_vision_command("capture_screenshot")
            return False

        def on_process_screenshots():
            """Process screenshots with AI (Alt+P)"""
            self.send_vision_command("process_screenshots")
            return False

        def on_switch_primary():
            """Switch to primary AI preset (Alt+Q)"""
            self.send_preset_switch_signal("primary")
            return False

        def on_switch_secondary():
            """Switch to secondary AI preset (Alt+W)"""
            self.send_preset_switch_signal("secondary")
            return False

        def on_auto_select():
            """Auto-select best available AI preset (Alt+E)"""
            self.send_context_aware_command("auto_select_preset")
            return False

        def on_switch_vision_model():
            """Switch vision model (Alt+T)"""
            self.send_vision_switch_command("switch_vision_model")
            return False

        def on_transparency_transparent():
            """Set window to transparent (40% opacity) - Alt+1"""
            self.send_transparency_command("transparent")
            return False

        def on_transparency_semi():
            """Set window to semi-transparent (70% opacity) - Alt+2"""
            self.send_transparency_command("semi")
            return False

        def on_transparency_opaque():
            """Set window to opaque (100% opacity) - Alt+3"""
            self.send_transparency_command("opaque")
            return False

        def on_toggle_mic_mute():
            """Toggle microphone mute (Alt+M)"""
            self.send_audio_command("toggle_mic_mute")
            return False

        def on_toggle_universal_mute():
            """Toggle universal mute/pause (Alt+U)"""
            self.send_audio_command("toggle_universal_mute")
            return False

        def on_reset_screenshot_queue():
            """Reset/clear screenshot queue (Alt+R)"""
            self.send_vision_command("reset_screenshot_queue")
            return False

        def on_enable_proctoring_stealth():
            """Enable proctoring stealth mode (Alt+Shift+S)"""
            self.enable_proctoring_stealth_mode()
            return False

        def on_move_left():
            """Move window left (Alt+Left)"""
            self.move_window(-20, 0)
            return False

        def on_move_right():
            """Move window right (Alt+Right)"""
            self.move_window(20, 0)
            return False

        def on_move_up():
            """Move window up (Alt+I) - SWAPPED"""
            self.move_window(0, -20)
            return False

        def on_move_down():
            """Move window down (Alt+J) - SWAPPED"""
            self.move_window(0, 20)
            return False

        def on_reset_interview():
            """Reset interview session (Alt+O)"""
            self.send_interview_command("reset_interview")
            return False

        # Add single press scroll handlers for initial response
        def on_scroll_up_start():
            """Start continuous scroll up (Alt+Up)"""
            if not self.scrolling_up:
                self.scrolling_up = True
                self._start_continuous_scrolling()
                print("🔼 Starting continuous scroll up")
            return False

        def on_scroll_down_start():
            """Start continuous scroll down (Alt+Down)"""
            if not self.scrolling_down:
                self.scrolling_down = True
                self._start_continuous_scrolling()
                print("🔽 Starting continuous scroll down")
            return False

        # Create a separate listener for key releases to stop scrolling
        def start_release_listener():
            """Background thread to handle key releases for stopping continuous scroll"""
            import threading
            
            def on_key_release(key):
                try:
                    if key == keyboard.Key.up and self.scrolling_up:
                        self.scrolling_up = False
                        print("🛑 Stopped continuous scroll up")
                    elif key == keyboard.Key.down and self.scrolling_down:
                        self.scrolling_down = False
                        print("🛑 Stopped continuous scroll down")
                except:
                    pass

            def on_key_press(key):
                # We don't need to handle press here since GlobalHotKeys handles it
                pass

            release_listener = keyboard.Listener(
                on_press=on_key_press,
                on_release=on_key_release,
                suppress=False
            )
            release_listener.start()
            release_listener.join()

        # Start the release listener in background
        release_thread = Thread(target=start_release_listener, daemon=True)
        release_thread.start()

        # Regular hotkeys using the proven GlobalHotKeys approach
        hotkey_map = {
            '<alt>+x': on_toggle_ghost,
            '<alt>+z': on_hide_show,
            '<alt>+v': on_toggle_vision_mode,  # Toggle vision mode
            '<alt>+s': on_capture_screenshot,  # Capture screenshot (replaces screen share hide)
            '<alt>+p': on_process_screenshots, # Process screenshots
            '<alt>+r': on_reset_screenshot_queue, # Reset screenshot queue
            '<alt>+q': on_switch_primary,      # Switch to primary preset
            '<alt>+w': on_switch_secondary,    # Switch to secondary preset
            '<alt>+e': on_auto_select,         # Auto-select best AI preset
            '<alt>+t': on_switch_vision_model,   # Switch vision model
            '<alt>+m': on_toggle_mic_mute,     # Toggle microphone mute
            '<alt>+u': on_toggle_universal_mute, # Toggle universal mute (pause)
            '<alt>+1': on_transparency_transparent,  # 40% opacity (transparent)
            '<alt>+2': on_transparency_semi,         # 70% opacity (semi-transparent)
            '<alt>+3': on_transparency_opaque,       # 100% opacity (opaque)
            '<alt>+<shift>+s': on_enable_proctoring_stealth,  # Enable proctoring stealth mode
            '<alt>+<left>': on_move_left,      # Move window left
            '<alt>+<right>': on_move_right,    # Move window right
            '<alt>+i': on_move_up,             # Move window up (SWAPPED)
            '<alt>+j': on_move_down,           # Move window down (SWAPPED)
            '<alt>+o': on_reset_interview,     # Reset interview session
            '<alt>+<up>': on_scroll_up_start,  # Start continuous scroll up (NEW)
            '<alt>+<down>': on_scroll_down_start,  # Start continuous scroll down (NEW)
        }
        
        with keyboard.GlobalHotKeys(hotkey_map) as h:
            h.join()

    def send_preset_switch_signal(self, preset_key: str):
        """Send preset switch signal to the application"""
        try:
            from datetime import datetime
            print(f"🔄 Global hotkey triggered: Switching to {preset_key} preset")
            self._write_command_file({
                "command": "switch_preset",
                "preset_key": preset_key,
                "timestamp": datetime.now().isoformat(),
                "source": "global_hotkey"
            })
        except Exception as e:
            print(f"❌ Error sending preset switch signal: {e}")

    def send_vision_command(self, command: str):
        """Send vision-related command to the application"""
        try:
            from datetime import datetime
            print(f"👁️ Global hotkey triggered: {command}")
            self._write_command_file({
                "command": command,
                "timestamp": datetime.now().isoformat(),
                "source": "global_hotkey"
            })
        except Exception as e:
            print(f"❌ Error sending vision command: {e}")

    def send_transparency_command(self, level: str):
        """Send transparency command to the application"""
        try:
            from datetime import datetime
            print(f"🔍 Global hotkey triggered: set_transparency_{level}")
            self._write_command_file({
                "command": "set_transparency",
                "level": level,
                "timestamp": datetime.now().isoformat(),
                "source": "global_hotkey"
            })
        except Exception as e:
            print(f"❌ Error sending transparency command: {e}")

    def send_audio_command(self, command: str):
        """Send audio-related command to the application"""
        try:
            from datetime import datetime
            print(f"🎤 Global hotkey triggered: {command}")
            self._write_command_file({
                "command": command,
                "timestamp": datetime.now().isoformat(),
                "source": "global_hotkey"
            })
        except Exception as e:
            print(f"❌ Error sending audio command: {e}")

    def send_context_aware_command(self, command: str):
        """Send command for context-aware actions like auto-selecting presets."""
        try:
            from datetime import datetime
            print(f"🔄 Global hotkey triggered: {command}")
            self._write_command_file({
                "command": "context_aware_action",
                "action": command,
                "timestamp": datetime.now().isoformat(),
                "source": "global_hotkey"
            })
        except Exception as e:
            print(f"❌ Error sending context-aware command: {e}")

    def send_vision_switch_command(self, command: str):
        """Send command to switch vision model"""
        try:
            from datetime import datetime
            print(f"👁️ Global hotkey triggered: {command}")
            self._write_command_file({
                "command": command,
                "timestamp": datetime.now().isoformat(),
                "source": "global_hotkey"
            })
        except Exception as e:
            print(f"❌ Error sending vision switch command: {e}")

    def send_interview_command(self, command: str):
        """Send interview-related command to the application"""
        try:
            from datetime import datetime
            print(f"🎤 Global hotkey triggered: {command}")
            self._write_command_file({
                "command": command,
                "timestamp": datetime.now().isoformat(),
                "source": "global_hotkey"
            })
        except Exception as e:
            print(f"❌ Error sending interview command: {e}")

    def send_scroll_command(self, direction: str):
        """Send scroll command to the application"""
        try:
            from datetime import datetime
            print(f"📜 Global hotkey triggered: scroll_{direction} ({SCROLL_AMOUNT_PX}px)")
            self._write_command_file({
                "command": "scroll",
                "direction": direction,
                "amount": SCROLL_AMOUNT_PX,
                "timestamp": datetime.now().isoformat(),
                "source": "global_hotkey"
            })
        except Exception as e:
            print(f"❌ Error sending scroll command: {e}")

    def _continuous_scroll_loop(self):
        """Continuous scrolling loop that runs while scroll keys are held"""
        import time
        while self.scrolling_up or self.scrolling_down:
            try:
                if self.scrolling_up:
                    self.send_scroll_command("up")
                elif self.scrolling_down:
                    self.send_scroll_command("down")
                
                # Wait between scroll commands for smooth scrolling
                time.sleep(SCROLL_INTERVAL_MS / 1000)
            except Exception as e:
                print(f"❌ Error in continuous scroll loop: {e}")
                break
        
        # Reset scroll thread when loop exits
        self.scroll_thread = None
        print("🔄 Continuous scroll loop ended")

    def _start_continuous_scrolling(self):
        """Start the continuous scrolling thread if not already running"""
        if self.scroll_thread is None or not self.scroll_thread.is_alive():
            self.scroll_thread = Thread(target=self._continuous_scroll_loop, daemon=True)
            self.scroll_thread.start()
            print("🔄 Started continuous scroll loop")

    def _write_command_file(self, command_data: dict):
        """Write command to temp file for inter-process communication"""
        import tempfile
        import json
        import os
        
        # Write command to a temp file that could be monitored
        temp_dir = tempfile.gettempdir()
        command_file = os.path.join(temp_dir, "aura_command.json")
        
        with open(command_file, "w") as f:
            json.dump(command_data, f)
        
        print(f"📄 Command written to: {command_file}")

    def start_hotkey_listener(self):
        """Starts the global hotkey listener in a separate thread."""
        if not self.is_windows:
            print("Global hotkeys not supported on this platform.")
            return

        print("🚀 Initializing global hotkey listener...")
        print("   Alt+X: Toggle ghost mode (click-through)")
        print("   Alt+Z: Toggle window visibility (stealth - no focus)")
        print("   Alt+Left/Right Arrow: Move window left/right (stealth - no focus)")
        print("   Alt+I: Move window up (stealth - no focus)")
        print("   Alt+J: Move window down (stealth - no focus)")
        print("   Alt+Up Arrow: Continuous scroll up (hold for continuous)")
        print("   Alt+Down Arrow: Continuous scroll down (hold for continuous)")
        print("   Alt+V: Toggle vision mode")
        print("   Alt+S: Capture screenshot")
        print("   Alt+P: Process screenshots with AI")
        print("   Alt+R: Reset screenshot queue")
        print("   Alt+O: Reset interview session")
        print("   Alt+Q: Switch to primary AI preset")
        print("   Alt+W: Switch to secondary AI preset")
        print("   Alt+E: Auto-select best AI preset")
        print("   Alt+T: Switch vision model")
        print("   Alt+M: Toggle microphone mute")
        print("   Alt+U: Toggle universal mute (pause)")
        print("   Alt+1: Set transparent (40% opacity)")
        print("   Alt+2: Set semi-transparent (70% opacity)")
        print("   Alt+3: Set opaque (100% opacity)")
        print("   Alt+Shift+S: Enable proctoring stealth mode")
        
        # Ensure we have the handle before starting
        if not self.hwnd:
            if not self.find_window_by_title("Aura"):
                 print("❌ Cannot start hotkey listener: Aura window not found.")
                 return
        
        listener_thread = Thread(target=self._start_hotkey_listener_thread, daemon=True)
        listener_thread.start()

# Global instance
window_manager = WindowManager()

# Convenience functions for easy use
def set_app_transparency(transparency: float) -> bool:
    """Set app window transparency (0.0 to 1.0)"""
    return window_manager.set_transparency(transparency)

def set_app_transparency_percent(percent: int) -> bool:
    """Set app window transparency as percentage (0 to 100)"""
    return window_manager.set_transparency_percent(percent)

def make_app_transparent() -> bool:
    """Make app window 60% transparent (good for interviews)"""
    return window_manager.make_transparent()

def make_app_semi_transparent() -> bool:
    """Make app window semi-transparent"""
    return window_manager.make_semi_transparent()

def make_app_opaque() -> bool:
    """Make app window fully opaque"""
    return window_manager.make_opaque()

def find_aura_window() -> bool:
    """Find and set Aura window for transparency control"""
    hwnd = window_manager.find_window_by_title("Aura")
    return hwnd is not None

def set_app_always_on_top(on_top: bool) -> bool:
    """Set app window to always stay on top"""
    return window_manager.set_always_on_top(on_top)

def get_transparency_info() -> dict:
    """Get current transparency information"""
    return window_manager.get_window_info()

def hide_screen_share_indicators() -> int:
    """Hide all screen sharing indicators and return count hidden"""
    return window_manager.hide_all_screen_share_indicators()

def start_screen_share_monitor():
    """Start automatically monitoring and hiding screen share indicators"""
    window_manager.start_screen_share_monitor()

def stop_screen_share_monitor():
    """Stop monitoring screen share indicators"""
    window_manager.stop_screen_share_monitor()

def enable_proctoring_stealth_mode():
    """Enable complete stealth mode for proctoring environments"""
    return window_manager.enable_proctoring_stealth_mode()

def move_window(dx: int, dy: int) -> bool:
    """Move window by specified offset without changing focus"""
    return window_manager.move_window(dx, dy)

def test_screen_share_detection():
    """Test function to show all currently detected screen sharing indicators"""
    print("🔍 Testing screen share indicator detection...")
    indicators = window_manager.find_screen_share_indicators()
    
    if not indicators:
        print("✅ No screen sharing indicators currently detected")
        return []
    
    print(f"🚨 Found {len(indicators)} screen sharing indicator(s):")
    for i, indicator in enumerate(indicators, 1):
        print(f"   {i}. Title: '{indicator['title']}'")
        print(f"      Class: '{indicator['class']}'") 
        print(f"      HWND: {hex(indicator['hwnd'])}")
        print()
    
    return indicators

def apply_capture_protection(window):
    """
    Applies display affinity to exclude the window from screen capture.

    This function is the heart of the "stealth" feature. It first tries to get
    the window handle directly from a private pywebview attribute and, if that fails,
    falls back to searching for the window by its title.

    Args:
        window: The pywebview window object.
    """
    hwnd = None
    print("🛡️ APPLYING SCREEN CAPTURE PROTECTION...")

    # --- Method 1: Get handle from pywebview's private attribute ---
    # This is the preferred method as it's direct and not dependent on the window title.
    # We use getattr for safety, in case this private attribute changes in future versions.
    hwnd = getattr(window, '_hwnd', None)
    print(f"🔍 Method 1 (window._hwnd): {hex(hwnd) if hwnd else 'Not found'}")

    # --- Method 2: Fallback to finding the window by title ---
    # If the private attribute doesn't exist, we use a classic Win32 function.
    if not hwnd:
        print("⚠️ Private attribute not found, trying title search...")
        # A small delay is crucial here. It gives the OS time to register the
        # native window after the 'shown' event has fired.
        time.sleep(0.2)
        hwnd = _user32.FindWindowW(None, window.title)
        print(f"🔍 Method 2 (FindWindowW with title '{window.title}'): {hex(hwnd) if hwnd else 'Not found'}")

    # --- Method 3: Try multiple search attempts with delay ---
    if not hwnd:
        print("⚠️ Trying multiple search attempts...")
        for attempt in range(5):
            time.sleep(0.05)
            hwnd = _user32.FindWindowW(None, "Aura")
            if hwnd:
                print(f"🔍 Method 3 (attempt {attempt + 1}): Found {hex(hwnd)}")
                break
        
    # --- Apply the Protection ---
    if not hwnd:
        print("❌ CRITICAL: Could not obtain window handle! Screen capture protection NOT applied!")
        print("   This means the window WILL be visible in screen recordings!")
        return False

    print(f"🛡️ Applying WDA_EXCLUDEFROMCAPTURE (0x{WDA_EXCLUDEFROMCAPTURE:08X}) to window {hex(hwnd)}...")
    success = _user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)

    if success:
        print(f"✅ SUCCESS: Window {hex(hwnd)} is now HIDDEN from screen capture!")
        print("   🎯 Window will appear as BLACK RECTANGLE in recordings/screen sharing")
        
        # Set window handle and hide from taskbar
        window_manager.set_window_handle(hwnd)
        window_manager.hide_from_taskbar()
        
        # Start screen share indicator monitoring
        window_manager.start_screen_share_monitor()
        
        # Verify the protection was applied
        verify_protection(hwnd)
        return True
    else:
        # If the function fails, we get the last error code from the OS for debugging.
        error_code = ctypes.GetLastError()
        print(f"❌ FAILED: SetWindowDisplayAffinity failed! Error Code: {error_code}")
        print("   🚨 WARNING: Window WILL be visible in screen recordings!")
        return False

def verify_protection(hwnd) -> Optional[bool]:
    """Verify that capture protection is actually applied.

    Returns True when the window's display affinity reads back as
    WDA_EXCLUDEFROMCAPTURE, False when it reads back as something else, and
    None when verification was not possible (API unavailable, call failed, or
    an unexpected error). Diagnostic only - this never raises and the result
    can safely be ignored.
    """
    try:
        # Try to get current display affinity (this is a read-only check)
        print(f"🔬 Verifying protection on window {hex(hwnd)}...")
        
        # Read the affinity back so this is a real confirmation, not a guess.
        if _HAS_GET_DISPLAY_AFFINITY:
            affinity = wintypes.DWORD(0)
            if _user32.GetWindowDisplayAffinity(hwnd, ctypes.byref(affinity)):
                if affinity.value == WDA_EXCLUDEFROMCAPTURE:
                    print(f"✅ CONFIRMED: display affinity is WDA_EXCLUDEFROMCAPTURE (0x{affinity.value:08X})")
                    return True
                print(f"❌ MISMATCH: display affinity is 0x{affinity.value:08X}, expected 0x{WDA_EXCLUDEFROMCAPTURE:08X}")
                print("   🚨 WARNING: Window may still be visible in screen recordings!")
                return False
            print(f"⚠️ GetWindowDisplayAffinity failed (Error Code: {ctypes.GetLastError()}) - falling back to handle check")
        else:
            print("⚠️ GetWindowDisplayAffinity unavailable on this system - falling back to handle check")

        # Fallback (previous behaviour): a valid handle is weak evidence only.
        is_window_valid = _user32.IsWindow(hwnd)
        if is_window_valid:
            print("✅ Window handle is valid - protection likely applied")
        else:
            print("❌ Window handle is invalid - protection may have failed")
        return None
            
    except Exception as e:
        print(f"⚠️ Could not verify protection: {e}")


# --- Example Usage (for testing this module directly) ---
if __name__ == '__main__':
    print("Running window_manager.py in test mode...")

    # Create a pywebview window for testing purposes
    test_window = webview.create_window(
        'Aura Stealth Test',
        html='<h1>This window should be black in screen recordings.</h1>',
        width=800,
        height=600
    )

    # Hook our protection function to the 'shown' event. This is critical.
    # The 'shown' event fires after the window is created and visible, ensuring
    # that a window handle exists.
    test_window.events.shown += lambda: apply_capture_protection(test_window)

    # Start the GUI event loop
    webview.start()
# This function is not called if DEV_MODE in main.py is True
    print("--- Running window_manager.py in test mode ---")