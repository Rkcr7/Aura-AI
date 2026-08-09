import asyncio
import base64
import json

import websockets

from core.config import settings
from services.stt_service import build_programming_keyterms

# 60db real-time STT WebSocket endpoint (wss for security).
# Auth is via the apiKey query parameter, per the 60db WebSocket STT spec.
SIXTYDB_WS_URL = "wss://api.60db.ai/ws/stt"

# The browser AudioWorklet emits 16-bit signed little-endian mono PCM, and the
# Deepgram path is hardcoded to 48 kHz. We mirror that exactly so both engines
# consume the identical audio stream — 60db's "linear" encoding == raw PCM16.
SIXTYDB_SAMPLE_RATE = 48000


async def verify_sixtydb_api_key():
    """
    Verifies the 60db API key by opening the STT WebSocket and waiting for the
    `connection_established` handshake. This also implicitly validates that the
    workspace has a sufficient credit balance (the server closes with code 1008
    otherwise). Mirrors `verify_deepgram_api_key` in intent.
    Returns True if the key is valid, False otherwise.
    """
    if not settings.SIXTYDB_API_KEY:
        return False

    url = f"{SIXTYDB_WS_URL}?apiKey={settings.SIXTYDB_API_KEY}"
    try:
        ws = await asyncio.wait_for(websockets.connect(url, max_size=None), timeout=10)
    except Exception as e:
        print(f"ERROR: 60db API key verification failed to connect: {e}")
        return False

    try:
        raw = await asyncio.wait_for(ws.recv(), timeout=10)
        msg = json.loads(raw)
        if "connection_established" in msg:
            print("INFO: 60db API key is valid.")
            return True
        if "error" in msg or msg.get("type") == "error":
            print(f"ERROR: 60db verification returned error: {msg}")
            return False
        # Any other well-formed first message still implies an authenticated socket.
        return True
    except Exception as e:
        print(f"ERROR: A problem occurred while verifying 60db key: {e}")
        return False
    finally:
        try:
            await ws.close()
        except Exception:
            pass


