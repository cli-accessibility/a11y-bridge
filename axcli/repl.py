"""Interactive AI-powered REPL for accessible CLI interaction."""
import sys
import readline  # enables arrow keys, history in input()

from axcli.intent import get_intent, summarize_output
from axcli.safety import classify
from axcli.executor import run
from axcli.ansi import strip


def start_repl(binary: str, audio: bool = False) -> int:
    """Start an interactive AI session wrapping the given binary."""
    from axcli.intent import _get_provider
    provider = _get_provider()

    speaker = None
    earcons = None
    listener = None
    if audio:
        from axcli.audio import Speaker, Earcons, Listener
        speaker = Speaker()
        earcons = Earcons()
        listener = Listener()
        if not speaker.available:
            print("error: No TTS engine found. Install espeak-ng (Linux) or use macOS say.")
            return 1

    mode_label = f"using {provider}" + (", audio enabled" if audio else "")
    if provider:
        voice_hint = ""
        if listener and listener.available:
            voice_hint = " Type 'v' to use voice input."
        msg = f"axcli: AI session for '{binary}' ({mode_label}).{voice_hint} Type natural language or raw commands."
        print(msg)
        if speaker:
            speaker.speak(f"AI session for {binary}. Audio enabled.")
    else:
        print(f"axcli: AI session for '{binary}'. WARNING: No AI provider configured.")
        print(f"axcli: Set AXCLI_AI_KEY and AXCLI_AI_PROVIDER, or start Ollama.")
    print(f"axcli: Type 'quit' to exit, 'help' for options.")
    print()

    context: list[dict] = []
    last_output = ""

    while True:
        try:
            user_input = input("you: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\naxcli: Session ended.")
            return 0

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("axcli: Session ended.")
            return 0

        if user_input.lower() == "help":
            _print_help(listener is not None and listener.available)
            continue

        if user_input.lower() == "v" and listener and listener.available:
            if earcons:
                earcons.received()
            text = listener.listen()
            if not text:
                print("axcli: No speech detected. Try again or type your command.")
                continue
            print(f"heard: {text}")
            if speaker:
                speaker.speak(f"I heard: {text}")
            user_input = text

        if user_input.lower() == "repeat":
            if last_output:
                print(last_output)
            else:
                print("axcli: Nothing to repeat.")
            continue

        # Detect raw command vs natural language
        # Raw: starts with a known verb/flag or the binary name
        argv = _try_raw_command(user_input, binary)

        if argv is None:
            # Natural language → ask AI
            print("status: Thinking...")
            intent = get_intent(user_input, binary, context)

            if intent.error:
                print(f"error: {intent.error}")
                continue

            if not intent.command:
                print(f"axcli: {intent.explanation or 'Could not determine a command for that request.'}")
                continue

            argv = [binary] + intent.command
            print(f"status: {intent.explanation}")

        # Safety check
        level = classify(argv)
        cmd_str = " ".join(argv)

        if level == "dangerous":
            print(f"warning: HIGH SEVERITY. I will run: {cmd_str}")
            print(f"warning: This may permanently modify or delete resources. Type 'yes' to proceed.")
            try:
                confirm = input("you: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\naxcli: Cancelled.")
                continue
            if confirm != "yes":
                print("axcli: Cancelled.")
                continue
        elif level == "confirm":
            print(f"status: I will run: {cmd_str}")
            print(f"status: Proceed? [Y/n]")
            try:
                confirm = input("you: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\naxcli: Cancelled.")
                continue
            if confirm in ("n", "no"):
                print("axcli: Cancelled.")
                continue
        else:
            print(f"status: Running: {cmd_str}")

        # Execute
        result = run(argv)

        # Summarize with AI
        stdout_clean = strip(result.stdout)
        stderr_clean = strip(result.stderr)

        if result.exit_code != 0 and stderr_clean:
            print(f"error: Command failed (exit {result.exit_code})")
            if earcons:
                earcons.error()

        summary = summarize_output(cmd_str, stdout_clean, stderr_clean, result.exit_code)

        output_text = f"result: {summary.summary}"
        print(output_text)

        if speaker:
            if result.exit_code == 0 and earcons:
                earcons.success()
            # Enqueue line by line — enqueue doesn't interrupt previous lines
            for line in summary.summary.splitlines():
                line = line.strip()
                if line:
                    speaker.enqueue(line)

        if summary.next_actions:
            actions_text = "You could try: " + ". ".join(summary.next_actions)
            print("axcli: You could try:")
            for i, action in enumerate(summary.next_actions, 1):
                print(f"  {i}. {action}")
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
    print("""axcli AI session commands:

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
