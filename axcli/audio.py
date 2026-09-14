"""Audio subsystem: text-to-speech output and speech-to-text input.

TTS: uses espeak-ng (Linux), say (macOS), or piper via subprocess.
     Zero pip dependencies — system packages only.
STT: future — requires vosk (pip install axcli[audio]).
"""
import os
import shutil
import subprocess
import threading
import queue


class Speaker:
    """Non-blocking TTS that queues text and speaks in background.

    New speech interrupts current speech (Emacspeak pattern).
    """

    def __init__(self):
        self._engine = _detect_tts_engine()
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._proc: subprocess.Popen | None = None
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        self._enabled = self._engine is not None
        self._rate = int(os.environ.get("AXCLI_TTS_RATE", "280"))

    @property
    def available(self) -> bool:
        return self._enabled

    def speak(self, text: str):
        """Queue text for speaking. Interrupts any current speech."""
        if not self._enabled:
            return
        self._interrupt()
        self._queue.put(text)

    def stop(self):
        """Stop current speech immediately."""
        self._interrupt()

    def shutdown(self):
        """Stop and clean up."""
        self._interrupt()
        self._queue.put(None)

    def _interrupt(self):
        """Kill current espeak process if running."""
        proc = self._proc
        if proc and proc.poll() is None:
            try:
                proc.kill()
                proc.wait(timeout=1)
            except Exception:
                pass
        # Drain queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def _worker(self):
        """Background thread: consume queue, speak each item."""
        while True:
            text = self._queue.get()
            if text is None:
                break
            self._speak_sync(text)

    def _speak_sync(self, text: str):
        """Speak text synchronously (called from worker thread)."""
        # Strip labels for cleaner speech
        text = text.replace("result: ", "").replace("status: ", "").replace("error: ", "error, ")
        # Strip ANSI
        import re
        text = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)

        if not text.strip():
            return

        try:
            if self._engine == "espeak-ng":
                self._proc = subprocess.Popen(
                    ["espeak-ng", "-s", str(self._rate), "--", text],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._proc.wait()
            elif self._engine == "say":
                self._proc = subprocess.Popen(
                    ["say", "-r", str(self._rate), "--", text],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._proc.wait()
        except Exception:
            pass


class Earcons:
    """Short audio cues for status events.

    Uses espeak-ng tone generation — no audio files needed.
    """

    def __init__(self):
        self._engine = _detect_tts_engine()

    def success(self):
        """Rising tone — command succeeded."""
        self._tone("[[{'=600' '=900'}]]")

    def error(self):
        """Falling tone — command failed."""
        self._tone("[[{'=600' '=400'}]]")

    def working(self):
        """Short tick — still running."""
        self._tone("[[{'=800'}]]")

    def received(self):
        """Click — input received."""
        self._tone("[[{'=1000'}]]")

    def _tone(self, ssml: str):
        if self._engine != "espeak-ng":
            return
        try:
            subprocess.Popen(
                ["espeak-ng", "-m", ssml],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


class Listener:
    """Push-to-talk speech-to-text using Vosk.

    Usage:
        listener = Listener()
        if listener.available:
            text = listener.listen()  # blocks until user stops speaking
    """

    def __init__(self):
        self._model = None
        self._available = False
        try:
            import vosk
            vosk.SetLogLevel(-1)  # suppress vosk logs
            model_path = os.path.expanduser("~/.cache/axcli/vosk-model")
            if os.path.isdir(model_path):
                self._model = vosk.Model(model_path)
                self._available = True
        except ImportError:
            pass
        except Exception:
            pass

    @property
    def available(self) -> bool:
        return self._available

    def listen(self, timeout: float = 10.0) -> str:
        """Record from microphone and return recognized text.

        Listens until silence is detected or timeout reached.
        Returns empty string on failure.
        """
        if not self._available:
            return ""

        try:
            import vosk
            import wave
            import tempfile

            # Record audio using arecord (Linux) or sox
            duration = int(timeout)
            tmpfile = tempfile.mktemp(suffix=".wav")

            # Try arecord first (ALSA), then sox (cross-platform)
            if shutil.which("arecord"):
                rec_cmd = [
                    "arecord", "-q", "-f", "S16_LE", "-r", "16000",
                    "-c", "1", "-d", str(duration), tmpfile,
                ]
            elif shutil.which("sox"):
                rec_cmd = [
                    "sox", "-q", "-d", "-r", "16000", "-c", "1",
                    "-b", "16", tmpfile, "trim", "0", str(duration),
                ]
            else:
                return ""

            print("axcli: Listening... (speak now, press Ctrl+C to stop)")
            try:
                proc = subprocess.run(rec_cmd, timeout=timeout + 2, capture_output=True)
            except subprocess.TimeoutExpired:
                pass
            except KeyboardInterrupt:
                # User pressed Ctrl+C to stop recording — this is expected
                pass

            if not os.path.exists(tmpfile):
                return ""

            # Recognize
            rec = vosk.KaldiRecognizer(self._model, 16000)
            with wave.open(tmpfile, "rb") as wf:
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    rec.AcceptWaveform(data)

            os.unlink(tmpfile)

            result = rec.FinalResult()
            import json
            text = json.loads(result).get("text", "")
            return text.strip()

        except Exception:
            return ""


def _detect_tts_engine() -> str | None:
    """Detect available TTS engine."""
    explicit = os.environ.get("AXCLI_TTS_ENGINE", "").lower()
    if explicit == "none":
        return None
    if explicit:
        return explicit

    if shutil.which("espeak-ng"):
        return "espeak-ng"
    if shutil.which("say"):  # macOS
        return "say"
    return None
