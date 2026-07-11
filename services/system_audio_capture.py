# services/system_audio_capture.py — native macOS system-audio capture.
#
# WKWebView's getDisplayMedia() does not expose system audio on macOS (only
# screen video is returned — see web/js/audio_handler.js's fallback to
# "mic-only mode"), so there is no way to hear a meeting app's audio (Zoom,
# Meet, Teams, ...) through the browser layer at all. This module captures
# whole-system audio output directly via ScreenCaptureKit (macOS 13+) and
# feeds it straight into the existing Deepgram pipeline, bypassing the
# WebSocket/frontend entirely.
import array
import asyncio
import platform
from typing import Callable, Optional

IS_MACOS = platform.system() == "Darwin"

if IS_MACOS:
    import objc
    from Foundation import NSObject
    import ScreenCaptureKit as SCK
    import CoreMedia as CM
    import Quartz
else:
    NSObject = object
    SCK = None
    CM = None
    Quartz = None

# Must match services/stt_service.py LiveOptions (encoding="linear16").
SAMPLE_RATE = 48000
CHANNEL_COUNT = 1


def has_screen_recording_permission() -> bool:
    """Check current Screen Recording (TCC) authorization without prompting."""
    if not IS_MACOS:
        return False
    return bool(Quartz.CGPreflightScreenCaptureAccess())


def request_screen_recording_permission() -> bool:
    """Trigger the native macOS Screen Recording permission dialog.

    Unlike mic/camera, granting this for an already-running process does NOT
    take effect until the app is fully quit and relaunched — that's a macOS
    quirk specific to Screen Recording, not a bug here.
    """
    if not IS_MACOS:
        return False
    return bool(Quartz.CGRequestScreenCaptureAccess())


def _extract_pcm16(sample_buffer) -> bytes:
    """Extract interleaved PCM from a CMSampleBuffer and convert Float32 -> Int16.

    ScreenCaptureKit always delivers audio as 32-bit float PCM (there is no
    bit-depth option on SCStreamConfiguration); Deepgram expects 16-bit
    linear PCM, so we convert here the same way the browser's AudioWorklet
    already does for mic/browser-captured audio (web/js/audio_processor.js).
    """
    block_buffer = CM.CMSampleBufferGetDataBuffer(sample_buffer)
    if not block_buffer:
        return b""
    length = CM.CMBlockBufferGetDataLength(block_buffer)
    if length <= 0:
        return b""
    status, raw_bytes = CM.CMBlockBufferCopyDataBytes(block_buffer, 0, length, None)
    if status != 0 or not raw_bytes:
        return b""

    floats = array.array("f")
    floats.frombytes(bytes(raw_bytes))

    pcm16 = array.array("h", bytes(len(floats) * 2))
    for i, sample in enumerate(floats):
        clamped = max(-1.0, min(1.0, sample))
        pcm16[i] = int(clamped * 32767)
    return pcm16.tobytes()


if IS_MACOS:

    class _SystemAudioStreamOutput(NSObject):
        """SCStreamOutput/SCStreamDelegate — receives raw audio sample buffers
        on an internal ScreenCaptureKit thread and hands PCM back to asyncio."""

        def initWithCallback_loop_(self, on_pcm_chunk, loop):
            self = objc.super(_SystemAudioStreamOutput, self).init()
            if self is None:
                return None
            self._on_pcm_chunk = on_pcm_chunk
            self._loop = loop
            return self

        def stream_didOutputSampleBuffer_ofType_(self, stream, sample_buffer, of_type):
            if of_type != SCK.SCStreamOutputTypeAudio:
                return
            try:
                pcm16 = _extract_pcm16(sample_buffer)
            except Exception as exc:
                print(f"⚠️ System audio: failed to extract PCM from sample buffer: {exc}")
                return
            if pcm16 and self._loop and not self._loop.is_closed():
                self._loop.call_soon_threadsafe(self._on_pcm_chunk, pcm16)

        def stream_didStopWithError_(self, stream, error):
            print(f"⚠️ System audio capture stopped by the system: {error}")


