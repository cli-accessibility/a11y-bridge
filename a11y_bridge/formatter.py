"""Output formatting: table-to-sentence conversion, labels, progressive disclosure."""
import re


def format_output(stdout: str, stderr: str, exit_code: int,
                  semantics: dict[int, str] | None = None) -> str:
    """Format command output with accessibility labels.

    Args:
        stdout: Clean (ANSI-stripped) stdout text.
        stderr: Clean (ANSI-stripped) stderr text.
        exit_code: Command exit code.
        semantics: Optional {line_number: label} map from color interpretation.
                   Applied to non-table output lines after formatting.
    """
    lines = []

    if exit_code != 0 and stderr:
        for l in stderr.strip().splitlines():
            lines.append(f"error: {l}")
        if stdout.strip():
            lines.append("")
            lines.extend(_format_body(stdout, semantics))
    elif stdout.strip():
        lines.extend(_format_body(stdout, semantics))

    if exit_code != 0 and not stderr:
        lines.append(f"error: command exited with code {exit_code}")

    return "\n".join(lines)


def _format_body(text: str, semantics: dict[int, str] | None = None) -> list[str]:
    rows = text.strip().splitlines()
    if not rows:
        return []

    table = _try_parse_table(rows)
    if table is not None:
        headers, data = table
        lines = [f"result: {len(data)} item(s)."]
        for i, row in enumerate(data, 1):
            # Apply color semantic to the row if available
            # Table data rows start at line index 1 (header is 0)
            sem = semantics.get(i, "") if semantics else ""
            prefix = f"[{sem}] " if sem else ""
            parts = [f"{h}: {v}" for h, v in zip(headers, row) if v.strip()]
            lines.append(f"result: {i}. {prefix}{'. '.join(parts)}.")
        return lines

    result = []
    for i, l in enumerate(rows[:20] if len(rows) > 20 else rows):
        sem = semantics.get(i, "") if semantics else ""
        prefix = f"[{sem}] " if sem else ""
        result.append(f"result: {prefix}{l}")

    if len(rows) > 20:
        return [
            f"result: {len(rows)} lines of output. First 20 shown.",
            *result,
            f"result: ... ({len(rows) - 20} more lines)",
        ]
    return result


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
