# axcli

Make any CLI tool screen-reader friendly. Zero config, zero dependencies.

axcli implements all 15 color and visual accessibility criteria from the CLI-ACS specification as runtime compensations — even if the wrapped binary has zero accessibility support, axcli makes its output accessible.

## Install

```bash
pip install .
```

Or run directly without installing:

```bash
python -m axcli oc get pods
```

## Usage

Prefix any command with `axcli`:

```bash
axcli oc get pods -n myns
axcli gh pr list
axcli kubectl get deployments
axcli docker ps
```

## Subcommands

axcli provides different processing modes via subcommands:

```bash
axcli <command> [args...]             # Full accessibility (default)
axcli color <command> [args...]       # Same as default — full CV-1 to CV-15
axcli raw <command> [args...]         # Strip ANSI only, no reformatting
axcli passthrough <command> [args...] # Just set NO_COLOR=1 TERM=dumb, don't touch output
```

### axcli (default) / axcli color

Applies all color and visual accessibility compensations. This is what you want for screen reader use.

```bash
$ axcli oc get pods
status: Running: oc get pods
result: 3 item(s).
result: 1. NAME: nginx-abc. READY: 1/1. STATUS: Running. RESTARTS: 0. AGE: 3d.
result: 2. NAME: postgres-xy. READY: 0/1. STATUS: Pending. RESTARTS: 2. AGE: 1h.
result: 3. NAME: redis-def. READY: 1/1. STATUS: Running. RESTARTS: 0. AGE: 5d.
```

### axcli raw

Strips all ANSI escape sequences but preserves the original output structure. No table conversion, no labels. Useful when you want clean text but don't need reformatting.

```bash
$ axcli raw kubectl logs my-pod
[plain log output with no escape sequences]
```

### axcli passthrough

Runs the command with `NO_COLOR=1` and `TERM=dumb` set but does not process the output. Use when the binary itself handles these signals correctly and you just want to ensure they're set.

```bash
$ axcli passthrough git diff
[git's own plain diff output, no ANSI because TERM=dumb]
```

## What it does

axcli wraps any CLI binary and compensates for all 15 CLI-ACS color and visual accessibility criteria (CV-1 through CV-15):

### Color semantic interpretation (CV-1)

When a binary uses color as the only way to convey meaning (red for errors, green for success), axcli detects the color codes and injects text prefixes:

```
# Binary outputs red text with no text indicator:
$ some-tool status
\x1b[31mconnection refused\x1b[0m

# axcli adds a text prefix based on the color:
$ axcli some-tool status
[ERROR] connection refused
```

Color-to-text mapping:

| Color | Text prefix |
|---|---|
| Red (SGR 31, 91) | `[ERROR]` |
| Green (SGR 32, 92) | `[OK]` |
| Yellow (SGR 33, 93) | `[WARN]` |
| Cyan (SGR 36, 96) | `[INFO]` |
| Magenta (SGR 35, 95) | `[NOTE]` |

If the text already has a prefix like `Error:` or `[FAIL]`, axcli does not double-label it.

### ANSI stripping (CV-2, CV-3, CV-4, CV-5)

All ANSI escape sequences are removed from output — color codes, cursor movement, screen clearing, erase-in-line, and text styling. The wrapped binary also runs with `NO_COLOR=1` and `TERM=dumb` set so well-behaved tools suppress escapes at source.

### Selection highlighting (CV-12)

Inverse video (SGR 7), commonly used for selected items in menus, is converted to a text marker:

```
# Binary shows selection with inverse video:
\x1b[7mcurrent item\x1b[27m

# axcli converts to:
[SELECTED: current item]
```

### Hyperlink extraction (CV-13)

Terminal hyperlinks (OSC 8) are invisible to screen readers. axcli extracts the URL and appends it as visible text:

```
# Binary embeds a clickable link:
\x1b]8;;https://docs.example.com\x07See docs\x1b]8;;\x07

# axcli makes the URL visible:
See docs (link: https://docs.example.com)
```

### Unicode symbol replacement (CV-15)

Unicode symbols and emoji that carry meaning are replaced with text alternatives. Screen readers announce Unicode names ("HEAVY CHECK MARK", "BLACK CIRCLE") which don't convey the intended meaning. axcli replaces them:

