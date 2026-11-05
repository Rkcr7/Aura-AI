"""Tests for the blank-window watchdog (issue #10).

Run from the repo root:  python -m unittest discover -s tests/python
"""
import logging
import threading
import time
import unittest
from types import SimpleNamespace

from core import webview_watchdog as watchdog

URL = "http://127.0.0.1:8002"

# What pywebview 6.2.1 logged when WebView2 failed to start, copied from a real
# run with the runtime folder pointed at an empty directory
# (webview/platforms/edgechromium.py, on_webview_ready)
PYWEBVIEW_INIT_ERROR = (
    "WebView2 initialization failed with exception:\n "
    "Couldn't find a compatible Webview2 Runtime installation to host WebViews. "
    "---> System.IO.FileNotFoundException: The system cannot find the file specified. "
    "(Exception from HRESULT: 0x80070002)\n"
    "   --- End of inner exception stack trace ---\n"
    "   at Microsoft.Web.WebView2.Core.CoreWebView2Environment.<CreateAsync>d__102.MoveNext()\n"
    "--- End of stack trace from previous location where exception was thrown ---\n"
    "   at System.Runtime.ExceptionServices.ExceptionDispatchInfo.Throw()\n"
    "   at System.Runtime.CompilerServices.TaskAwaiter.HandleNonSuccessAndDebuggerNotification(Task task)\n"
    "   at Microsoft.Web.WebView2.WinForms.WebView2.<InitCoreWebView2Async>d__25.MoveNext()"
)


class Reports:
    """Collects what the watchdog would have printed."""

    def __init__(self):
        self.messages = []
        self.changed = threading.Event()

    def __call__(self, message):
        self.messages.append(message)
        self.changed.set()


class FakeEvent:
    """The parts of pywebview's Event the watchdog uses: wait/set/is_set and +=.

    Also records when it was set and every wait() the watchdog made, so tests
    can check the worker's actual state instead of guessing it with sleeps.
    """

    def __init__(self):
        self._event = threading.Event()
        self._handlers = []
        self.set_at = None
        self.waits = []  # (started_at, timeout, result)

    def __iadd__(self, handler):
        self._handlers.append(handler)
        return self

    def set(self, *args):
        for handler in self._handlers:
            handler(*args)
        self.set_at = time.monotonic()
        self._event.set()

    def is_set(self):
        return self._event.is_set()

    def wait(self, timeout=None):
        started_at = time.monotonic()
        result = self._event.wait(timeout)
        self.waits.append((started_at, timeout, result))
        return result


def wait_until(condition, timeout=2.0):
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError("timed out waiting for the watchdog")
        time.sleep(0.005)


def fake_window():
    names = ("initialized", "shown", "loaded", "closing", "closed")
    return SimpleNamespace(events=SimpleNamespace(**{name: FakeEvent() for name in names}))


class WatchPageLoadTests(unittest.TestCase):
    def test_page_that_loads_in_time_reports_nothing(self):
        loaded = threading.Event()
        loaded.set()
        reports = Reports()

        ok = watchdog.watch_page_load(loaded, URL, lambda: [], timeout_s=0.05, report=reports, late_wait_s=0.05)

        self.assertTrue(ok)
        self.assertEqual(reports.messages, [])

    def test_blank_window_names_the_webview2_failure_and_the_fix(self):
        reason = "WebView2 initialization failed with exception: Couldn't find a compatible Webview2 Runtime"
        reports = Reports()

        ok = watchdog.watch_page_load(
            threading.Event(), URL, lambda: [reason], timeout_s=0.05, report=reports, late_wait_s=0.05
        )

        self.assertFalse(ok)
        self.assertEqual(len(reports.messages), 1)
        message = reports.messages[0]
        self.assertIn("blank", message)
        self.assertIn("failed to start", message)
        self.assertIn(reason, message)
        self.assertIn(watchdog.WEBVIEW2_DOWNLOAD_URL, message)
        self.assertIn(URL, message)
        self.assertIn("NOT hidden from screen sharing", message)

    def test_blank_window_without_a_logged_reason_does_not_claim_webview2_failed(self):
        reports = Reports()

        watchdog.watch_page_load(threading.Event(), URL, lambda: [], timeout_s=0.05, report=reports, late_wait_s=0.05)

        message = reports.messages[0]
        self.assertIn("didn't report an error", message)
        self.assertNotIn("failed to start", message)
        # The splash is inline HTML, so a stall here is WebView2 itself, not the network
        self.assertIn("never finished starting", message)
        self.assertNotIn("firewall", message)
        self.assertIn(watchdog.WEBVIEW2_DOWNLOAD_URL, message)
        self.assertIn(URL, message)

    def test_a_late_load_takes_the_warning_back(self):
        loaded = threading.Event()
        reports = Reports()
        timer = threading.Timer(0.5, loaded.set)
        timer.start()

        ok = watchdog.watch_page_load(loaded, URL, lambda: [], timeout_s=0.05, report=reports, late_wait_s=5)

        timer.join()
        self.assertFalse(ok)
        self.assertEqual(len(reports.messages), 2)
        self.assertIn("loaded after all", reports.messages[1])


