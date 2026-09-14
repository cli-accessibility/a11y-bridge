"""CLI entry point with subcommands for domain-specific accessibility."""
import sys
from axcli.executor import run
from axcli.formatter import format_output
from axcli.ansi import accessible, strip


USAGE = """\
axcli -- accessible CLI wrapper

Usage:
  axcli <command> [args...]             Apply all accessibility compensations
  axcli color <command> [args...]       Apply color & visual compensations (CV-1 to CV-15)
  axcli raw <command> [args...]         Strip ANSI only, no reformatting
  axcli passthrough <command> [args...] Run with NO_COLOR=1 TERM=dumb, no processing

Options:
  --help, -h    Show this help
  --version     Show version

Subcommands:
  color         Full color & visual accessibility: interprets color semantics
                as text prefixes, extracts hyperlink URLs, converts bold/underline
                to markers, replaces Unicode symbols with text alternatives,
                and reformats tables as labeled sentences.

  raw           Strips ANSI escape sequences but preserves original output
                structure. No table conversion, no labels.

  passthrough   Runs the command with NO_COLOR=1 and TERM=dumb but does not
                touch the output. Use when the binary itself handles these
                signals correctly.

Examples:
  axcli oc get pods -n myns
  axcli color gh pr list
  axcli raw kubectl logs my-pod
  axcli passthrough git diff
"""


def main() -> int:
    args = sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        print(USAGE.strip())
        return 0

    if args[0] == "--version":
        from axcli import __version__
        print(f"axcli {__version__}")
        return 0

    # Determine mode from first arg
    mode = "full"
    cmd_args = args

    if args[0] in ("color", "raw", "passthrough") and len(args) > 1:
        mode = args[0]
        cmd_args = args[1:]

    if not cmd_args:
        print(USAGE.strip())
        return 0

    # Pipe-safe: raw passthrough when stdout is not a TTY
    if not sys.stdout.isatty():
        result = run(cmd_args)
        sys.stdout.write(strip(result.stdout) if mode != "passthrough" else result.stdout)
        sys.stderr.write(result.stderr)
        return result.exit_code

    if mode == "passthrough":
        print(f"status: Running: {' '.join(cmd_args)}")
        result = run(cmd_args)
        sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)
        return result.exit_code

    print(f"status: Running: {' '.join(cmd_args)}")
    result = run(cmd_args)

    if mode == "raw":
        # Strip ANSI but no reformatting
        out = strip(result.stdout)
        if out.strip():
            print(out, end="" if out.endswith("\n") else "\n")
        if result.stderr:
            err = strip(result.stderr)
            for line in err.strip().splitlines():
                print(f"error: {line}")
        if result.exit_code != 0 and not result.stderr:
            print(f"error: command exited with code {result.exit_code}")
        return result.exit_code

    # Full mode or color mode — interpret colors semantically, then format
    a11y_stdout, stdout_sem = accessible(result.stdout)
    a11y_stderr, _ = accessible(result.stderr)
    output = format_output(a11y_stdout, a11y_stderr, result.exit_code, stdout_sem)

    if output:
        print(output)

    return result.exit_code
