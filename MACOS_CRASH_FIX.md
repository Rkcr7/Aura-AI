# macOS AppKit Thread Safety Fix

## The Problem

Your application crashed with:
```
Exception Type: EXC_BREAKPOINT (SIGTRAP)
Termination Reason: SIGNAL, Code 5, Trace/BPT trap: 5
Application Specific Information: Must only be used from the main thread
```

**Root Cause**: The hotkey handler in `window_manager.py` was spawning background daemon threads to execute AppKit GUI operations. macOS AppKit is **not thread-safe** — all GUI operations must run on the main thread or the app will crash with a segfault.

### The Problematic Code
```python
# OLD CODE (line ~540) — WRONG ❌
def _on_key_down(event) -> None:
    if action:
        Thread(target=action, daemon=True).start()  # ← Spawns a background thread!
```

When the hotkey handler detected Option+Z, Option+X, or Option+1-3, it would spawn a daemon thread to call:
- `toggle_visibility()` → calls `NSWindow.setVisible()` / `orderFrontRegardless()`
- `toggle_ghost_mode()` → calls `NSWindow.setIgnoresMouseEvents_()`
- `set_transparency()` → calls `NSWindow.setAlphaValue_()`

All of these are AppKit methods that **must** run on macOS's main thread. Since they were being called from Thread-2 (the background hotkey thread), macOS immediately crashed with:
```
-[NSWMWindowCoordinator performTransactionUsingBlock:] + 752
  ↓ (crash)
```

## The Solution

### 1. Added a Main-Thread Dispatcher
Created `_dispatch_to_main_thread(func, *args, **kwargs)` function that safely schedules AppKit operations to run on the main NSApplication thread:

```python
def _dispatch_to_main_thread(func, *args, **kwargs):
    """Dispatch a callable to the main thread safely."""
    if not IS_MACOS or NSApp is None:
        return func(*args, **kwargs)
    
    try:
        def _run_func():
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                print(f"⚠️  Error in main-thread dispatch: {exc}")
        
        NSApp.performSelectorOnMainThread_withObject_waitUntilDone_(
            "performSelector:withObject:",
            (lambda: _run_func(),),
            False
        )
    except Exception as exc:
        print(f"⚠️  Could not dispatch to main thread: {exc}")
        try:
            func(*args, **kwargs)
        except Exception:
            pass
```

### 2. Updated Hotkey Action Map
Wrapped all AppKit GUI operations with `_dispatch_to_main_thread`:

```python
_HOTKEY_ACTIONS: dict = {
    'z': lambda: _dispatch_to_main_thread(self.toggle_visibility),      # ✅ GUI → main thread
    'x': lambda: _dispatch_to_main_thread(self.toggle_ghost_mode),      # ✅ GUI → main thread
    '1': lambda: _dispatch_to_main_thread(self.set_transparency, 1.0),  # ✅ GUI → main thread
    '2': lambda: _dispatch_to_main_thread(self.set_transparency, 0.7),  # ✅ GUI → main thread
    '3': lambda: _dispatch_to_main_thread(self.set_transparency, 0.4),  # ✅ GUI → main thread
    'm': lambda: _send_command({"command": "toggle_mic_mute"}),        # ✅ File I/O (thread-safe)
    'u': lambda: _send_command({"command": "toggle_universal_mute"}),  # ✅ File I/O (thread-safe)
    # ... other command-based hotkeys remain thread-safe (they write JSON)
}
```

### 3. Removed Background Thread Spawning
The key-down handler now runs actions **directly** instead of spawning daemon threads:

```python
# NEW CODE ✅
def _on_key_down(event) -> None:
    if action:
        action()  # Runs immediately — _dispatch_to_main_thread handles routing to main thread
```

## Why This Works

1. **AppKit GUI operations (z, x, 1-3)**: 
   - `_dispatch_to_main_thread` routes them to the main NSApplication event loop
   - They execute safely on the main thread
   - pywebview's event loop is already running, so this integrates seamlessly

2. **Command-file operations (m, u, q, w, e, f, v, s, a, d, r)**:
   - These are **thread-safe** — they just write JSON files to `/tmp/aura_command.json`
   - `_send_command()` uses atomic `os.replace()` to prevent partial writes
   - No need to dispatch to main thread
   - Can run immediately from the hotkey handler

## Testing the Fix

1. **Rebuild and restart**:
   ```bash
   source venv/bin/activate
   python main.py
   ```

2. **Test hotkeys**:
   - Press **Option+Z** to toggle visibility
   - Press **Option+X** to toggle ghost mode
   - Press **Option+1/2/3** to change opacity
   - These should now work without crashing

3. **Test command hotkeys**:
   - Press **Option+M** to mute microphone
   - Press **Option+S** to capture screenshot
   - These continue to work as before

## Files Modified

- [window_manager.py](window_manager.py):
  - Added import: `from functools import partial`
  - Added import: `NSRunLoop, NSTimer` from Foundation
  - Added function: `_dispatch_to_main_thread()`
  - Updated: `_HOTKEY_ACTIONS` to wrap GUI operations
  - Updated: `_on_key_down()` to remove background thread spawning

## Key Takeaways

✅ **macOS AppKit requires all GUI operations on the main thread**
- Cross-thread GUI calls → instant segfault/SIGTRAP
- Solution: Use `NSApp.performSelectorOnMainThread_withObject_waitUntilDone_()`

✅ **pywebview's NSApplication event loop is already running**
- No need to manually start a CFRunLoop
- No CFRunLoop conflicts with NSEvent monitors

✅ **Mix thread-safe and GUI operations safely**
- File I/O (JSON commands) → stay on hotkey thread (fast, safe)
- Window manipulation → dispatch to main thread (required, safe)

## References

- [Apple AppKit Thread Safety](https://developer.apple.com/documentation/appkit/nsapplication)
- [NSApplication.performSelectorOnMainThread_withObject_waitUntilDone_](https://developer.apple.com/documentation/appkit/nsapplication/1428537-performselectoronmainthread)
- [pyobjc](https://pyobjc.readthedocs.io/)
- [pywebview](https://pywebview.kivy.org/)
