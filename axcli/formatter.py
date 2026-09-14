"""Output formatting: table-to-sentence conversion, labels, progressive disclosure."""
import re
from axcli.ansi import strip


def format_output(stdout: str, stderr: str, exit_code: int) -> str:
    stdout = strip(stdout)
    stderr = strip(stderr)
    lines = []

    if exit_code != 0 and stderr:
        for l in stderr.strip().splitlines():
            lines.append(f"error: {l}")
        if stdout.strip():
            lines.append("")
            lines.extend(_format_body(stdout))
    elif stdout.strip():
        lines.extend(_format_body(stdout))

    if exit_code != 0 and not stderr:
        lines.append(f"error: command exited with code {exit_code}")

    return "\n".join(lines)


def _format_body(text: str) -> list[str]:
    rows = text.strip().splitlines()
    if not rows:
        return []

    table = _try_parse_table(rows)
    if table is not None:
        headers, data = table
        lines = [f"result: {len(data)} item(s)."]
        for i, row in enumerate(data, 1):
            parts = [f"{h}: {v}" for h, v in zip(headers, row) if v.strip()]
            lines.append(f"result: {i}. {'. '.join(parts)}.")
        return lines

    if len(rows) <= 20:
        return [f"result: {l}" for l in rows]

    return [
        f"result: {len(rows)} lines of output. First 10 shown.",
        *[f"result: {l}" for l in rows[:10]],
        f"result: ... ({len(rows) - 10} more lines)",
    ]


def _try_parse_table(rows: list[str]) -> tuple[list[str], list[list[str]]] | None:
    """Detect whitespace-aligned tables (like kubectl/oc output)."""
    if len(rows) < 2:
        return None

    header = rows[0]
    # Table heuristic: header has 2+ tokens separated by 2+ spaces
    cols = re.split(r"\s{2,}", header.strip())
    if len(cols) < 2:
        return None

    # Find column start positions from header
    positions = []
    for col in cols:
        pos = header.index(col, positions[-1] + 1 if positions else 0)
        positions.append(pos)

    data = []
    for row in rows[1:]:
        if not row.strip():
            continue
        values = []
        for j, start in enumerate(positions):
            end = positions[j + 1] if j + 1 < len(positions) else len(row)
            val = row[start:end].strip() if start < len(row) else ""
            values.append(val)
        data.append(values)

    if not data:
        return None

    return cols, data
