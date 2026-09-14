"""Interactive AI-powered REPL for accessible CLI interaction."""
import sys
import readline  # enables arrow keys, history in input()

from a11y_bridge.intent import get_intent, summarize_output
from a11y_bridge.safety import classify
from a11y_bridge.executor import run
from a11y_bridge.ansi import strip


def start_repl(binary: str, domains: set[str] | None = None) -> int:
    """Start an interactive AI session wrapping the given binary."""
    from a11y_bridge.intent import _get_provider
    from a11y_bridge.detect import needs_accessible_mode
    provider = _get_provider()

    if domains is None:
        domains = {"color"}
    audio = "audio" in domains
    speaker = None
    earcons = None
    listener = None
    if audio:
        from a11y_bridge.audio import Speaker, Earcons, Listener
        speaker = Speaker()
        earcons = Earcons()
        listener = Listener()
        if not speaker.available:
            print("error: No TTS engine found. Install espeak-ng (Linux) or use macOS say.")
            return 1

    # Determine output formatting mode
    use_screen_reader = "screen-reader" in domains or needs_accessible_mode()

    mode_label = f"using {provider}" + (", audio enabled" if audio else "")
    # Style helpers — no ANSI in screen reader / audio mode
    B = "\x1b[1m" if not use_screen_reader else ""   # bold
    D = "\x1b[2m" if not use_screen_reader else ""   # dim
    R = "\x1b[0m" if not use_screen_reader else ""   # reset
    RE = "\x1b[31m" if not use_screen_reader else ""  # red
    YE = "\x1b[33m" if not use_screen_reader else "" # yellow

    if provider:
        voice_hint = ""
        if listener and listener.available:
            voice_hint = " Type 'v' to use voice input."
        print(f"{B}a11y-bridge{R} {D}— AI session for{R} {B}{binary}{R} {D}({mode_label}){R}")
        if voice_hint:
            print(f"{D}{voice_hint.strip()}{R}")
        if speaker:
            speaker.speak(f"AI session for {binary}. Audio enabled.")
    else:
        print(f"{B}a11y-bridge{R} {D}— AI session for{R} {B}{binary}{R}")
        print(f"{YE}WARNING: No AI provider configured. Set A11Y_AI_KEY and A11Y_AI_PROVIDER.{R}")
    print(f"{D}Type 'quit' to exit, 'help' for options.{R}")
    print()

    context: list[dict] = []
    last_output = ""
    last_suggestions: list[str] = []

    # Styled prompt
    PROMPT = f"{B}you:{R} " if not use_screen_reader else "you: "

    while True:
        try:
            user_input = input(PROMPT).strip()
        except (EOFError, KeyboardInterrupt):
            # Ctrl+C: if speech is playing, stop it instead of exiting
            if speaker and speaker._proc and speaker._proc.poll() is None:
                speaker.stop()
                print(f"\n{D}(speech stopped){R}")
                continue
            print(f"\n{D}Session ended.{R}")
            return 0

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print(f"{D}Session ended.{R}")
            return 0

        if user_input.lower() == "help":
            _print_help(listener is not None and listener.available)
            continue

        if user_input.lower() == "v" and listener and listener.available:
            if earcons:
                earcons.received()
            text = listener.listen()
            if not text:
                print("a11y-bridge: No speech detected. Try again or type your command.")
                continue
            print(f"heard: {text}")
            if speaker:
                speaker.speak(f"I heard: {text}")
            user_input = text

        if user_input.lower() == "repeat":
            if last_output:
                print(last_output)
                if speaker:
                    for line in last_output.splitlines():
                        if line.strip():
                            speaker.enqueue(line)
            else:
                print("a11y-bridge: Nothing to repeat.")
            continue

        # Numbered shortcut: "1", "2", "run 1", "run 2", "try 1"
        shortcut_input = user_input.lower().strip()
        shortcut_num = None
        if shortcut_input.isdigit():
            shortcut_num = int(shortcut_input)
        elif shortcut_input.startswith(("run ", "try ", "do ")) and shortcut_input.split()[-1].isdigit():
            shortcut_num = int(shortcut_input.split()[-1])

        if shortcut_num is not None and last_suggestions:
            idx = shortcut_num - 1
            if 0 <= idx < len(last_suggestions):
                suggestion = last_suggestions[idx]
                # Extract command from suggestion text like "Run 'gh repo view foo'"
                import re
                cmd_match = re.search(r"['\"]([^'\"]+)['\"]", suggestion)
                if cmd_match:
                    user_input = cmd_match.group(1)
                else:
                    # No quoted command — pass the whole suggestion to AI
                    user_input = suggestion
                print(f"{D}→ {user_input}{R}")
            else:
                print(f"a11y-bridge: No suggestion #{shortcut_num}. Valid: 1-{len(last_suggestions)}")
                continue

        # Detect raw command vs natural language
        argv = _try_raw_command(user_input, binary)

        import time as _time
        t0 = _time.monotonic()

        if argv is None:
            print(f"{D}Thinking...{R}")
            intent = get_intent(user_input, binary, context)

            if intent.error:
                print(f"{RE}error: {intent.error}{R}")
                continue

            if not intent.command:
                print(f"a11y-bridge: {intent.explanation or 'Could not determine a command for that request.'}")
                continue

            argv = [binary] + intent.command
            print(f"{D}{intent.explanation}{R}")

        # Safety check
        level = classify(argv)
        cmd_str = " ".join(argv)

        if level == "dangerous":
            print(f"{YE}⚠ HIGH SEVERITY: {cmd_str}{R}")
            print(f"{YE}This may permanently modify or delete resources. Type 'yes' to proceed.{R}")
            try:
                confirm = input(PROMPT).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{D}Cancelled.{R}")
                continue
            if confirm != "yes":
                print(f"{D}Cancelled.{R}")
                continue
        elif level == "confirm":
            print(f"{D}→ {cmd_str}{R}")
            print(f"{D}Proceed? [Y/n]{R}")
            try:
                confirm = input(PROMPT).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{D}Cancelled.{R}")
                continue
            if confirm in ("n", "no"):
                print(f"{D}Cancelled.{R}")
                continue
        else:
            print(f"{D}→ {cmd_str}{R}")

        # Execute
        result = run(argv)
        elapsed = _time.monotonic() - t0

        # Summarize with AI
        stdout_clean = strip(result.stdout)
        stderr_clean = strip(result.stderr)

        if result.exit_code != 0 and stderr_clean:
            print(f"{RE}error: Command failed (exit {result.exit_code}){R}")
            if earcons:
                earcons.error()

        summary = summarize_output(cmd_str, stdout_clean, stderr_clean, result.exit_code)

        # Apply domain-specific formatting
        if use_screen_reader:
            output_text = f"result: {summary.summary}"
            print(output_text)
        else:
            from a11y_bridge.colorize import colorize
            print()
            output_text = colorize(summary.summary)
            print(output_text)

        # Timing
        print(f"{D}({elapsed:.1f}s){R}")

        if speaker:
            if result.exit_code == 0 and earcons:
                earcons.success()
            for line in summary.summary.splitlines():
                line = line.strip()
                if line:
                    speaker.enqueue(line)

        # Suggestions — store for numbered shortcut access
        last_suggestions = summary.next_actions or []
        if last_suggestions:
            actions_text = "You could try: " + ". ".join(last_suggestions)
            if use_screen_reader:
                print("a11y-bridge: You could try:")
                for i, action in enumerate(last_suggestions, 1):
                    print(f"  {i}. {action}")
            else:
                print(f"{D}{'─' * 40}{R}")
                print(f"{D}Next (type the number to run):{R}")
                for i, action in enumerate(last_suggestions, 1):
                    print(f"{D}  {i}. {action}{R}")
            if speaker:
                speaker.enqueue(actions_text)

        last_output = output_text

        # Update context for multi-turn
        context.append({"role": "user", "content": user_input})
        # Truncate stdout for context to save tokens
        ctx_output = stdout_clean[:1000] if len(stdout_clean) > 1000 else stdout_clean
        context.append({
            "role": "assistant",
            "content": f"Ran: {cmd_str}\nExit: {result.exit_code}\nOutput:\n{ctx_output}"
        })

        # Keep context window manageable — last 6 turns (3 exchanges)
        if len(context) > 6:
            context = context[-6:]

        print()


