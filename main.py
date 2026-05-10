import ssl
import certifi

# ── macOS SSL fix ────────────────────────────────────────────────────────────
# macOS Python doesn't include CA certificates, so every HTTPS/WSS call fails
# with CERTIFICATE_VERIFY_FAILED. Monkey-patch ssl.create_default_context so
# ALL libraries (requests, aiohttp, websockets, Deepgram SDK, etc.) use
# certifi's bundle automatically — even if they don't read env vars.
_certifi_ctx = ssl.create_default_context(cafile=certifi.where())

_orig_create_default_context = ssl.create_default_context
def _patched_create_default_context(*args, **kwargs):
    if 'cafile' not in kwargs and not args:
        return ssl.create_default_context(cafile=certifi.where())
    return _orig_create_default_context(*args, **kwargs)
ssl.create_default_context = _patched_create_default_context
# ─────────────────────────────────────────────────────────────────────────────

import webview
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import aiofiles
import window_manager  # macOS-native AppKit window manager
import os
import orjson
import tempfile
import time
import sys
import socket
import threading
import shutil
from pathlib import Path


# --- Auto-create .env from .env.example if missing ---
_env_path = Path(".env")
_env_example_path = Path(".env.example")

if not _env_path.exists() and _env_example_path.exists():
    shutil.copy2(_env_example_path, _env_path)
    print("📄 Created .env from .env.example — please fill in your API keys!")
elif not _env_path.exists() and not _env_example_path.exists():
    print("⚠️ No .env or .env.example found. The app may fail to start without a .env file.")

from api import websocket, config_api
from api.session_manager import session_manager
from core.config import settings, print_config_debug


