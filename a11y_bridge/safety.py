"""Safety gate: allowlist of read-only verbs, confirmation for everything else."""

READ_ONLY_VERBS = frozenset({
    "get", "list", "describe", "status", "show", "view", "log", "logs",
    "whoami", "version", "help", "explain", "top", "events", "auth",
    "api-resources", "api-versions", "cluster-info", "config", "completion",
    "projects", "project", "diff", "inspect", "info", "search", "check",
    "pr", "issue", "repo", "run", "release", "gist",  # gh read commands
})

HIGH_SEVERITY_VERBS = frozenset({
    "delete", "rm", "remove", "destroy", "purge", "drop", "drain",
    "cordon", "taint", "reset", "format", "wipe", "nuke", "uninstall",
})


WRITE_VERBS = frozenset({
    "create", "apply", "patch", "edit", "set", "label", "annotate",
    "expose", "scale", "rollout", "run", "cp", "replace", "attach",
    "login", "logout", "new-app", "start-build", "cancel-build",
    "close", "merge", "comment", "review", "approve",
})


def classify(argv: list[str]) -> str:
    """Classify a command as 'safe', 'confirm', or 'dangerous'.

    Returns:
        'safe'      — auto-execute, no confirmation needed
        'confirm'   — ask user before executing
        'dangerous' — warn strongly, require 'yes' not just 'y'
    """
    if not argv:
        return "confirm"

    words = {w.lower().lstrip("-") for w in argv if not w.startswith("-")}

    if words & HIGH_SEVERITY_VERBS:
        return "dangerous"

    # Write verbs override read-only nouns (e.g., "pr create" has both "pr" and "create")
    if words & WRITE_VERBS:
        return "confirm"

    if words & READ_ONLY_VERBS:
        return "safe"

    return "confirm"
