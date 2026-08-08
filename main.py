import os
import shutil
import signal
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

# --- Auto-create .env from .env.example if missing ---
# This must run BEFORE any first-party import: window_manager and core.config
# both read .env at import time, so creating it afterwards meant a freshly
# generated .env had no effect until the next launch.
_env_path = Path(".env")
_env_example_path = Path(".env.example")

if not _env_path.exists() and _env_example_path.exists():
    shutil.copy2(_env_example_path, _env_path)
    print("📄 Created .env from .env.example — please fill in your API keys!")
elif not _env_path.exists() and not _env_example_path.exists():
    print("⚠️ No .env or .env.example found. The app may fail to start without a .env file.")

import asyncio

import aiofiles
import orjson
import uvicorn
import webview
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import window_manager  # Our new module for capture protection
from api import websocket, config_api
from api.session_manager import session_manager
from core.config import settings, print_config_debug


def find_free_port(preferred: int = 8002) -> int:
    """Check if the preferred port is available; if not, find a free one."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', preferred))
            return preferred
        except OSError:
            pass
    # Preferred port is occupied — let the OS pick a free one
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    print(f"⚠️ Port {preferred} is busy, using port {port} instead")
    return port

# --- Development Flag (now from .env) ---
# DEV_MODE is now controlled via .env file - see core/config.py
DEV_MODE = settings.DEV_MODE

# Print configuration debug info at startup
print_config_debug()

# --- Global Command Monitor ---
class GlobalCommandMonitor:
    """Monitors the temp command file for global hotkey commands"""
    
    def __init__(self):
        self.command_file = os.path.join(tempfile.gettempdir(), "aura_command.json")
        self.last_command_time = 0
        self.running = False
        self.websocket_manager = None
        self.startup_time = time.time()
        self.startup_delay = 5  # Ignore commands for first 5 seconds after startup
        self.last_processed_command = None
        self.command_cooldown = 0.5  # 500ms cooldown between same commands
        self._monitor_task = None
        
    def set_websocket_manager(self, ws_manager):
        """Set the websocket manager for sending commands"""
        self.websocket_manager = ws_manager
        
    async def start_monitoring(self):
        """Start the command monitoring task"""
        # Clean up any old command files
        try:
            if os.path.exists(self.command_file):
                os.remove(self.command_file)
                print("🧹 Cleared old global command file")
        except Exception as e:
            print(f"⚠️ Could not clear old command file: {e}")
        
        self.running = True
        self._monitor_task = asyncio.create_task(self._async_monitor_loop())
        print("🎮 Global command monitor started")
        
    async def stop_monitoring(self):
        """Stop the command monitoring"""
        self.running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        print("🎮 Global command monitor stopped")
    
    async def _async_monitor_loop(self):
        """Async monitoring loop that checks for commands with improved performance"""
        while self.running:
            try:
                if os.path.exists(self.command_file):
                    # Check file modification time
                    file_mtime = os.path.getmtime(self.command_file)
                    
                    if file_mtime > self.last_command_time:
                        self.last_command_time = file_mtime
                        
                        # Read and process the command using async file I/O
                        try:
                            async with aiofiles.open(self.command_file, 'rb') as f:
                                file_content = await f.read()
                                command_data = orjson.loads(file_content)
                            
                            # Process the command
                            if self._process_command(command_data):
                                # Clean up the command file after successful processing
                                try:
                                    os.remove(self.command_file)
                                    print(f"🧹 Cleaned up command file after processing")
                                except Exception as cleanup_error:
                                    # Don't fail if cleanup fails
                                    pass
                            
                        except (orjson.JSONDecodeError, IOError) as e:
                            # Ignore file read errors (file might be being written)
                            pass
                            
                await asyncio.sleep(0.2)  # Check every 200ms (reduced frequency)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Error in command monitor: {e}")
                await asyncio.sleep(1)  # Wait longer on error
                
    def _process_command(self, command_data):
        """Process a command from the global hotkey"""
        command = command_data.get('command', '')
        source = command_data.get('source', '')
        timestamp_str = command_data.get('timestamp', '')
        
        if source != 'global_hotkey':
            return False  # Only process global hotkey commands
        
        # Ignore commands during startup to prevent processing old/accidental commands
        if time.time() - self.startup_time < self.startup_delay:
            print(f"🎮 Ignoring global command during startup: {command}")
            return False
        
        # Create a unique command identifier for deduplication
        command_id = f"{command}_{command_data.get('level', '')}_{command_data.get('preset_key', '')}_{command_data.get('direction', '')}"
        current_time = time.time()
        
        # Check for duplicate commands within cooldown period
        if (self.last_processed_command and 
            self.last_processed_command['id'] == command_id and 
            current_time - self.last_processed_command['time'] < self.command_cooldown):
            print(f"🎮 Ignoring duplicate command within cooldown: {command}")
            return False
        
        # Update last processed command
        self.last_processed_command = {
            'id': command_id,
            'time': current_time,
            'command': command
        }
            
        print(f"🎮 Processing global command: {command}")
        
        # Execute the command by sending it to the browser
        try:
            if command == 'toggle_vision_mode':
                self._execute_browser_command('if (window.toggleVisionMode) { window.toggleVisionMode(); } else { console.warn("toggleVisionMode not available"); }')
            elif command == 'capture_screenshot':
                self._execute_browser_command('if (window.captureScreenshot) { window.captureScreenshot(); } else { console.warn("captureScreenshot not available"); }')
            elif command == 'process_screenshots':
                self._execute_browser_command('if (window.processScreenshots) { window.processScreenshots(); } else { console.warn("processScreenshots not available"); }')
            elif command == 'reset_screenshot_queue':
                self._execute_browser_command('if (window.resetScreenshotQueue) { window.resetScreenshotQueue(); } else { console.warn("resetScreenshotQueue not available"); }')
            elif command == 'switch_preset':
                preset_key = command_data.get('preset_key', 'primary')
                self._execute_browser_command(f'if (window.switchPreset) {{ window.switchPreset("{preset_key}"); }} else {{ console.warn("switchPreset not available"); }}')
            elif command == 'set_transparency':
                transparency_level = command_data.get('level', 'opaque')
                self._execute_browser_command(f'if (window.setTransparency) {{ window.setTransparency("{transparency_level}"); }} else {{ console.warn("setTransparency not available"); }}')
            elif command == 'toggle_mic_mute':
                self._execute_browser_command('if (window.toggleMicMute) { window.toggleMicMute(); } else { console.warn("toggleMicMute not available"); }')
            elif command == 'toggle_universal_mute':
                self._execute_browser_command('if (window.toggleUniversalMute) { window.toggleUniversalMute(); } else { console.warn("toggleUniversalMute not available"); }')
            elif command == 'switch_vision_model':
                self._execute_browser_command('if (window.switchVisionModel) { window.switchVisionModel(); } else { console.warn("switchVisionModel not available"); }')
            elif command == 'reset_interview':
                self._execute_browser_command('if (window.resetInterview) { window.resetInterview(); } else { console.warn("resetInterview not available"); }')
            elif command == 'scroll':
                direction = command_data.get('direction', 'down')
                amount = command_data.get('amount', 150)
                # Use smooth scrolling with the specified amount
                if direction == 'up':
                    scroll_amount = -amount
                else:
                    scroll_amount = amount
                js_code = f'document.getElementById("conversation-stream").scrollBy({{ top: {scroll_amount}, left: 0, behavior: "smooth" }})'
                self._execute_browser_command(js_code)
            elif command == 'context_aware_action':
                action = command_data.get('action', '')
                if action == 'auto_select_preset':
                    # Auto-select AI preset
                    self._execute_browser_command('if (window.switchPreset) { window.switchPreset("auto"); } else { console.warn("switchPreset not available"); }')
                else:
                    print(f"⚠️ Unknown context-aware action: {action}")
                    return False
            else:
                print(f"⚠️ Unknown global command: {command}")
                return False
                
            return True  # Command processed successfully
            
        except Exception as e:
            print(f"❌ Error executing global command: {e}")
            return False
            
    def _execute_browser_command(self, js_code):
        """Execute JavaScript code in the browser"""
        try:
            # Use webview's evaluate_js to run the command
            if hasattr(webview, 'windows') and webview.windows:
                window = webview.windows[0]  # Get the first (main) window
                
                # Add a small delay to ensure the page is loaded
                time.sleep(0.1)
                
                # Try to execute with error handling
                try:
                    result = window.evaluate_js(js_code)
                    print(f"✅ Executed global command in browser: {js_code.split('&&')[0]}...")
                except Exception as js_error:
                    # If direct execution fails, try wrapping in setTimeout
                    wrapped_code = f"setTimeout(() => {{ try {{ {js_code} }} catch(e) {{ console.warn('Global command error:', e); }} }}, 100);"
                    window.evaluate_js(wrapped_code)
                    print(f"✅ Executed global command in browser (delayed): {js_code.split('&&')[0]}...")
            else:
                print("⚠️ No webview window available for command execution")
        except Exception as e:
            print(f"❌ Failed to execute browser command: {e}")

# Create global command monitor instance
command_monitor = GlobalCommandMonitor()

# --- FastAPI App Setup ---
app = FastAPI()
app.include_router(websocket.router)
app.include_router(config_api.router)

# Mount the 'web' directory to serve static files (CSS, JS)
# This makes files in 'web/css' and 'web/js' available under '/static/css' and '/static/js'
app.mount("/static", StaticFiles(directory="web"), name="static")

@app.get("/")
async def read_index(request: Request):
    """Serves the main index.html file."""
    return FileResponse(os.path.join('web', 'index.html'))

# --- Async Server Management ---
class UvicornServer:
    """Manages the Uvicorn server as an asyncio task"""
    
    def __init__(self, app, host="127.0.0.1", port=None):
        self.app = app
        self.host = host
        self.port = port if port else find_free_port()
        self.server = None
        self.server_task = None
        
    async def start(self):
        """Start the Uvicorn server as an asyncio task"""
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
            loop="asyncio"
        )
        self.server = uvicorn.Server(config)
        self.server_task = asyncio.create_task(self.server.serve())
        print(f"🚀 Uvicorn server started on {self.host}:{self.port}")
        
    async def stop(self):
        """Stop the Uvicorn server gracefully"""
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
        print("🛑 Uvicorn server stopped")

# Global server instance
uvicorn_server = UvicornServer(app)

# --- Background Thread for Asyncio Services ---
class AsyncioServiceThread:
    """Manages all asyncio services in a dedicated background thread"""
    
    def __init__(self):
        self.thread = None
        self.loop = None
        self.shutdown_event = None
        self.services_task = None
        
    def start(self):
        """Start the asyncio services in a background thread"""
        self.shutdown_event = threading.Event()
        self.thread = threading.Thread(target=self._run_asyncio_thread, daemon=True)
        self.thread.start()
        print("🚀 Asyncio services thread started")
        
    def stop(self):
        """Stop the asyncio services gracefully"""
        if self.shutdown_event:
            print("🛑 Requesting asyncio services shutdown...")
            self.shutdown_event.set()
            
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)  # Wait up to 10 seconds
            if self.thread.is_alive():
                print("⚠️ Asyncio thread did not stop gracefully")
            else:
                print("✅ Asyncio services thread stopped")
    
    def _run_asyncio_thread(self):
        """Run the asyncio event loop in this thread"""
        try:
            # Create a new event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            print("🔄 Starting asyncio event loop in background thread")
            
            # Run the async services
            self.loop.run_until_complete(self._run_async_services())
            
        except Exception as e:
            print(f"❌ Error in asyncio thread: {e}")
        finally:
            if self.loop:
                try:
                    # Clean up any remaining tasks
                    pending = asyncio.all_tasks(self.loop)
                    if pending:
                        print(f"🧹 Cancelling {len(pending)} pending tasks...")
                        for task in pending:
                            task.cancel()
                        
                        # Wait for tasks to be cancelled
                        self.loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                    
                    self.loop.close()
                    print("✅ Asyncio event loop closed")
                except Exception as e:
                    print(f"⚠️ Error during loop cleanup: {e}")
    
    async def _run_async_services(self):
        """Run all async services concurrently"""
        try:
            print("🚀 Starting async services...")
            
            # Start the Uvicorn server
            await uvicorn_server.start()
            
            # Start the session cleanup task
            session_manager.start_cleanup_task()
            
            # Start the global command monitor
            await command_monitor.start_monitoring()
            
            # Wait for shutdown signal
            while not self.shutdown_event.is_set():
                await asyncio.sleep(0.1)
            
            print("🛑 Shutdown signal received, cleaning up...")
            
        except Exception as e:
            print(f"❌ Error in async services: {e}")
        finally:
            # Cleanup
            await self._cleanup_async_services()
    
    async def _cleanup_async_services(self):
        """Clean up all async services"""
        print("🧹 Cleaning up async services...")
        
        # Stop the command monitor
        await command_monitor.stop_monitoring()
        
        # Stop the server
        await uvicorn_server.stop()
        
        print("✅ Async services cleanup complete")

# Global asyncio service thread instance
asyncio_service_thread = AsyncioServiceThread()

# --- Webview Setup (Main Thread) ---
def setup_webview_window():
    """Setup and configure the webview window"""
    # Create the pywebview window, loading the FastAPI server
    window = webview.create_window(
        'Aura',
        f'http://127.0.0.1:{uvicorn_server.port}',
        width=1000,
        height=750,
        resizable=True
    )

    # Window shown event handler
    def on_window_shown():
        print(f"🔧 Window shown event fired. DEV_MODE = {DEV_MODE}")
        
        if not DEV_MODE:
            print("🛡️ DEV_MODE is False - Applying screen capture protection...")
            protection_success = window_manager.apply_capture_protection(window)
            if protection_success:
                print("✅ Screen capture protection successfully applied!")
            else:
                print("❌ CRITICAL: Screen capture protection FAILED!")
                print("   🚨 WARNING: Window will be visible in screen recordings!")
        else:
            print("ℹ️ DEV_MODE is True. Skipping screen capture protection.")
            print("   📋 Note: Window WILL be visible in screen recordings during development")
        
        # Set up window transparency and always-on-top
        import time
        time.sleep(1.0)  # Give window more time to fully initialize
        
        # Find window and configure always-on-top (but NOT transparency yet)
        if window_manager.find_aura_window():
            print("🔍 Window found - setting up always-on-top only")
            
            # Wait a bit more before setting always-on-top
            time.sleep(0.5)
            
            # Set window to always stay on top with retries
            always_on_top_success = False
            for attempt in range(3):
                always_on_top_success = window_manager.set_app_always_on_top(True)
                if always_on_top_success:
                    print("📌 Window set to always stay on top")
                    break
                else:
                    print(f"⚠️ Always-on-top attempt {attempt + 1} failed, retrying...")
                    time.sleep(0.3)
            
            if not always_on_top_success:
                print("⚠️ Failed to set always on top after 3 attempts")
                
            print("ℹ️ Transparency will be applied only during live interview")
        else:
            print("⚠️ Could not find Aura window for window management")
        
        # Start the global hotkey listener
        window_manager.window_manager.start_hotkey_listener()
    
    # Window closing event handler
    def on_window_closing():
        print("🛑 Window closing, shutting down services...")
        asyncio_service_thread.stop()
        return True  # Allow window to close
    
    window.events.shown += on_window_shown
    window.events.closing += on_window_closing
    
    return window

# --- Main Application Entry Point ---
def main():
    """Main application entry point"""
    print("🚀 Starting Aura with corrected asyncio-native architecture...")
    print("   📋 Architecture: pywebview on main thread, asyncio services in background thread")
    
    try:
        # Start the asyncio services in background thread
        asyncio_service_thread.start()
        
        # Give the server a moment to start
        time.sleep(2)
        
        # Setup and run webview on main thread (required by pywebview)
        window = setup_webview_window()
        
        # Start the pywebview event loop (blocks until window closes)
        print("🖥️ Starting pywebview on main thread...")
        webview.start(debug=DEV_MODE)
        
    except KeyboardInterrupt:
        print("🛑 Application interrupted by user")
    except Exception as e:
        print(f"❌ Application error: {e}")
    finally:
        # Ensure cleanup
        print("🧹 Final cleanup...")
        asyncio_service_thread.stop()
        print("✅ Application shutdown complete")

if __name__ == '__main__':
    main()