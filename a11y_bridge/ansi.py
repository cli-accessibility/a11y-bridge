"""ANSI-aware accessible text conversion.

Instead of just stripping escape sequences, this module interprets them
semantically — extracting meaning from colors and styling before removing
them, then expressing that meaning as text prefixes and markers.

Implements compensations for CLI-ACS CV-1 through CV-15.
"""
import re

# --- Raw stripping patterns ---

_ALL_ESC_RE = re.compile(
    r"\x1b\[[0-9;]*[a-zA-Z]"       # CSI (SGR, cursor, erase)
    r"|\x1b\][^\x07\x1b]*[\x07]"   # OSC terminated by BEL
    r"|\x1b\][^\x07\x1b]*\x1b\\"   # OSC terminated by ST
    r"|\x1b[()][0-9A-B]"           # charset selection
)

# --- CV-13: OSC 8 hyperlink extraction ---

_OSC8_RE = re.compile(
    r"\x1b\]8;([^;]*);([^\x07\x1b]*?)(?:\x07|\x1b\\)"  # opening: params;URI
    r"(.*?)"                                              # visible text
    r"\x1b\]8;;(?:\x07|\x1b\\)",                         # closing
    re.DOTALL,
)

# --- CV-1: Color semantic interpretation ---
# Map SGR foreground color codes to semantic prefixes

_SGR_SEMANTICS = {
    "31": "ERROR",    # red
    "91": "ERROR",    # bright red
    "32": "OK",       # green
    "92": "OK",       # bright green
    "33": "WARN",     # yellow
    "93": "WARN",     # bright yellow
    "36": "INFO",     # cyan
    "96": "INFO",     # bright cyan
    "35": "NOTE",     # magenta
    "95": "NOTE",     # bright magenta
}

# --- CV-15: Unicode symbol replacement ---

_SYMBOL_MAP = {
    "✓": "[OK]",     # ✓ CHECK MARK
    "✔": "[OK]",     # ✔ HEAVY CHECK MARK
    "✅": "[OK]",     # ✅ WHITE HEAVY CHECK MARK
    "✗": "[FAIL]",   # ✗ BALLOT X
    "✘": "[FAIL]",   # ✘ HEAVY BALLOT X
    "❌": "[FAIL]",   # ❌ CROSS MARK
    "●": "[*]",      # ● BLACK CIRCLE
    "○": "[ ]",      # ○ WHITE CIRCLE
    "◉": "[*]",      # ◉ FISHEYE
    "◆": "[*]",      # ◆ BLACK DIAMOND
    "◇": "[ ]",      # ◇ WHITE DIAMOND
    "⬤": "[*]",      # ⬤ BLACK LARGE CIRCLE
    "▶": "->",       # ▶ BLACK RIGHT-POINTING TRIANGLE
    "▷": "->",       # ▷ WHITE RIGHT-POINTING TRIANGLE
    "►": "->",       # ► BLACK RIGHT-POINTING POINTER
    "▸": "->",       # ▸ BLACK RIGHT-POINTING SMALL TRIANGLE
    "→": "->",       # → RIGHTWARDS ARROW
    "←": "<-",       # ← LEFTWARDS ARROW
    "↑": "^",        # ↑ UPWARDS ARROW
    "↓": "v",        # ↓ DOWNWARDS ARROW
    "⚠": "[WARN]",   # ⚠ WARNING SIGN
    "⚡": "[!]",      # ⚡ HIGH VOLTAGE
    "ℹ": "[INFO]",   # ℹ INFORMATION SOURCE
    "ⓘ": "[INFO]",   # ⓘ CIRCLED LATIN SMALL LETTER I
    "\U0001f534": "[FAIL]",   # 🔴 RED CIRCLE
    "\U0001f7e2": "[OK]",     # 🟢 GREEN CIRCLE
    "\U0001f7e1": "[WARN]",   # 🟡 YELLOW CIRCLE
    "⏳": "[WAIT]",       # ⏳ HOURGLASS
    "\U0001f680": "[DEPLOY]", # 🚀 ROCKET
    "\U0001f4e6": "[PKG]",    # 📦 PACKAGE
}