class ErrorCollectorTests(unittest.TestCase):
    def setUp(self):
        # Records reach the collector the way pywebview's do: through a logger,
        # which is where the handler's ERROR level is enforced
        self.collector = watchdog.PywebviewErrorCollector()
        self.logger = logging.getLogger(f"aura-test.{self.id()}")
        self.logger.propagate = False
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.collector)
        self.addCleanup(self.logger.removeHandler, self.collector)

    def test_keeps_the_reason_and_drops_the_dotnet_stack_trace(self):
        self.logger.error(PYWEBVIEW_INIT_ERROR)

        self.assertEqual(len(self.collector.reasons), 1)
        reason = self.collector.reasons[0]
        self.assertTrue(reason.startswith("WebView2 initialization failed with exception: Couldn't find"))
        self.assertTrue(reason.endswith("(Exception from HRESULT: 0x80070002)"), reason)
        self.assertNotIn("MoveNext", reason)
        self.assertNotIn("End of", reason)

    def test_reports_a_repeated_failure_once(self):
        # Loading the app URL makes WebView2 retry its start, so pywebview logs it twice
        self.logger.error(PYWEBVIEW_INIT_ERROR)
        self.logger.error(PYWEBVIEW_INIT_ERROR)

        self.assertEqual(len(self.collector.reasons), 1)

    def test_ignores_warnings(self):
        self.logger.warning("MSHTML is deprecated.")

        self.assertEqual(self.collector.reasons, [])

    def test_ignores_errors_that_are_not_about_webview2(self):
        # pywebview logs exceptions from any event handler, Aura's own included
        self.logger.error("'NoneType' object has no attribute 'set_window_handle'")

        self.assertEqual(self.collector.reasons, [])


class StartPageLoadWatchdogTests(unittest.TestCase):
    def setUp(self):
        self.window = fake_window()
        self.reports = Reports()
        self.logger = logging.getLogger("pywebview")
        self.handlers_before = list(self.logger.handlers)

    def start(self, timeout_s=0.05):
        return watchdog.start_page_load_watchdog(self.window, URL, timeout_s=timeout_s, report=self.reports)

    def test_a_healthy_launch_reports_nothing_and_detaches_from_the_logger(self):
        thread = self.start()
        self.window.events.initialized.set("edgechromium")
        self.window.events.loaded.set()
        self.window.events.shown.set()
        thread.join(2)

        self.assertFalse(thread.is_alive())
        self.assertEqual(self.reports.messages, [])
        self.assertEqual(self.logger.handlers, self.handlers_before)

    def test_the_clock_starts_when_the_window_shows(self):
        events = self.window.events
        thread = self.start(timeout_s=0.2)
        events.initialized.set("edgechromium")
        time.sleep(0.3)  # slow startup before the window appears: longer than timeout_s
        events.shown.set()
        events.loaded.set()
        thread.join(2)

        self.assertEqual(self.reports.messages, [])
        # The load timeout only started once the window was shown
        self.assertTrue(events.loaded.waits, "the watchdog never waited for the page")
        self.assertGreaterEqual(events.loaded.waits[0][0], events.shown.set_at)

    def test_reports_the_error_pywebview_logged_before_the_window_showed(self):
        thread = self.start()
        self.window.events.initialized.set("edgechromium")
        # WebView2 fails during window creation, before pywebview fires `shown`
        self.logger.error(PYWEBVIEW_INIT_ERROR)
        self.window.events.shown.set()
        self.assertTrue(self.reports.changed.wait(2), "watchdog never reported the blank window")
        # Detached once reported, though the late-load wait is still running
        self.assertEqual(self.logger.handlers, self.handlers_before)
        self.window.events.loaded.set()  # let the late-load wait finish so the thread exits
        thread.join(2)

        self.assertIn("Couldn't find a compatible Webview2 Runtime", self.reports.messages[0])
        self.assertNotIn(PYWEBVIEW_INIT_ERROR, self.reports.messages[0])  # no raw stack trace
        self.assertFalse(thread.is_alive())

    def test_the_internet_explorer_fallback_is_reported_right_away(self):
        thread = self.start(timeout_s=60)
        self.window.events.initialized.set("mshtml")
        self.window.events.shown.set()
        thread.join(2)

        self.assertFalse(thread.is_alive(), "should not wait for the load timeout")
        self.assertEqual(len(self.reports.messages), 1)
        message = self.reports.messages[0]
        self.assertIn("Internet Explorer", message)
        self.assertIn(watchdog.WEBVIEW2_DOWNLOAD_URL, message)
        # IE can also be forced, so it must not claim WebView2 is definitely missing
        self.assertIn("Usually", message)
        self.assertIn("PYWEBVIEW_GUI", message)
        self.assertEqual(self.logger.handlers, self.handlers_before)

    def test_says_nothing_when_the_window_is_closed_before_it_loads(self):
        events = self.window.events
        thread = self.start()
        events.initialized.set("edgechromium")
        events.shown.set()
        events.closing.set()
        # Let the load timeout actually expire before checking it stayed quiet
        wait_until(lambda: any(result is False for _, _, result in events.loaded.waits))
        self.assertEqual(self.reports.messages, [])
        events.loaded.set()
        thread.join(2)

        self.assertEqual(self.reports.messages, [])


if __name__ == "__main__":
    unittest.main()
