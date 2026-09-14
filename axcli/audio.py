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
