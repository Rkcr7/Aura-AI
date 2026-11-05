"""Spot the Aura window staying blank and say why (issue #10).

On Windows, pywebview renders the UI in Microsoft Edge WebView2. When WebView2
fails to start, pywebview logs a single error line and leaves an empty white
window behind. The FastAPI server keeps running, so the app looks hung, and
that one line scrolls away under the hotkey list printed right after it.
With no WebView2 runtime at all, pywebview quietly falls back to the old
Internet Explorer engine, which can't run Aura's UI.

This watches the window and, when either happens, prints what went wrong and
how to fix it.
"""
from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Callable, List, Optional, Protocol, Sequence

if TYPE_CHECKING:
    from webview import Window

# Generous: WebView2's first start on a slow machine took ~4s in testing,
# and a window that loads is normally ready well under a second after showing.
LOAD_TIMEOUT_S = 20.0
WEBVIEW2_DOWNLOAD_URL = "https://developer.microsoft.com/microsoft-edge/webview2/"
PYWEBVIEW_LOGGER = "pywebview"
LEGACY_IE_RENDERER = "mshtml"


class Waitable(Protocol):
    def wait(self, timeout: Optional[float] = None) -> bool: ...


def _is_dotnet_stack_line(line: str) -> bool:
    # "at Namespace.Method()" frames and "--- End of ... stack trace ---" separators
    return line.startswith("at ") or line.startswith("--- ")


class PywebviewErrorCollector(logging.Handler):
    """Keeps the WebView2 errors pywebview logs, minus the .NET stack trace.

    pywebview also logs exceptions from any event handler (Aura's own included)
    on this logger, so anything not about WebView2 is left out.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)
        self.reasons: List[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if "webview2" not in message.lower():
            return
        lines = [line.strip() for line in message.splitlines()]
        summary = " ".join(line for line in lines if line and not _is_dotnet_stack_line(line))
        if summary:
            self.reasons.append(summary)


def _browser_fallback(url: str) -> List[str]:
    return [
        f"   Aura itself is running. Until then you can open {url} in a browser,",
        "   but a browser tab is NOT hidden from screen sharing.",
        "",
    ]


def explain_blank_window(url: str, reasons: Sequence[str], timeout_s: float) -> str:
    """The console message for a window that never loaded."""
    if reasons:
        details = ["   WebView2 (the Edge engine the Aura window runs on) failed to start:"]
        details += [f"     {reason}" for reason in reasons]
        details += ["   Fix: install or repair the Microsoft Edge WebView2 Runtime, then restart Aura:"]
    else:
        details = [
            "   WebView2 (the Edge engine the Aura window runs on) didn't report an error, it just",
            "   hasn't finished loading the page. A firewall, VPN, proxy or antivirus may be holding",
            "   it up. If it never loads, repair the Microsoft Edge WebView2 Runtime and restart Aura:",
        ]

    return "\n".join([
        "",
        f"⚠️ The Aura window still hasn't loaded after {timeout_s:.0f}s, so it's probably blank.",
        *details,
        f"     {WEBVIEW2_DOWNLOAD_URL}",
        *_browser_fallback(url),
    ])


def explain_legacy_renderer(url: str) -> str:
    """The console message for pywebview falling back to Internet Explorer."""
    return "\n".join([
        "",
        "⚠️ The Microsoft Edge WebView2 Runtime isn't installed, so the Aura window fell back",
        "   to the old Internet Explorer engine and won't work properly.",
        "   Fix: install the WebView2 Runtime, then restart Aura:",
        f"     {WEBVIEW2_DOWNLOAD_URL}",
        *_browser_fallback(url),
    ])


def watch_page_load(
    loaded: Waitable,
    url: str,
    reasons: Callable[[], Sequence[str]],
    *,
    timeout_s: float = LOAD_TIMEOUT_S,
    report: Callable[[str], None] = print,
    late_wait_s: Optional[float] = None,
) -> bool:
    """Wait for the page to load; explain the blank window if it doesn't.

    Returns True when the page loaded within `timeout_s`. After a timeout it
    keeps waiting (up to `late_wait_s`, forever by default) so a slow load
    that does finish can take the warning back.
    """
    if loaded.wait(timeout_s):
        return True

    report(explain_blank_window(url, reasons(), timeout_s))
    if loaded.wait(late_wait_s):
        report("✅ The Aura window loaded after all, ignore the warning above.")
    return False


def start_page_load_watchdog(
    window: Window,
    url: str,
    *,
    timeout_s: float = LOAD_TIMEOUT_S,
    report: Callable[[str], None] = print,
) -> threading.Thread:
    """Watch a pywebview window in the background. Call before webview.start().

    The error collector goes on pywebview's logger right away because WebView2
    fails while the window is being created, before `shown` fires.
    """
    collector = PywebviewErrorCollector()
    logger = logging.getLogger(PYWEBVIEW_LOGGER)
    logger.addHandler(collector)
    renderer: List[str] = []

    def remember_renderer(gui_renderer: str) -> None:
        # pywebview passes the engine it picked, e.g. "edgechromium" or "mshtml"
        renderer.append(gui_renderer)

    def reasons_so_far() -> List[str]:
        # Read once, when the warning prints. Detach here rather than at the
        # end: on a blank window the late-load wait below never finishes.
        logger.removeHandler(collector)
        return list(collector.reasons)

    def report_unless_closing(message: str) -> None:
        # Closing a window that never loaded is not something to warn about
        if not (window.events.closing.is_set() or window.events.closed.is_set()):
            report(message)

    def run() -> None:
        try:
            window.events.shown.wait()
            if LEGACY_IE_RENDERER in renderer:
                report_unless_closing(explain_legacy_renderer(url))
                return
            watch_page_load(
                window.events.loaded, url, reasons_so_far, timeout_s=timeout_s, report=report_unless_closing
            )
        finally:
            logger.removeHandler(collector)

    window.events.initialized += remember_renderer
    thread = threading.Thread(target=run, name="aura-page-load-watchdog", daemon=True)
    thread.start()
    return thread
