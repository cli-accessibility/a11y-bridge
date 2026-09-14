"""Audio subsystem: text-to-speech output and speech-to-text input.

TTS: uses espeak-ng (Linux), say (macOS), or piper via subprocess.
     Zero pip dependencies — system packages only.
STT: future — requires vosk (pip install a11y-bridge[audio]).
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
        self._rate = int(os.environ.get("A11Y_TTS_RATE", "170"))

    @property
    def available(self) -> bool:
        return self._enabled

    def speak(self, text: str):
        """Queue text for speaking. Interrupts any current speech."""
        if not self._enabled:
            return
        self._interrupt()
        self._queue.put(text)

    def enqueue(self, text: str):
        """Queue text without interrupting current speech. Use for multi-line output."""
        if not self._enabled:
            return
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
        import re

        # Strip labels for cleaner speech
        text = text.replace("result: ", "").replace("status: ", "").replace("error: ", "error, ")
        # Strip ANSI
        text = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)
        # Replace em-dash and en-dash with comma (piper chokes on these)
        text = text.replace("—", ", ").replace("–", ", ")
        # Replace slashes in repo paths with " slash " for speech
        text = re.sub(r"(\w)/(\w)", r"\1 slash \2", text)
        # Shorten URLs — say "link to example.com" instead of the full URL
        text = re.sub(r"https?://([^/\s]+)\S*", r"link to \1", text)
        # Shorten SHA hashes (>12 hex chars) — say "hash" instead of reading 64 chars
        text = re.sub(r"\b[a-f0-9]{12,}\b", "hash", text)
        # Shorten image digests (sha256:abc123...)
        text = re.sub(r"sha256:[a-f0-9]+", "digest", text)
        # Remove special characters that confuse TTS
        text = re.sub(r"[`\"'{}()\[\]<>|\\~^]", " ", text)
        # Clean up repeated dots/dashes
        text = re.sub(r"[.\-_]{3,}", " ", text)
        # Clean up multiple spaces
        text = re.sub(r"\s{2,}", " ", text)

        text = text.strip()
        if not text:
            return
        # Truncate very long lines — piper struggles with >200 chars
        if len(text) > 200:
            text = text[:200]

        try:
            if self._engine == "piper":
                self._speak_piper(text)
            elif self._engine == "espeak-ng":
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

    def _speak_piper(self, text: str):
        """Speak using Piper neural TTS — natural sounding voice."""
        model_dir = os.path.expanduser("~/.cache/a11y-bridge/piper")
        model = os.environ.get("A11Y_PIPER_MODEL", os.path.join(model_dir, "en_US-lessac-medium.onnx"))
        if not os.path.exists(model):
            # Fallback to espeak-ng if piper model missing
            self._proc = subprocess.Popen(
                ["espeak-ng", "-s", str(self._rate), "--", text],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            self._proc.wait()
            return
        # Pipe text through piper CLI → audio player
        if shutil.which("paplay"):
            player_cmd = "paplay --raw --rate=22050 --format=s16le --channels=1"
        elif shutil.which("aplay"):
            player_cmd = "aplay -r 22050 -f S16_LE -t raw -c 1 -q"
        else:
            return
        self._proc = subprocess.Popen(
            f'echo {_shell_escape(text)} | piper --model {_shell_escape(model)} --output-raw 2>/dev/null | {player_cmd}',
            shell=True,  # ponytail: shell=True needed for pipe chain; text is escaped
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._proc.wait()


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
    """Push-to-talk speech-to-text.

    Supports two engines (auto-detected, Whisper preferred):
    - faster-whisper: high accuracy, ~1.5GB model, 1-3s processing
    - vosk: lower accuracy, ~50MB model, ~200ms processing

    Override: A11Y_STT_ENGINE=whisper or A11Y_STT_ENGINE=vosk
    Whisper model: A11Y_WHISPER_MODEL=medium (default), small, large-v3

    Usage:
        listener = Listener()
        if listener.available:
            text = listener.listen()
    """

    def __init__(self):
        self._engine = _detect_stt_engine()
        self._whisper_model = None
        self._vosk_model = None
        self._available = False

        if self._engine == "whisper":
            try:
                from faster_whisper import WhisperModel
                model_size = os.environ.get("A11Y_WHISPER_MODEL", "medium")
                print(f"a11y-bridge: Loading Whisper {model_size} model...")
                self._whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
                self._available = True
            except Exception as e:
                print(f"a11y-bridge: Whisper failed ({e}), falling back to Vosk")
                self._engine = "vosk"

        if self._engine == "vosk":
            try:
                import vosk
                vosk.SetLogLevel(-1)
                model_path = os.path.expanduser("~/.cache/a11y-bridge/vosk-model")
                if os.path.isdir(model_path):
                    self._vosk_model = vosk.Model(model_path)
                    self._available = True
            except ImportError:
                pass

    @property
    def available(self) -> bool:
        return self._available

    @property
    def engine_name(self) -> str:
        return self._engine or "none"

    def listen(self) -> str:
        """Record from microphone and return recognized text.

        Records until user presses Enter. Returns empty string on failure.
        """
        if not self._available:
            return ""

        tmpfile = self._record()
        if not tmpfile:
            return ""

        try:
            if self._engine == "whisper":
                return self._recognize_whisper(tmpfile)
            else:
                return self._recognize_vosk(tmpfile)
        finally:
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)

    def _record(self) -> str:
        """Record audio until Enter is pressed. Returns path to wav file."""
        import tempfile
        tmpfile = tempfile.mktemp(suffix=".wav")

        if shutil.which("arecord"):
            rec_cmd = ["arecord", "-q", "-f", "S16_LE", "-r", "16000", "-c", "1", tmpfile]
        elif shutil.which("sox"):
            rec_cmd = ["sox", "-q", "-d", "-r", "16000", "-c", "1", "-b", "16", tmpfile]
        else:
            print("a11y-bridge: No recording tool found. Install alsa-utils (arecord) or sox.")
            return ""

        print("a11y-bridge: Listening... (press Enter when done)")
        proc = subprocess.Popen(rec_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass

        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()

        return tmpfile if os.path.exists(tmpfile) else ""

    def _recognize_whisper(self, audio_path: str) -> str:
        """Recognize speech using faster-whisper."""
        try:
            print("a11y-bridge: Processing speech...")
            segments, info = self._whisper_model.transcribe(audio_path, beam_size=5)
            text = " ".join(seg.text.strip() for seg in segments)
            return text.strip()
        except Exception:
            return ""

    def _recognize_vosk(self, audio_path: str) -> str:
        """Recognize speech using Vosk."""
        try:
            import vosk
            import wave
            import json

            rec = vosk.KaldiRecognizer(self._vosk_model, 16000)
            with wave.open(audio_path, "rb") as wf:
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    rec.AcceptWaveform(data)

            result = rec.FinalResult()
            return json.loads(result).get("text", "").strip()
        except Exception:
            return ""


def _detect_stt_engine() -> str | None:
    """Detect available STT engine. Whisper preferred over Vosk."""
    explicit = os.environ.get("A11Y_STT_ENGINE", "").lower()
    if explicit:
        return explicit if explicit != "none" else None

    try:
        import faster_whisper  # noqa: F401
        return "whisper"
    except ImportError:
        pass

    try:
        import vosk  # noqa: F401
        model_path = os.path.expanduser("~/.cache/a11y-bridge/vosk-model")
        if os.path.isdir(model_path):
            return "vosk"
    except ImportError:
        pass

    return None


def _shell_escape(s: str) -> str:
    """Escape string for shell use in subprocess with shell=True."""
    import shlex
    return shlex.quote(s)


def _detect_tts_engine() -> str | None:
    """Detect available TTS engine."""
    explicit = os.environ.get("A11Y_TTS_ENGINE", "").lower()
    if explicit == "none":
        return None
    if explicit:
        return explicit

    # Prefer piper (natural voice) if model exists
    piper_model = os.path.expanduser("~/.cache/a11y-bridge/piper/en_US-lessac-medium.onnx")
    if shutil.which("piper") and os.path.exists(piper_model):
        return "piper"
    # ponytail: also check if piper is importable (pip install piper-tts adds CLI)
    if os.path.exists(piper_model):
        try:
            import piper  # noqa: F401
            return "piper"
        except ImportError:
            pass
    if shutil.which("espeak-ng"):
        return "espeak-ng"
    if shutil.which("say"):  # macOS
        return "say"
    return None
