# axcli

Make any CLI tool accessible. Zero config, zero dependencies.

axcli wraps any command-line binary and adapts its output based on who is using it — adding color for sighted users or adding text labels for screen reader users. It implements all 15 CLI-ACS color and visual accessibility criteria as runtime compensations.

## Install

```bash
pip install .
```

Or run directly without installing:

```bash
python -m axcli oc get pods
```

## Quick Start

```bash
axcli oc get pods -n myns
axcli gh pr list
axcli kubectl get deployments
axcli docker ps
```

axcli detects your context automatically:

- **Sighted user** (terminal, no screen reader) → adds semantic color to plain output
- **Screen reader user** (NO_COLOR set, TERM=dumb, or screen reader running) → strips color, adds text labels, converts tables

## Adaptive Behavior

### Sighted Mode

When running in a normal terminal, axcli adds color to make plain output easier to scan:

```bash
$ axcli oc get pods
status: Running: oc get pods
NAME          READY   STATUS             RESTARTS   AGE
nginx-abc     1/1     Running            0          3d      ← green
redis-def     0/1     Pending            2          1h      ← yellow
postgres-xy   0/1     CrashLoopBackOff   5          4d      ← red
```

What gets colored:

| Pattern | Color |
|---|---|
| Running, Succeeded, Active, Ready, True, PASS, OK | Green |
| Pending, Waiting, ContainerCreating, WARN | Yellow |
| CrashLoopBackOff, Error, Failed, OOMKilled, FAIL | Red |
| modified (git) | Yellow |
| deleted (git) | Red |
| new file (git) | Green |
| Active project marker (`*`) | Bold green |
| Table headers (ALL CAPS) | Bold |
| URLs | Cyan |

### Screen Reader Mode

When `NO_COLOR` is set, `TERM=dumb`, or a screen reader (orca, nvda, jaws) is detected, axcli switches to text-only accessibility:

```bash
$ NO_COLOR=1 axcli oc get pods
status: Running: oc get pods
result: 3 item(s).
result: 1. [OK] NAME: nginx-abc. READY: 1/1. STATUS: Running. RESTARTS: 0. AGE: 3d.
result: 2. [WARN] NAME: redis-def. READY: 0/1. STATUS: Pending. RESTARTS: 2. AGE: 1h.
result: 3. [ERROR] NAME: postgres-xy. READY: 0/1. STATUS: CrashLoopBackOff. RESTARTS: 5. AGE: 4d.
```

What it does:

- Strips all ANSI escape sequences
- Converts tables to labeled sentences (each value paired with its header)
- Adds `[OK]`/`[WARN]`/`[ERROR]` prefixes based on color semantics
- Extracts OSC 8 hyperlink URLs as visible text
- Replaces Unicode symbols with text alternatives (✓→`[OK]`, ✗→`[FAIL]`, ⚠→`[WARN]`)
- Converts inverse video to `[SELECTED: text]`
- Labels all output with `result:`/`error:`/`status:` prefixes

## Options

```bash
axcli [options] <command> [args...]

Options:
  --domain color          Color & visual accessibility (default, adaptive)
  --domain screen-reader  Force screen reader mode regardless of context
  --domain audio          Text-to-speech output (future)
  --raw                   Strip ANSI only, no reformatting
  --passthrough           Just set NO_COLOR=1 TERM=dumb, no processing
  --help, -h              Show help
  --version               Show version
```

### --domain color (default)

Adaptive behavior — adds color for sighted users, adds text labels for screen reader users. This is the default when no `--domain` is specified.

```bash
axcli oc get pods                       # same as --domain color
axcli --domain color oc get pods        # explicit
```

### --domain screen-reader

Forces screen reader mode regardless of terminal context. Use when you want text labels and table conversion even in a normal terminal.

```bash
axcli --domain screen-reader oc projects
status: Running: oc projects
result: You have access to the following projects...
result:   * arewm-tenant - arewm
result:     gatekeeper-tenant - gatekeeper
```

### --raw

Strips all ANSI escape sequences but preserves the original output structure. No table conversion, no labels, no color additions.

```bash
axcli --raw kubectl logs my-pod
```

### --passthrough

Runs the command with `NO_COLOR=1` and `TERM=dumb` environment variables set but does not process the output at all. Use when the binary itself handles these signals correctly.

```bash
axcli --passthrough git diff
```

## Screen Reader Detection

axcli automatically detects screen reader usage via:

| Signal | Triggers accessible mode |
|---|---|
| `NO_COLOR` env var set (non-empty) | Yes |
| `TERM=dumb` | Yes |
| `AXCLI_SCREEN_READER=1` env var | Yes |
| `orca` process running (Linux) | Yes |
| `nvda` or `jaws` process running | Yes |
| None of the above | No — sighted mode (add color) |

To force screen reader mode without setting global env vars:

```bash
AXCLI_SCREEN_READER=1 axcli oc get pods
```

## Pipes

When stdout is not a terminal (piped or redirected), axcli strips ANSI but passes output through without labels, colors, or reformatting:

```bash
axcli oc get pods              # Adaptive (terminal)
axcli oc get pods | grep nginx  # Raw stripped output (pipe)
axcli oc get pods > pods.txt    # Raw stripped output (file)
```

## CLI-ACS Coverage

axcli compensates for all 15 criteria in the CLI-ACS Color & Visual Presentation domain:

| Criterion | Sighted mode | Screen reader mode |
|---|---|---|
| CV-1: Color not sole info | Adds color to status words | Adds text prefixes `[OK]`/`[ERROR]`/`[WARN]` |
| CV-2: NO_COLOR | N/A (adds color) | Detects and enables text mode |
| CV-3: --no-color | N/A (adds color) | Strips all ANSI |
| CV-4: TTY-aware | Detects TTY for mode | Strips when piped |
| CV-5: TERM=dumb | N/A (adds color) | Detects and enables text mode |
| CV-6-10: Color config | Handles at source | Strips everything |
| CV-11: High contrast | N/A | Plain text — no contrast issues |
| CV-12: Inverse video | Preserves | Converts to `[SELECTED: text]` |
| CV-13: OSC 8 hyperlinks | Preserves | Extracts URL as text |
| CV-14: FG/BG contrast | Adds safe colors | Strips all color |
| CV-15: Unicode symbols | Preserves | Replaces with text alternatives |

### Symbol Replacement (Screen Reader Mode)

| Symbol | Replacement | Symbol | Replacement |
|---|---|---|---|
| ✓ ✔ ✅ | `[OK]` | ✗ ✘ ❌ | `[FAIL]` |
| ● ◉ ◆ ⬤ | `[*]` | ○ ◇ | `[ ]` |
| ⚠ | `[WARN]` | ℹ ⓘ | `[INFO]` |
| ▶ ▷ ► → | `->` | ← | `<-` |
| 🔴 | `[FAIL]` | 🟢 | `[OK]` |
| 🟡 | `[WARN]` | ⏳ | `[WAIT]` |

## Requirements

Python 3.11 or later. No pip dependencies — stdlib only.

## License

Apache-2.0