| Symbol | Replacement | Symbol | Replacement |
|---|---|---|---|
| ✓ ✔ ✅ | `[OK]` | ✗ ✘ ❌ | `[FAIL]` |
| ● ◉ ◆ ⬤ | `[*]` | ○ ◇ | `[ ]` |
| ⚠ | `[WARN]` | ℹ ⓘ | `[INFO]` |
| ▶ ▷ ► → | `->` | ← | `<-` |
| 🔴 | `[FAIL]` | 🟢 | `[OK]` |
| 🟡 | `[WARN]` | ⏳ | `[WAIT]` |
| 🚀 | `[DEPLOY]` | 📦 | `[PKG]` |

### Table to labeled sentences

Whitespace-aligned tables (like kubectl, oc, docker output) are converted to labeled sentences where each value is paired with its column header:

Before:

```
NAME          READY   STATUS    RESTARTS   AGE
nginx-abc     1/1     Running   0          3d
postgres-xy   0/1     Pending   2          1h
```

After:

```
result: 2 item(s).
result: 1. NAME: nginx-abc. READY: 1/1. STATUS: Running. RESTARTS: 0. AGE: 3d.
result: 2. NAME: postgres-xy. READY: 0/1. STATUS: Pending. RESTARTS: 2. AGE: 1h.
```

## Output labels

All output lines are prefixed with a label that serves as a screen reader navigation landmark:

| Prefix | Meaning |
|---|---|
| `status:` | What axcli is doing (the command being run) |
| `result:` | Successful command output |
| `error:` | Error messages from the wrapped command |
| `[ERROR]` | Text injected by color interpretation (was red) |
| `[OK]` | Text injected by color interpretation (was green) |
| `[WARN]` | Text injected by color interpretation (was yellow) |
| `[SELECTED: ...]` | Text that was shown in inverse video |

## Error handling

```bash
$ axcli oc get pods -n nonexistent
status: Running: oc get pods -n nonexistent
error: Error from server (NotFound): namespaces "nonexistent" not found
```

Errors go to stdout with the `error:` prefix so screen readers encounter them in reading order. The original exit code is preserved.

## Pipes

When stdout is not a terminal, axcli strips ANSI but passes output through without labels or reformatting — pipes and redirects work transparently:

```bash
axcli oc get pods              # Labels and formatting (terminal)
axcli oc get pods | grep nginx  # Raw stripped output (pipe)
axcli oc get pods > pods.txt    # Raw stripped output (file)
```

## Options

```
axcli --help       Show usage
axcli --version    Show version
```

Everything after the subcommand (or after `axcli` if no subcommand) is passed directly to the wrapped command.

## CLI-ACS Coverage

axcli compensates for all 15 criteria in the CLI-ACS Color & Visual Presentation domain:

| Criterion | What the spec requires | How axcli compensates |
|---|---|---|
| CV-1 | Color not sole info channel | Injects text prefixes based on color semantics |
| CV-2 | NO_COLOR support | Forces `NO_COLOR=1` on wrapped binary |
| CV-3 | --no-color flag | Strips all ANSI regardless of binary support |
| CV-4 | TTY-aware color | Captures and strips output in non-TTY mode |
| CV-5 | TERM=dumb respect | Forces `TERM=dumb` on wrapped binary |
| CV-6 | --color flag modes | Stripping makes flag moot |
| CV-7 | FORCE_COLOR support | Stripping makes env var moot |
| CV-8 | 4-bit ANSI preference | Stripping removes all color tiers |
| CV-9 | No background assumption | Stripping removes all color |
| CV-10 | Config precedence | NO_COLOR=1 + TERM=dumb forced at source |
| CV-11 | High contrast support | Plain text — no contrast issues |
| CV-12 | Bold/underline as structure | Converts inverse video to text markers |
| CV-13 | Terminal hyperlinks | Extracts OSC 8 URLs as visible text |
| CV-14 | FG/BG pair contrast | Stripping removes all color pairs |
| CV-15 | Unicode symbol accessibility | Replaces 30+ symbols with text alternatives |

## Requirements

Python 3.11 or later. No pip dependencies — stdlib only.

## License

Apache-2.0
