"""CLI entry point."""
import sys
from axcli.executor import run
from axcli.formatter import format_output


USAGE = """\
axcli — accessible CLI wrapper

Usage: axcli <command> [args...]

Runs any CLI command with accessibility features:
  - Strips ANSI color/escape sequences
  - Converts tables to labeled sentences for screen readers
  - Labels output sections (result:, error:, status:)
  - Forces NO_COLOR=1 and TERM=dumb

Examples:
  axcli oc get pods -n myns
  axcli gh pr list
  axcli kubectl get deployments

Options:
  --help, -h    Show this help
  --version     Show version
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

    # Everything after axcli is the command to run
    # If stdout is not a TTY, pass through raw (pipe-safe)
    if not sys.stdout.isatty():
        result = run(args)
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return result.exit_code

    print(f"status: Running: {' '.join(args)}")

    result = run(args)
    output = format_output(result.stdout, result.stderr, result.exit_code)

    if output:
        print(output)

    return result.exit_code