class SixtyDBManager:
    """
    Manages a connection to 60db for live transcription.

    This is a drop-in alternative to `DeepgramManager`: it exposes the same
    public surface used by the session layer — `start()`, `send_audio()` and
    `finish()` — and invokes `transcript_callback` with the identical
    `{speaker, transcript, is_final}` contract so the rest of the app does not
    need to know which engine is active.
    """

    def __init__(self, transcript_callback, user_languages=None):
        self.transcript_callback = transcript_callback
        self.user_languages = user_languages or []
        self.ws = None
        self.is_connected = False  # True only once the session is ready for audio
        self.stop_event = asyncio.Event()
        self.sample_rate = SIXTYDB_SAMPLE_RATE
        self._recv_task = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_base_delay = 1.0  # seconds

    async def start(self):
        """Opens the 60db connection and begins the transcription session."""
        if not settings.SIXTYDB_API_KEY:
            print("❌ ERROR: SIXTYDB_API_KEY is not set; cannot start 60db STT.")
            return

        self.stop_event.clear()
        url = f"{SIXTYDB_WS_URL}?apiKey={settings.SIXTYDB_API_KEY}"

        try:
            self.ws = await asyncio.wait_for(websockets.connect(url, max_size=None), timeout=10)
        except Exception as e:
            print(f"❌ ERROR: Could not connect to 60db: {e}")
            asyncio.create_task(self._reconnect())
            return

        # The spec requires waiting for `connection_established` before sending `start`.
        try:
            raw = await asyncio.wait_for(self.ws.recv(), timeout=10)
            handshake = json.loads(raw)
        except Exception as e:
            print(f"❌ ERROR: 60db handshake failed: {e}")
            await self._safe_close()
            asyncio.create_task(self._reconnect())
            return

        if "connection_established" not in handshake:
            print(f"❌ ERROR: Unexpected 60db handshake message: {handshake}")
            await self._safe_close()
            return
        print("🔗 60db connection established")

        # Reuse the same boosted vocabulary as Deepgram. 60db surfaces up to ~30
        # terms to its LLM refinement pass, so we keep the list compact.
        terms = build_programming_keyterms(self.user_languages)[:30]

        start_msg = {
            "type": "start",
            # Spoken language is English, matching the Deepgram path (language="en").
            "languages": ["en"],
            "config": {
                "encoding": "linear",
                "sample_rate": self.sample_rate,
                "utterance_end_ms": 1000,       # mirror Deepgram's utterance_end_ms
                "continuous_mode": True,
                "interim_results_frequency": 300,
                "audio_enhancement": "adaptive",
            },
        }
        if terms:
            start_msg["context"] = {"terms": terms}

        try:
            await self.ws.send(json.dumps(start_msg))
        except Exception as e:
            print(f"❌ ERROR: Failed to send 60db start message: {e}")
            await self._safe_close()
            asyncio.create_task(self._reconnect())
            return

        # Begin reading server events. `session_started` flips is_connected on.
        self._recv_task = asyncio.create_task(self._receive_loop())
        # Safety net: if the server doesn't emit an explicit session-started ack
        # (key naming varies), enable audio after a short grace period anyway.
        asyncio.create_task(self._enable_audio_fallback())
        self._reconnect_attempts = 0
        print("✅ 60db STT session starting...")

    async def _enable_audio_fallback(self):
        await asyncio.sleep(1.5)
        if not self.is_connected and not self.stop_event.is_set() and self.ws:
            print("⚠️ 60db: no explicit session_started ack — enabling audio anyway")
            self.is_connected = True

    async def _receive_loop(self):
        """Reads and dispatches server messages until the socket closes."""
        try:
            async for raw in self.ws:
                if self.stop_event.is_set():
                    break
                try:
                    msg = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    continue
                await self._handle_message(msg)
        except websockets.exceptions.ConnectionClosed:
            if not self.stop_event.is_set():
                print("⚠️ Unexpected 60db close, attempting reconnect...")
                self.is_connected = False
                asyncio.create_task(self._reconnect())
        except Exception as e:
            if not self.stop_event.is_set():
                print(f"❌ 60db receive loop error: {e}")
                self.is_connected = False
                asyncio.create_task(self._reconnect())

    async def _handle_message(self, msg):
        """Routes a single decoded server message."""
        if "connection_established" in msg:
            return

        if "session_started" in msg or msg.get("type") == "session_started":
            self.is_connected = True
            print("✅ 60db session started — ready for audio")
            return

        if "error" in msg or msg.get("type") == "error":
            err = msg.get("error") or msg.get("message") or msg
            print(f"❌ 60db error: {err}")
            return

        if msg.get("type") == "transcription":
            await self._handle_transcription(msg)
            return

        # speech_started / session_stopped / billing summaries are not needed here.

    async def _handle_transcription(self, msg):
        if self.stop_event.is_set():
            return

        transcript = (msg.get("text") or "").strip()
        # An empty final result signals rejected audio (silence / low confidence /
        # hallucination guard) — skip it, exactly like an empty Deepgram transcript.
        if not transcript:
            return

        is_final = bool(msg.get("is_final", False))
        speech_final = bool(msg.get("speech_final", False))

        # 60db does not provide a speaker index in non-diarized mode, so we default
        # to speaker 0 (candidate) — the same default DeepgramManager uses.
        speaker = msg.get("speaker", 0)
        if speaker is None:
            speaker = 0

        # 60db can emit two-phase finals when context is supplied: a fast
        # dict-corrected result (speech_final=False) followed by the LLM-refined
        # canonical result (speech_final=True). Map ONLY the canonical result to the
        # app's `is_final=True` so each utterance is processed exactly once; treat
        # everything else as interim. Without context, both flags are True and this
        # still yields a single final.
        final = speech_final

        data = {
            "speaker": speaker,
            "transcript": transcript,
            "is_final": final,
        }

        if final:
            print(f"✅ FINAL RESULT (60db): Speaker {speaker} - '{transcript}'")
        await self.transcript_callback(data)

    async def _reconnect(self):
        """Attempt to reconnect to 60db with exponential backoff."""
        if self.stop_event.is_set():
            return
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            print(f"❌ 60db: max reconnect attempts ({self._max_reconnect_attempts}) reached, giving up")
            return

        self._reconnect_attempts += 1
        delay = self._reconnect_base_delay * (2 ** (self._reconnect_attempts - 1))
        print(f"🔄 60db reconnect attempt {self._reconnect_attempts}/{self._max_reconnect_attempts} in {delay:.1f}s...")
        await asyncio.sleep(delay)

        if self.stop_event.is_set():
            return

        await self.start()

    async def send_audio(self, audio_chunk, source='unknown'):
        """Sends a raw PCM16 audio chunk to 60db as a base64 JSON frame."""
        if not (self.is_connected and self.ws and not self.stop_event.is_set()):
            return
        try:
            encoded = base64.b64encode(audio_chunk).decode("ascii")
            await self.ws.send(json.dumps({
                "type": "audio",
                "audio": encoded,
                "encoding": "linear",
                "sample_rate": self.sample_rate,
            }))
        except websockets.exceptions.ConnectionClosed:
            self.is_connected = False
        except Exception as e:
            print(f"❌ 60db send_audio error: {e}")

    async def _safe_close(self):
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None

    async def finish(self):
        """Signals the connection to stop and closes it."""
        print("🛑 Closing 60db connection...")
        self.stop_event.set()
        self.is_connected = False

        if self.ws:
            try:
                await self.ws.send(json.dumps({"type": "stop"}))
            except Exception:
                pass
            await self._safe_close()

        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass

        print("✅ 60db connection closed successfully")
