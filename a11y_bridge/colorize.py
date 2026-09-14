"""Add semantic color to plain text output.

When a sighted user runs a11y-bridge on a binary that produces plain/uncolored
output, this module detects patterns and adds ANSI color to enhance
readability — the inverse of stripping.
"""
import re

# ANSI SGR helpers
_GREEN = "\x1b[32m"
_RED = "\x1b[31m"
_YELLOW = "\x1b[33m"
_CYAN = "\x1b[36m"
_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"
_RESET = "\x1b[0m"

# Status patterns → color
_STATUS_COLORS = {
    # Kubernetes / OpenShift
    "Running": _GREEN,
    "Succeeded": _GREEN,
    "Completed": _GREEN,
    "Active": _GREEN,
    "Ready": _GREEN,
    "Bound": _GREEN,
    "Available": _GREEN,
    "True": _GREEN,
    "Pending": _YELLOW,
    "Waiting": _YELLOW,
    "ContainerCreating": _YELLOW,
    "Terminating": _YELLOW,
    "Unknown": _YELLOW,
    "False": _RED,
    "CrashLoopBackOff": _RED,
    "Error": _RED,
    "Failed": _RED,
    "ImagePullBackOff": _RED,
    "ErrImagePull": _RED,
    "OOMKilled": _RED,
    "Evicted": _RED,
    # Git
    "modified": _YELLOW,
    "deleted": _RED,
    "new file": _GREEN,
    "renamed": _CYAN,
    # General
    "PASS": _GREEN,
    "PASSED": _GREEN,
    "OK": _GREEN,
    "SUCCESS": _GREEN,
    "FAIL": _RED,
    "FAILED": _RED,
    "ERROR": _RED,
    "WARN": _YELLOW,
    "WARNING": _YELLOW,
    "SKIP": _CYAN,
    "SKIPPED": _CYAN,
    "INFO": _CYAN,
    # Repository / resource visibility
    "public": _GREEN,
    "private": _YELLOW,
    "fork": _CYAN,
    "archived": _DIM,
    # Merge / PR status
    "open": _GREEN,
    "closed": _RED,
    "merged": _CYAN,
    "draft": _YELLOW,
}

_STATUS_RE = re.compile(
    r"\b(" + "|".join(re.escape(s) for s in sorted(_STATUS_COLORS, key=len, reverse=True)) + r")\b"
)

# Active item marker (e.g., "* arewm-tenant" in oc projects)
_ACTIVE_MARKER_RE = re.compile(r"^(\s*)\*\s+(.*)$")

# Error line patterns
_ERROR_LINE_RE = re.compile(r"(?i)^(error|fatal|panic|exception|traceback)\b")

# URL pattern
_URL_RE = re.compile(r"(https?://\S+)")


def colorize(text: str) -> str:
    """Add semantic ANSI color to plain text output."""
    lines = text.splitlines()
    result = []

    for line in lines:
        result.append(_colorize_line(line))

    return "\n".join(result)


def _colorize_line(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return line

    # Active item markers: * prefix → bold green
    m = _ACTIVE_MARKER_RE.match(line)
    if m:
        return f"{m.group(1)}{_BOLD}{_GREEN}* {m.group(2)}{_RESET}"

    # Error lines → red
    if _ERROR_LINE_RE.match(stripped):
        return f"{_RED}{line}{_RESET}"

    # Table header detection: ALL-CAPS words separated by 2+ spaces
    if re.match(r"^[A-Z][A-Z\s/_-]{5,}$", stripped):
        return f"{_BOLD}{line}{_RESET}"

    # Colorize known status words within the line
    colored = _STATUS_RE.sub(_color_status_word, line)
    if colored != line:
        return colored

    # URLs → cyan
    colored = _URL_RE.sub(f"{_CYAN}\\1{_RESET}", line)
    if colored != line:
        return colored

    return line


def _color_status_word(m: re.Match) -> str:
    word = m.group(1)
    color = _STATUS_COLORS.get(word, "")
    if color:
        return f"{color}{word}{_RESET}"
    return word
