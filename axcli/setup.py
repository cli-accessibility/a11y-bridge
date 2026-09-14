"""axcli setup — download models and check prerequisites."""
import os
import shutil
import urllib.request
import zipfile


PIPER_MODEL_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
PIPER_CONFIG_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
PIPER_DIR = os.path.expanduser("~/.cache/axcli/piper")
PIPER_MODEL = os.path.join(PIPER_DIR, "en_US-lessac-medium.onnx")
PIPER_CONFIG = os.path.join(PIPER_DIR, "en_US-lessac-medium.onnx.json")

VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
VOSK_DIR = os.path.expanduser("~/.cache/axcli")
VOSK_MODEL = os.path.join(VOSK_DIR, "vosk-model")


def run_setup() -> int:
    """Check prerequisites and download models."""
    print("axcli setup")
    print("=" * 40)
    print()

    ok = True

    # System packages
    print("System packages:")
    ok &= _check_binary("espeak-ng", "TTS engine (fallback)", "sudo dnf install espeak-ng")
    ok &= _check_binary("paplay", "Audio playback (for Piper)", "sudo dnf install pulseaudio-utils")
    ok &= _check_binary("arecord", "Microphone recording (for voice input)", "sudo dnf install alsa-utils")
    print()

    # Python packages
    print("Python packages:")
    ok &= _check_import("piper", "Piper neural TTS", "pip install axcli[audio]")
    ok &= _check_import("vosk", "Vosk speech-to-text", "pip install axcli[audio]")
    print()

    # Models
    print("Models:")
    if os.path.exists(PIPER_MODEL) and os.path.exists(PIPER_CONFIG):
        size = os.path.getsize(PIPER_MODEL) // (1024 * 1024)
        print(f"  [OK] Piper voice model ({size}MB) at {PIPER_DIR}")
    else:
        print(f"  [MISSING] Piper voice model")
        if _confirm("  Download Piper voice model (~60MB)?"):
            ok &= _download_piper()
        else:
            ok = False

    if os.path.isdir(VOSK_MODEL):
        print(f"  [OK] Vosk speech model at {VOSK_MODEL}")
    else:
        print(f"  [MISSING] Vosk speech model")
        if _confirm("  Download Vosk speech model (~50MB)?"):
            ok &= _download_vosk()
        else:
            ok = False

    print()

    # AI provider
    print("AI provider (for --askai):")
    ai_key = os.environ.get("AXCLI_AI_KEY") or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if ai_key:
        provider = os.environ.get("AXCLI_AI_PROVIDER", "auto-detected")
        print(f"  [OK] API key set (provider: {provider})")
    elif shutil.which("ollama"):
        print(f"  [OK] Ollama found at {shutil.which('ollama')}")
    else:
        print(f"  [MISSING] No AI provider configured")
        print(f"  Set AXCLI_AI_KEY and AXCLI_AI_PROVIDER, or install Ollama")
        # Not a hard failure — AI is optional

    print()
    if ok:
        print("Setup complete. Ready to use:")
        print("  axcli gh pr list                     # wrapper mode")
        print("  axcli --domain audio gh pr list       # with voice output")
        print("  axcli --askai gh                      # AI interactive mode")
        print("  axcli --domain audio --askai gh       # AI + voice")
    else:
        print("Some components are missing. axcli core still works:")
        print("  axcli gh pr list")

    return 0


def _check_binary(name: str, purpose: str, install_hint: str) -> bool:
    path = shutil.which(name)
    if path:
        print(f"  [OK] {name} — {purpose}")
        return True
    else:
        print(f"  [MISSING] {name} — {purpose}")
        print(f"    Install: {install_hint}")
        return False


def _check_import(module: str, purpose: str, install_hint: str) -> bool:
    try:
        __import__(module)
        print(f"  [OK] {module} — {purpose}")
        return True
    except ImportError:
        print(f"  [MISSING] {module} — {purpose}")
        print(f"    Install: {install_hint}")
        return False


def _confirm(prompt: str) -> bool:
    try:
        resp = input(f"{prompt} [Y/n] ").strip().lower()
        return resp in ("", "y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def _download_piper() -> bool:
    try:
        os.makedirs(PIPER_DIR, exist_ok=True)
        print(f"  Downloading voice model...")
        urllib.request.urlretrieve(PIPER_MODEL_URL, PIPER_MODEL, _progress)
        print()
        print(f"  Downloading voice config...")
        urllib.request.urlretrieve(PIPER_CONFIG_URL, PIPER_CONFIG)
        size = os.path.getsize(PIPER_MODEL) // (1024 * 1024)
        print(f"  [OK] Piper voice model downloaded ({size}MB)")
        return True
    except Exception as e:
        print(f"  [FAIL] Download failed: {e}")
        return False


def _download_vosk() -> bool:
    try:
        os.makedirs(VOSK_DIR, exist_ok=True)
        zippath = os.path.join(VOSK_DIR, "vosk-model.zip")
        print(f"  Downloading speech model...")
        urllib.request.urlretrieve(VOSK_MODEL_URL, zippath, _progress)
        print()
        print(f"  Extracting...")
        with zipfile.ZipFile(zippath, "r") as zf:
            zf.extractall(VOSK_DIR)
        # Rename extracted dir
        extracted = os.path.join(VOSK_DIR, "vosk-model-small-en-us-0.15")
        if os.path.isdir(extracted):
            if os.path.isdir(VOSK_MODEL):
                shutil.rmtree(VOSK_MODEL)
            os.rename(extracted, VOSK_MODEL)
        os.unlink(zippath)
        print(f"  [OK] Vosk speech model downloaded")
        return True
    except Exception as e:
        print(f"  [FAIL] Download failed: {e}")
        return False


def _progress(block_num: int, block_size: int, total_size: int):
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(100, downloaded * 100 // total_size)
        mb = downloaded // (1024 * 1024)
        total_mb = total_size // (1024 * 1024)
        print(f"\r  {mb}MB / {total_mb}MB ({pct}%)", end="", flush=True)
