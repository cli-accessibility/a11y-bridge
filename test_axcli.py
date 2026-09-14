"""Minimal self-test."""
from axcli.ansi import strip
from axcli.formatter import format_output, _try_parse_table


def test_strip_ansi():
    assert strip("\x1b[31mred\x1b[0m") == "red"
    assert strip("\x1b[1;34mbold blue\x1b[0m") == "bold blue"
    assert strip("plain") == "plain"


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
    assert data[0][1] == "Running"


def test_format_table():
    out = format_output(
        "NAME          STATUS    RESTARTS   AGE\nnginx-abc     Running   0          3d\n",
        "",
        0,
    )
    assert "result: 1 item(s)." in out
    assert "NAME: nginx-abc" in out
    assert "STATUS: Running" in out


def test_format_error():
    out = format_output("", "something failed\n", 1)
    assert "error: something failed" in out


def test_format_plain_lines():
    out = format_output("line one\nline two\n", "", 0)
    assert "result: line one" in out
    assert "result: line two" in out


if __name__ == "__main__":
    test_strip_ansi()
    test_table_parse()
    test_format_table()
    test_format_error()
    test_format_plain_lines()
    print("All tests pass.")
