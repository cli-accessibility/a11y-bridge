"""Detect user context: sighted vs screen reader."""
import os
import shutil


def needs_accessible_mode() -> bool:
    """Return True if output should use text-only accessibility mode.

    Checks (any triggers accessible mode):
    - NO_COLOR env var set and non-empty
    - TERM=dumb
    - A11Y_SCREEN_READER env var set
    - Known screen reader process running (best-effort)
    """
    if os.environ.get("NO_COLOR", ""):
        return True
    if os.environ.get("TERM", "") == "dumb":
        return True
    if os.environ.get("A11Y_SCREEN_READER", ""):
        return True
    return _screen_reader_running()


def _screen_reader_running() -> bool:
    """Best-effort detection of running screen readers."""
    # ponytail: pgrep check, no deps. False negative is fine — user can set A11Y_SCREEN_READER=1
    if not shutil.which("pgrep"):
        return False
    import subprocess
    for name in ("orca", "nvda", "jaws", "narrator", "voiceover"):
        try:
            result = subprocess.run(
                ["pgrep", "-x", name],
                capture_output=True, timeout=2,
            )
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    return False