class SystemAudioCapture:
    """Captures whole-system audio output and delivers 16-bit PCM chunks."""

    def __init__(self):
        self._stream = None
        self._output = None
        self._running = False

    async def start(self, on_pcm_chunk: Callable[[bytes], None]) -> bool:
        """Start capturing system audio. Returns False (never raises) on any
        failure — system audio is a best-effort enhancement, not required for
        the interview to function (mic-only still works without it)."""
        if not IS_MACOS:
            return False
        if not has_screen_recording_permission():
            print("⚠️ System audio capture: Screen Recording permission not granted — skipping.")
            print("   Grant it in System Settings → Privacy & Security → Screen Recording, then fully restart Aura.")
            return False

        loop = asyncio.get_event_loop()
        try:
            content = await self._get_shareable_content(loop)
            displays = content.displays()
            if not displays:
                print("⚠️ System audio capture: no displays found.")
                return False
            display = displays[0]

            content_filter = SCK.SCContentFilter.alloc().initWithDisplay_excludingWindows_(display, [])

            config = SCK.SCStreamConfiguration.alloc().init()
            config.setCapturesAudio_(True)
            config.setExcludesCurrentProcessAudio_(True)
            config.setSampleRate_(SAMPLE_RATE)
            config.setChannelCount_(CHANNEL_COUNT)
            # We only want audio — minimize video capture overhead.
            config.setWidth_(2)
            config.setHeight_(2)
            config.setShowsCursor_(False)

            self._output = _SystemAudioStreamOutput.alloc().initWithCallback_loop_(on_pcm_chunk, loop)
            self._stream = SCK.SCStream.alloc().initWithFilter_configuration_delegate_(
                content_filter, config, self._output
            )

            ok, error = self._stream.addStreamOutput_type_sampleHandlerQueue_error_(
                self._output, SCK.SCStreamOutputTypeAudio, None, None
            )
            if not ok:
                print(f"❌ System audio capture: failed to add stream output: {error}")
                return False

            started = await self._start_capture()
            if not started:
                return False

            self._running = True
            print("🔊 System audio capture started (ScreenCaptureKit)")
            return True
        except Exception as exc:
            print(f"❌ System audio capture failed to start: {exc}")
            return False

    async def _get_shareable_content(self, loop):
        future = loop.create_future()

        def handler(content, error):
            def _resolve():
                if future.done():
                    return
                if error is not None:
                    future.set_exception(RuntimeError(str(error)))
                else:
                    future.set_result(content)
            loop.call_soon_threadsafe(_resolve)

        SCK.SCShareableContent.getShareableContentWithCompletionHandler_(handler)
        return await future

    async def _start_capture(self) -> bool:
        loop = asyncio.get_event_loop()
        future = loop.create_future()

        def handler(error):
            def _resolve():
                if not future.done():
                    future.set_result(error)
            loop.call_soon_threadsafe(_resolve)

        self._stream.startCaptureWithCompletionHandler_(handler)
        error = await future
        if error is not None:
            print(f"❌ System audio capture: startCaptureWithCompletionHandler error: {error}")
            return False
        return True

    async def stop(self):
        if not self._stream or not self._running:
            return
        self._running = False
        loop = asyncio.get_event_loop()
        future = loop.create_future()

        def handler(error):
            def _resolve():
                if not future.done():
                    future.set_result(error)
            loop.call_soon_threadsafe(_resolve)

        try:
            self._stream.stopCaptureWithCompletionHandler_(handler)
            await asyncio.wait_for(future, timeout=5.0)
        except Exception as exc:
            print(f"⚠️ Error stopping system audio capture: {exc}")
        finally:
            self._stream = None
            self._output = None
            print("🔇 System audio capture stopped")
