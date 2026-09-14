# Configuration and Reference

## Options

```
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

## Domain: color (default)

Adaptive behavior — adds color for sighted users, adds text labels for screen reader users. This is the default when no `--domain` is specified.

```bash
axcli oc get pods                       # same as --domain color
axcli --domain color oc get pods        # explicit
```

## Domain: screen-reader

Forces screen reader mode regardless of terminal context. Use when you want text labels and table conversion even in a normal terminal.

```bash
axcli --domain screen-reader oc projects
status: Running: oc projects
result: You have access to the following projects...
result:   * arewm-tenant - arewm
result:     gatekeeper-tenant - gatekeeper
```

## --raw

Strips all ANSI escape sequences but preserves the original output structure. No table conversion, no labels, no color additions.

```bash
axcli --raw kubectl logs my-pod
```

## --passthrough

Runs the command with `NO_COLOR=1` and `TERM=dumb` environment variables set but does not process the output at all.

```bash
axcli --passthrough git diff
```

## Screen Reader Detection

axcli automatically detects screen reader usage:

| Signal | Triggers accessible mode |
|---|---|
| `NO_COLOR` env var set (non-empty) | Yes |
| `TERM=dumb` | Yes |
| `AXCLI_SCREEN_READER=1` env var | Yes |
| `orca` process running (Linux) | Yes |
| `nvda` or `jaws` process running (Windows) | Yes |
| None of the above | No — sighted mode |

To force screen reader mode without setting global env vars:

```bash
AXCLI_SCREEN_READER=1 axcli oc get pods
```

## Pipe Behavior

When stdout is not a terminal (piped or redirected), axcli strips ANSI but passes output through without labels, colors, or reformatting:

```bash
axcli oc get pods              # Adaptive (terminal)
axcli oc get pods | grep nginx  # Raw stripped output (pipe)
axcli oc get pods > pods.txt    # Raw stripped output (file)
```

## Sighted Mode Color Map

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

## Screen Reader Mode Symbol Replacement

| Symbol | Replacement | Symbol | Replacement |
|---|---|---|---|
| ✓ ✔ ✅ | `[OK]` | ✗ ✘ ❌ | `[FAIL]` |
| ● ◉ ◆ ⬤ | `[*]` | ○ ◇ | `[ ]` |
| ⚠ | `[WARN]` | ℹ ⓘ | `[INFO]` |
| ▶ ▷ ► → | `->` | ← | `<-` |
| 🔴 | `[FAIL]` | 🟢 | `[OK]` |
| 🟡 | `[WARN]` | ⏳ | `[WAIT]` |

## Output Labels (Screen Reader Mode)

| Prefix | Meaning |
|---|---|
| `status:` | What axcli is doing (the command being run) |
| `result:` | Successful command output |
| `error:` | Error messages from the wrapped command |
| `[ERROR]` | Injected by color interpretation (was red) |
| `[OK]` | Injected by color interpretation (was green) |
| `[WARN]` | Injected by color interpretation (was yellow) |
| `[SELECTED: ...]` | Text shown in inverse video |
