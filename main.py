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
        self.command_file = os.path.join(tempfile.gettempdir(), "aura_command.json")
        self.last_command_time = 0
        self.running = False
        self.startup_time = time.time()
        self.startup_delay = 5
        self.last_processed_command = None
        self.command_cooldown = 0.5
        self._monitor_task = None

    async def start_monitoring(self):
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
        self.running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        print("🎮 Global command monitor stopped")

    async def _async_monitor_loop(self):
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
                # (1 = 20%, 2 = 40%, 3 = 60%, 4 = 70%/semi, 5 = 100%/opaque)
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
            elif command == "scroll":
                direction = command_data.get("direction", "down")
                amount = command_data.get("amount", 150)
                scroll_amount = -amount if direction == "up" else amount
                self._js(
                    f'document.getElementById("conversation-stream")'
                    f'.scrollBy({{top:{scroll_amount},left:0,behavior:"smooth"}})'
                )
            else:
                print(f"⚠️ Unknown global command: {command}")
                return False
            return True
        except Exception as exc:
            print(f"❌ Error executing global command: {exc}")
            return False

    def _js(self, code: str) -> None:
        """Execute JavaScript in the pywebview window."""
        if webview.windows:
            win = webview.windows[0]
            time.sleep(0.05)
            try:
                win.evaluate_js(code)
            except Exception:
                # Wrap in setTimeout as fallback
                win.evaluate_js(
                    f"setTimeout(()=>{{try{{{code}}}catch(e){{console.warn(e)}}}},100)"
                )


command_monitor = GlobalCommandMonitor()

# --- FastAPI App ---
app = FastAPI()
app.include_router(websocket.router)
app.include_router(config_api.router)
app.mount("/static", StaticFiles(directory="web"), name="static")


@app.get("/")
async def read_index(request: Request):
    return FileResponse(os.path.join("web", "index.html"))


# --- Uvicorn server wrapper ---
class UvicornServer:
    def __init__(self, fastapi_app, host="127.0.0.1", port=None):
        self.app = fastapi_app
        self.host = host
        self.port = port if port else find_free_port()
        self.server = None
        self.server_task = None

    async def start(self):
        config = uvicorn.Config(
            app=self.app, host=self.host, port=self.port,
            log_level="warning", loop="asyncio"
        )
        self.server = uvicorn.Server(config)
        self.server_task = asyncio.create_task(self.server.serve())
        print(f"🚀 Uvicorn started on {self.host}:{self.port}")

    async def stop(self):
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
    def __init__(self):
        self.thread = None
        self.loop = None
        self.shutdown_event = threading.Event()

    def start(self):
        self.shutdown_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print("🚀 Asyncio services thread started")

    def stop(self):
        print("🛑 Requesting asyncio services shutdown…")
        self.shutdown_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)
            if self.thread.is_alive():
                print("⚠️ Asyncio thread did not stop gracefully")
            else:
                print("✅ Asyncio services thread stopped")

    def _run(self):
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

        # Start global hotkey listener
        window_manager.window_manager.start_hotkey_listener()

    def on_window_closing():
        print("🛑 Window closing — shutting down services…")
        asyncio_service_thread.stop()
        return True

    win.events.shown += on_window_shown
    win.events.closing += on_window_closing
    return win


# --- Entry point ---
def main():
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