def _try_raw_command(user_input: str, binary: str) -> list[str] | None:
    """Detect if user typed a raw command vs natural language.

    Raw command: starts with the binary name, a known verb, or a flag.
    """
    parts = user_input.split()
    if not parts:
        return None

    first = parts[0].lower()

    # Explicit binary prefix: "gh pr list"
    if first == binary:
        return parts

    # Starts with a flag: "--version", "-n"
    if first.startswith("-"):
        return [binary] + parts

    # Known CLI verbs that are clearly commands, not English
    raw_verbs = {
        "get", "describe", "apply", "create", "delete", "patch", "edit",
        "logs", "exec", "port-forward", "rollout", "scale", "expose",
        "label", "annotate", "set", "auth", "config", "version", "login",
        "logout", "whoami", "project", "projects", "status", "new-app",
        "pr", "issue", "repo", "run", "release", "gist", "api",
        "completion", "help",
    }
    if first in raw_verbs:
        return [binary] + parts

    return None


def _print_help(voice_available: bool = False):
    print("""a11y-bridge AI session commands:

  Type natural language:
    "show me my pull requests"
    "what pods are running in my namespace"
    "delete the build pod"

  Type raw commands:
    get pods -n myns
    pr list --state open
    logs my-pod --tail=50

  Session commands:
    repeat    — repeat the last output
    help      — show this help
    quit      — end the session""")
    if voice_available:
        print("    v         — voice input (speak your command)")
    print()