def find_free_port(preferred: int = 8002) -> int:
    """Check if the preferred port is available; if not, find a free one."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    print(f"⚠️ Port {preferred} is busy, using port {port} instead")
    return port


# DEV_MODE is controlled via .env — see core/config.py
DEV_MODE = settings.DEV_MODE
print_config_debug()


# --- Global Command Monitor ---
class GlobalCommandMonitor:
    """Monitors the temp command file for global hotkey commands."""

    def __init__(self):
        """Initialise the monitor with a temp-file path and timing defaults."""
        self.command_file = os.path.join(tempfile.gettempdir(), "aura_command.json")
        self.last_command_time = 0
        self.running = False
        self.startup_time = time.time()
        self.startup_delay = 5
        self.last_processed_command = None
        self.command_cooldown = 0.5
        self._monitor_task = None

    async def start_monitoring(self):
        """Delete any stale command file and launch the async polling loop."""
        try:
            if os.path.exists(self.command_file):
                os.remove(self.command_file)
                print("🧹 Cleared old global command file")
        except Exception as exc:
            print(f"⚠️ Could not clear old command file: {exc}")
        self.running = True
        self._monitor_task = asyncio.create_task(self._async_monitor_loop())
        print("🎮 Global command monitor started")

    async def stop_monitoring(self):
        """Signal the polling loop to stop and await its cancellation."""
        self.running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        print("🎮 Global command monitor stopped")

    async def _async_monitor_loop(self):
        """Poll the command file every 200 ms and dispatch recognised commands."""
        while self.running:
            try:
                if os.path.exists(self.command_file):
                    file_mtime = os.path.getmtime(self.command_file)
                    if file_mtime > self.last_command_time:
                        self.last_command_time = file_mtime
                        try:
                            async with aiofiles.open(self.command_file, "rb") as f:
                                command_data = orjson.loads(await f.read())
                            if self._process_command(command_data):
                                try:
                                    os.remove(self.command_file)
                                except Exception:
                                    pass
                        except (orjson.JSONDecodeError, IOError):
                            pass
                await asyncio.sleep(0.2)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                print(f"❌ Error in command monitor: {exc}")
                await asyncio.sleep(1)

    def _process_command(self, command_data: dict) -> bool:
        """Validate and dispatch a single command dict; return True on success."""
        command = command_data.get("command", "")
        source = command_data.get("source", "")

        if source != "global_hotkey":
            return False

        if time.time() - self.startup_time < self.startup_delay:
            print(f"🎮 Ignoring global command during startup: {command}")
            return False

        command_id = (
            f"{command}_{command_data.get('level','')}_{command_data.get('preset_key','')}_{command_data.get('direction','')}"
        )
        current_time = time.time()
        if (
            self.last_processed_command
            and self.last_processed_command["id"] == command_id
            and current_time - self.last_processed_command["time"] < self.command_cooldown
        ):
            print(f"🎮 Ignoring duplicate command within cooldown: {command}")
            return False

        self.last_processed_command = {"id": command_id, "time": current_time, "command": command}
        print(f"🎮 Processing global command: {command}")

        try:
            if command == "toggle_vision_mode":
                self._js('if(window.toggleVisionMode)window.toggleVisionMode()')
            elif command == "capture_screenshot":
                self._js('if(window.captureScreenshot)window.captureScreenshot()')
            elif command == "process_screenshots":
                self._js('if(window.processScreenshots)window.processScreenshots()')
            elif command == "reset_screenshot_queue":
                self._js('if(window.resetScreenshotQueue)window.resetScreenshotQueue()')
            elif command == "switch_preset":
                pk = command_data.get("preset_key", "primary")
                self._js(f'if(window.switchPreset)window.switchPreset("{pk}")')
            elif command == "set_transparency":
                # Map string names to the numeric levels exposed by window.setTransparencyLevel()
                # transparencyLevels = [0.2, 0.4, 0.6, 0.8, 1.0] (index 0-based, level 1-based)
                # 1=20%, 2=40%, 3=60%, 4=80%/semi, 5=100%/opaque
                level_map = {"transparent": 1, "semi": 4, "opaque": 5}
                level = level_map.get(command_data.get("level", "opaque"))
                if level is None:
                    print(f"⚠️ Unknown transparency level: {command_data.get('level')}")
                    return False
                self._js(f"if(window.setTransparencyLevel)window.setTransparencyLevel({level})")
            elif command == "toggle_mic_mute":
                self._js('if(window.toggleMicMute)window.toggleMicMute()')
            elif command == "toggle_universal_mute":
                self._js('if(window.toggleUniversalMute)window.toggleUniversalMute()')
            elif command == "switch_vision_model":
                self._js('if(window.switchVisionModel)window.switchVisionModel()')
            elif command == "reset_interview":
                self._js('if(window.resetInterview)window.resetInterview()')
            else:
                print(f"⚠️ Unknown global command: {command}")
                return False
            return True
        except Exception as exc:
            print(f"❌ Error executing global command: {exc}")
            return False

    def _js(self, code: str) -> None:
        """Execute JavaScript in the pywebview window.

        Runs evaluate_js off the asyncio event loop via run_in_executor so the
        50 ms+ synchronous IPC call does not block the shared asyncio thread
        (which also serves Uvicorn and the session-cleanup task).
        Logs the original exception before attempting the setTimeout fallback.
        """
        if not webview.windows:
            return
        win = webview.windows[0]
        loop = asyncio.get_event_loop()

        def _run() -> None:
            try:
                win.evaluate_js(code)
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️ evaluate_js failed ({exc!r}); retrying via setTimeout")
                try:
                    win.evaluate_js(
                        f"setTimeout(()=>{{try{{{code}}}catch(e){{console.warn(e)}}}},100)"
                    )
                except Exception as exc2:
                    print(f"❌ evaluate_js fallback also failed: {exc2!r}")

        loop.run_in_executor(None, _run)


command_monitor = GlobalCommandMonitor()

# --- FastAPI App ---
app = FastAPI()
app.include_router(websocket.router)
app.include_router(config_api.router)
app.mount("/static", StaticFiles(directory="web"), name="static")


@app.get("/")
async def read_index(request: Request):
    """Serve the main SPA entry point (web/index.html)."""
    return FileResponse(os.path.join("web", "index.html"))


# --- Uvicorn server wrapper ---
class UvicornServer:
    """Thin async wrapper around a Uvicorn ASGI server instance."""

    def __init__(self, fastapi_app, host="127.0.0.1", port=None):
        """Bind the server to *host* and an available *port* (auto-detected if None)."""
        self.app = fastapi_app
        self.host = host
        self.port = port if port else find_free_port()
        self.server = None
        self.server_task = None

    async def start(self):
        """Configure and start the Uvicorn server as an asyncio task."""
        config = uvicorn.Config(
            app=self.app, host=self.host, port=self.port,
            log_level="warning", loop="asyncio"
        )
        self.server = uvicorn.Server(config)
        self.server_task = asyncio.create_task(self.server.serve())
        print(f"🚀 Uvicorn started on {self.host}:{self.port}")

    async def stop(self):
        """Gracefully signal Uvicorn to exit and await task completion."""
        if self.server:
            self.server.should_exit = True
            if self.server_task and not self.server_task.done():
                try:
                    await asyncio.wait_for(self.server_task, timeout=5.0)
                except asyncio.TimeoutError:
                    self.server_task.cancel()
                    try:
                        await self.server_task
                    except asyncio.CancelledError:
                        pass
        print("🛑 Uvicorn stopped")


uvicorn_server = UvicornServer(app)


# --- Background asyncio thread ---
class AsyncioServiceThread:
    """Runs an asyncio event loop in a background daemon thread."""

    def __init__(self):
        """Initialise thread handle, loop reference, and shutdown event."""
        self.thread = None
        self.loop = None
        self.shutdown_event = threading.Event()

    def start(self):
        """Spawn the daemon thread and start the asyncio services inside it."""
        self.shutdown_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print("🚀 Asyncio services thread started")

    def stop(self):
        """Signal the asyncio loop to shut down and join the thread (up to 10 s)."""
        print("🛑 Requesting asyncio services shutdown…")
        self.shutdown_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)
            if self.thread.is_alive():
                print("⚠️ Asyncio thread did not stop gracefully")
            else:
                print("✅ Asyncio services thread stopped")

    def _run(self):
        """Thread target: create a fresh event loop and run all async services."""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._run_services())
        except Exception as exc:
            print(f"❌ Error in asyncio thread: {exc}")
        finally:
            if self.loop:
                try:
                    pending = asyncio.all_tasks(self.loop)
                    if pending:
                        for task in pending:
                            task.cancel()
                        self.loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                    self.loop.close()
                    print("✅ Asyncio event loop closed")
                except Exception as exc:
                    print(f"⚠️ Error during loop cleanup: {exc}")

    async def _run_services(self):
        """Start Uvicorn, the session cleaner, and the command monitor; block until shutdown."""
        try:
            print("🚀 Starting async services…")
            await uvicorn_server.start()
            session_manager.start_cleanup_task()
            await command_monitor.start_monitoring()

            while not self.shutdown_event.is_set():
                await asyncio.sleep(0.1)

            print("🛑 Shutdown signal received, cleaning up…")
        except Exception as exc:
            print(f"❌ Error in async services: {exc}")
        finally:
            await command_monitor.stop_monitoring()
            await uvicorn_server.stop()
            print("✅ Async services cleanup complete")


asyncio_service_thread = AsyncioServiceThread()


# --- pywebview window setup ---
def setup_webview_window():
    """Create and configure the pywebview window (Cocoa backend on macOS)."""
    win = webview.create_window(
        "Aura",
        f"http://127.0.0.1:{uvicorn_server.port}",
        width=1000,
        height=750,
        resizable=True,
    )

    def on_window_shown():
        """Apply macOS window properties once the Cocoa window is visible."""
        print(f"🔧 Window shown. DEV_MODE={DEV_MODE}")

        if not DEV_MODE:
            print("🛡️ Applying screen capture protection…")
            ok = window_manager.apply_capture_protection(win)
            if ok:
                print("✅ Screen capture protection applied!")
            else:
                print("❌ Screen capture protection FAILED — window may be visible in recordings!")
        else:
            print("ℹ️ DEV_MODE=True — skipping screen capture protection")

        # Give Cocoa a moment to fully render the window
        time.sleep(1.0)

        if window_manager.find_aura_window():
            print("🔍 NSWindow located — configuring window behaviour")
            time.sleep(0.3)

            # Always-on-top (NSFloatingWindowLevel)
            for attempt in range(3):
                if window_manager.set_app_always_on_top(True):
                    print("📌 Window set to always-on-top")
                    break
                print(f"⚠️ Always-on-top attempt {attempt + 1} failed, retrying…")
                time.sleep(0.3)

            print("ℹ️ Transparency will be applied when live interview starts")
        else:
            print("⚠️ Could not locate Aura NSWindow at startup")

        # ── WKUIDelegate: auto-grant getUserMedia() microphone requests ──────
        # WKWebView will call this delegate method when JS calls getUserMedia().
        # Without it, WKWebView silently denies mic access even if the process
        # has macOS microphone permission. WKPermissionDecisionGrant = 1.
        try:
            from WebKit import WKWebView
            from Foundation import NSObject
            from AppKit import NSApp
            import objc

            class _AuraMicDelegate(NSObject):
                """Minimal WKUIDelegate that grants all media capture requests."""

                def webView_requestMediaCapturePermissionForOrigin_initiatedByFrame_type_decisionHandler_(
                    self, webview, origin, frame, media_type, handler
                ):
                    """Grant microphone (and camera) access automatically."""
                    print("🎙️ WKUIDelegate: granting media capture permission")
                    handler(1)  # 1 = WKPermissionDecisionGrant

                webView_requestMediaCapturePermissionForOrigin_initiatedByFrame_type_decisionHandler_ = objc.selector(
                    webView_requestMediaCapturePermissionForOrigin_initiatedByFrame_type_decisionHandler_,
                    selector=b"webView:requestMediaCapturePermissionForOrigin:initiatedByFrame:type:decisionHandler:",
                    signature=b"v@:@@@q@?",
                )

            def _find_wkwebview(view):
                """Recursively search view hierarchy for WKWebView."""
                if isinstance(view, WKWebView):
                    return view
                for sub in (view.subviews() or []):
                    found = _find_wkwebview(sub)
                    if found:
                        return found
                return None

            mic_delegate = _AuraMicDelegate.alloc().init()
            for ns_window in NSApp.windows():
                content = ns_window.contentView()
                if content is None:
                    continue
                wkview = _find_wkwebview(content)
                if wkview:
                    # Remove gesture restriction for playback too
                    wkview.configuration().setMediaTypesRequiringUserActionForPlayback_(0)
                    wkview.setUIDelegate_(mic_delegate)
                    # Pin to prevent garbage collection
                    win._mic_delegate = mic_delegate
                    print("🎙️ WKUIDelegate set — microphone will be auto-granted")
                    break
        except Exception as mic_exc:
            print(f"ℹ️ WKUIDelegate setup failed: {mic_exc}")

        # Start global hotkey listener
        window_manager.window_manager.start_hotkey_listener()

    def on_window_closing():
        """Tear down asyncio services before the window is destroyed."""
        print("🛑 Window closing — shutting down services…")
        asyncio_service_thread.stop()
        return True

    win.events.shown += on_window_shown
    win.events.closing += on_window_closing
    return win


# --- Entry point ---
def main():
    """Application entry point: start async services, open pywebview window, run Cocoa loop."""
    print("🚀 Starting Aura (macOS — AppKit/Cocoa)")
    print("   📋 Architecture: pywebview/Cocoa on main thread, asyncio in background thread")

    try:
        asyncio_service_thread.start()
        time.sleep(2)   # Let Uvicorn bind before opening the window

        setup_webview_window()

        print("🖥️  Starting pywebview Cocoa event loop on main thread…")
        webview.start(debug=DEV_MODE)

    except KeyboardInterrupt:
        print("🛑 Interrupted by user")
    except Exception as exc:
        print(f"❌ Application error: {exc}")
    finally:
        print("🧹 Final cleanup…")
        asyncio_service_thread.stop()
        print("✅ Shutdown complete")


if __name__ == "__main__":
    main()
