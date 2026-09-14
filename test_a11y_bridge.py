"""Tests for a11y-bridge accessible CLI wrapper."""
from a11y_bridge.ansi import accessible, strip, _replace_symbols, _extract_hyperlinks, _detect_line_semantic
from a11y_bridge.formatter import format_output, _try_parse_table


# --- CV-2/4/5: ANSI stripping ---

def test_strip_ansi():
    assert strip("\x1b[31mred\x1b[0m") == "red"
    assert strip("\x1b[1;34mbold blue\x1b[0m") == "bold blue"
    assert strip("plain") == "plain"

def test_strip_osc():
    assert strip("\x1b]8;;https://example.com\x07text\x1b]8;;\x07") == "text"

def test_strip_csi_cursor():
    assert strip("\x1b[2J\x1b[H\x1b[Khello") == "hello"


# --- CV-1: Color semantic interpretation ---

def test_color_red_detected():
    line = "\x1b[31mfailed to connect\x1b[0m"
    clean, sem = accessible(line)
    assert "failed to connect" in clean
    assert 0 in sem and sem[0] == "ERROR"

def test_color_green_detected():
    line = "\x1b[32mdeployment successful\x1b[0m"
    clean, sem = accessible(line)
    assert 0 in sem and sem[0] == "OK"

def test_color_yellow_detected():
    line = "\x1b[33mdeprecated flag\x1b[0m"
    clean, sem = accessible(line)
    assert 0 in sem and sem[0] == "WARN"

def test_color_no_double_label():
    line = "\x1b[31mError: connection refused\x1b[0m"
    clean, sem = accessible(line)
    assert 0 in sem  # semantic detected, but formatter skips lines with existing prefix


# --- CV-12: Bold/underline to text markers ---

def test_inverse_to_selected():
    line = "\x1b[7mchosen item\x1b[27m"
    clean, _ = accessible(line)
    assert "[SELECTED: chosen item]" in clean


# --- CV-13: OSC 8 hyperlink extraction ---

def test_hyperlink_extraction():
    text = "\x1b]8;;https://docs.example.com\x07See docs\x1b]8;;\x07"
    clean, _ = accessible(text)
    assert "See docs" in clean
    assert "(link: https://docs.example.com)" in clean

def test_hyperlink_no_url():
    text = "plain text no links"
    clean, _ = accessible(text)
    assert clean == "plain text no links"


# --- CV-15: Unicode symbol replacement ---

def test_symbol_checkmark():
    assert _replace_symbols("✓ passed") == "[OK] passed"
    assert _replace_symbols("✗ failed") == "[FAIL] failed"

def test_symbol_circles():
    assert _replace_symbols("● active") == "[*] active"
    assert _replace_symbols("○ inactive") == "[ ] inactive"

def test_symbol_arrows():
    assert _replace_symbols("▶ running") == "-> running"

def test_symbol_warning():
    assert _replace_symbols("⚠ caution") == "[WARN] caution"

def test_symbol_emoji():
    assert _replace_symbols("\U0001f534 down") == "[FAIL] down"
    assert _replace_symbols("\U0001f7e2 up") == "[OK] up"

def test_no_symbols():
    assert _replace_symbols("plain text") == "plain text"


# --- Table formatting ---

def test_table_parse():
    rows = [
        "NAME          STATUS    RESTARTS   AGE",
        "nginx-abc     Running   0          3d",
        "postgres-xy   Pending   2          1h",
    ]
    result = _try_parse_table(rows)
    assert result is not None
    headers, data = result
    assert headers == ["NAME", "STATUS", "RESTARTS", "AGE"]
    assert len(data) == 2
    assert data[0][0] == "nginx-abc"

def test_format_table():
    out = format_output(
        "NAME          STATUS    RESTARTS   AGE\nnginx-abc     Running   0          3d\n",
        "", 0,
    )
    assert "result: 1 item(s)." in out
    assert "NAME: nginx-abc" in out

def test_format_error():
    out = format_output("", "something failed\n", 1)
    assert "error: something failed" in out

def test_format_plain_lines():
    out = format_output("line one\nline two\n", "", 0)
    assert "result: line one" in out


# --- Integration: full pipeline ---

def test_full_pipeline_colored_table():
    """Simulates colored kubectl/oc output going through the full pipeline."""
    raw = (
        "\x1b[1mNAME          STATUS    RESTARTS   AGE\x1b[0m\n"
        "\x1b[32mnginx-abc     Running   0          3d\x1b[0m\n"
        "\x1b[33mredis-def     Pending   2          1h\x1b[0m\n"
    )
    clean, sem = accessible(raw)
    out = format_output(clean, "", 0, sem)
    assert "result: 2 item(s)." in out
    assert "NAME: nginx-abc" in out
    # Color semantics applied at row level, not shifting columns
    assert "[OK]" in out   # green row
    assert "[WARN]" in out  # yellow row

def test_full_pipeline_error_with_color():
    from a11y_bridge.ansi import accessible_simple
    raw = "\x1b[31mfatal: remote origin already exists.\x1b[0m\n"
    a11y = accessible_simple(raw)
    out = format_output("", a11y, 1)
    assert "[ERROR]" in out
    assert "fatal: remote origin already exists." in out


if __name__ == "__main__":
    import sys
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS: {t.__name__}")
        except AssertionError as e:
            print(f"  FAIL: {t.__name__}: {e}")
            failed += 1
    print(f"\n{len(tests)} tests, {failed} failed.")
    sys.exit(1 if failed else 0)