_SYMBOL_RE = re.compile("|".join(re.escape(s) for s in _SYMBOL_MAP))


def accessible(text: str) -> tuple[str, dict[int, str]]:
    """Convert ANSI-colored text to accessible plain text.

    Returns (clean_text, line_semantics) where line_semantics maps
    line numbers to semantic prefixes (e.g., {1: "OK", 2: "WARN"}).
    The caller applies prefixes AFTER table formatting to avoid
    shifting column positions.

    Pipeline:
    1. Extract OSC 8 hyperlink URLs (CV-13)
    2. Convert inverse video to text markers (CV-12)
    3. Detect per-line color semantics (CV-1) — stored separately
    4. Strip all ANSI (CV-2/3/4/5)
    5. Replace Unicode symbols (CV-15)
    """
    text = _extract_hyperlinks(text)
    text = _convert_styling(text)
    semantics = _detect_all_semantics(text)
    text = _ALL_ESC_RE.sub("", text)
    text = _replace_symbols(text)
    return text, semantics


def accessible_simple(text: str) -> str:
    """Convenience wrapper that applies semantics inline.

    Use when table parsing is not needed (e.g., error messages).
    """
    clean, semantics = accessible(text)
    if not semantics:
        return clean
    lines = clean.split("\n")
    for i, sem in semantics.items():
        if i < len(lines) and not _HAS_PREFIX_RE.match(lines[i]):
            lines[i] = f"[{sem}] {lines[i]}"
    return "\n".join(lines)


def strip(text: str) -> str:
    """Plain strip — removes all ANSI without interpretation."""
    return _ALL_ESC_RE.sub("", text)


def _extract_hyperlinks(text: str) -> str:
    """CV-13: Convert OSC 8 hyperlinks to visible text with URL appended."""
    def _repl(m):
        url = m.group(2)
        visible = m.group(3)
        if url and visible.strip():
            return f"{visible} (link: {url})"
        elif url:
            return f"(link: {url})"
        return visible
    return _OSC8_RE.sub(_repl, text)


def _detect_all_semantics(text: str) -> dict[int, str]:
    """CV-1: Detect per-line color semantics from ANSI codes.

    Returns {line_number: semantic_label} for lines where color
    carries meaning. Called before ANSI stripping.
    """
    result = {}
    for i, line in enumerate(text.split("\n")):
        sem = _detect_line_semantic(line)
        if sem:
            result[i] = sem
    return result


_SGR_START_RE = re.compile(r"^(\s*)\x1b\[([0-9;]*)m")
_HAS_PREFIX_RE = re.compile(
    r"(?i)^\s*\[?(error|err|fail|failed|warn|warning|ok|pass|passed|info|note|debug|success)\]?\s*[:>\-]\s"
)


def _detect_line_semantic(line: str) -> str | None:
    """Detect the color semantic of a line without modifying it."""
    m = _SGR_START_RE.search(line)
    if not m:
        return None
    codes = m.group(2).split(";")
    for code in codes:
        if code in _SGR_SEMANTICS:
            return _SGR_SEMANTICS[code]
    return None


def _convert_styling(text: str) -> str:
    """CV-12: Convert bold/underline/inverse to text markers.

    Bold text that serves as a heading (standalone bold line) gets no
    markers — the blank-line separation handles structure. Inline bold
    within a line gets ** markers. Inverse (SGR 7) becomes [SELECTED: ...].
    """
    # Inverse video: \x1b[7m ... \x1b[27m or \x1b[0m
    text = re.sub(
        r"\x1b\[7m(.*?)(?:\x1b\[27m|\x1b\[0m)",
        r"[SELECTED: \1]",
        text,
    )
    return text


def _replace_symbols(text: str) -> str:
    """CV-15: Replace Unicode symbols with text alternatives."""
    return _SYMBOL_RE.sub(lambda m: _SYMBOL_MAP[m.group()], text)
