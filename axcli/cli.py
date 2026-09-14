"""CLI entry point — adaptive accessibility based on user context."""
import sys
from axcli.executor import run
from axcli.formatter import format_output
from axcli.ansi import accessible, strip
from axcli.colorize import colorize
from axcli.detect import needs_accessible_mode


USAGE = """\
axcli -- accessible CLI wrapper

Usage:
  axcli [options] <command> [args...]

Adaptive behavior:
  Sighted user (TTY, no screen reader) → adds color to plain output
  Screen reader user (NO_COLOR, TERM=dumb) → strips color, adds text labels

Options:
  --domain color        Apply color & visual accessibility (default)
  --domain screen-reader  Force screen reader mode (labels, tables, symbols)
  --domain audio        Speak output via text-to-speech (espeak-ng/say)
  --askai               Start an AI-powered interactive session
  --raw                 Strip ANSI only, no reformatting
  --passthrough         Just set NO_COLOR=1 TERM=dumb, no processing
  --help, -h            Show this help
  --version             Show version

Examples:
  axcli oc get pods -n myns
  axcli --domain color gh pr list
  axcli --domain screen-reader oc projects
  axcli --askai gh                          # AI interactive session
  axcli --raw kubectl logs my-pod
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

    # Parse axcli's own flags
    domain = "color"
    mode = "adaptive"
    askai = False
    cmd_start = 0

    i = 0
    while i < len(args):
        if args[i] == "--domain" and i + 1 < len(args):
            domain = args[i + 1]
            i += 2
            cmd_start = i
        elif args[i] == "--askai":
            askai = True
            i += 1
            cmd_start = i
        elif args[i] == "--raw":
            mode = "raw"
            i += 1
            cmd_start = i
        elif args[i] == "--passthrough":
            mode = "passthrough"
            i += 1
            cmd_start = i
        elif args[i].startswith("--"):
            # Unknown flag — might be for the wrapped command
            break
        else:
            break

    cmd_args = args[cmd_start:]
    if not cmd_args:
        print(USAGE.strip())
        return 0

    # --askai mode: interactive AI session
    if askai:
        binary = cmd_args[0]
        from axcli.repl import start_repl
        return start_repl(binary, audio=(domain == "audio"))

    # Pipe-safe: raw output when stdout is not a TTY
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
        out = strip(result.stdout)
        if out.strip():
            print(out, end="" if out.endswith("\n") else "\n")
        if result.stderr:
            for line in strip(result.stderr).strip().splitlines():
                print(f"error: {line}")
        if result.exit_code != 0 and not result.stderr:
            print(f"error: command exited with code {result.exit_code}")
        return result.exit_code

    # Adaptive mode: detect context and apply appropriate enhancement
    if domain == "screen-reader" or needs_accessible_mode():
        # Screen reader mode: strip color, add text labels, convert tables
        a11y_stdout, stdout_sem = accessible(result.stdout)
        a11y_stderr, _ = accessible(result.stderr)
        output = format_output(a11y_stdout, a11y_stderr, result.exit_code, stdout_sem)
    elif domain == "audio":
        # Audio mode: screen reader formatting + TTS
        from axcli.audio import Speaker, Earcons
        speaker = Speaker()
        earcons = Earcons()
        if not speaker.available:
            print("error: No TTS engine found. Install espeak-ng (Linux) or use macOS say.")
            return 1
        a11y_stdout, stdout_sem = accessible(result.stdout)
        a11y_stderr, _ = accessible(result.stderr)
        output = format_output(a11y_stdout, a11y_stderr, result.exit_code, stdout_sem)
        if output:
            print(output)
            if result.exit_code != 0:
                earcons.error()
            else:
                earcons.success()
            for line in output.splitlines():
                if line.strip():
                    speaker.enqueue(line)
        # Wait for speech to finish
        import time
        while not speaker._queue.empty() or (speaker._proc and speaker._proc.poll() is None):
            time.sleep(0.1)
        speaker.shutdown()
        return result.exit_code
    else:
        # Sighted mode: add color to plain output
        stdout = strip(result.stdout)
        stderr = strip(result.stderr)
        colored_stdout = colorize(stdout)
        if result.exit_code != 0 and stderr:
            for line in stderr.strip().splitlines():
                print(f"\x1b[31merror: {line}\x1b[0m")
            if colored_stdout.strip():
                print()
                print(colored_stdout, end="" if colored_stdout.endswith("\n") else "\n")
        elif colored_stdout.strip():
            print(colored_stdout, end="" if colored_stdout.endswith("\n") else "\n")
        if result.exit_code != 0 and not stderr:
            print(f"\x1b[31merror: command exited with code {result.exit_code}\x1b[0m")
        return result.exit_code

    if output:
        print(output)
    return result.exit_code
