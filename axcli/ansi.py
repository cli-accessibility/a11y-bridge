"""ANSI escape sequence stripping."""
import re

_ANSI_RE = re.compile(r"\x1b[\[\]()][^\x1b]*?[a-zA-Z\x07]|\x1b\[[0-9;]*m")


def strip(text: str) -> str:
    return _ANSI_RE.sub("", text)
