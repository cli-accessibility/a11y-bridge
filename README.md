# axcli

Make any CLI tool screen-reader friendly. Zero config, zero dependencies.

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

## What it does

axcli wraps any CLI binary and applies three accessibility compensations:

1. Forces `NO_COLOR=1` and `TERM=dumb` so the wrapped tool suppresses color and escape sequences at source
2. Strips any remaining ANSI escape sequences from the output
3. Converts whitespace-aligned tables into labeled sentences that screen readers can read linearly

### Before (raw oc output)

```
NAME          READY   STATUS    RESTARTS   AGE
nginx-abc     1/1     Running   0          3d
postgres-xy   0/1     Pending   2          1h
```

A screen reader reads this as a stream of words with no column association — the user cannot tell which value belongs to which header.

### After (axcli output)

```
status: Running: oc get pods
result: 2 item(s).
result: 1. NAME: nginx-abc. READY: 1/1. STATUS: Running. RESTARTS: 0. AGE: 3d.
result: 2. NAME: postgres-xy. READY: 0/1. STATUS: Pending. RESTARTS: 2. AGE: 1h.
```

Every value is paired with its column header. The `result:` and `status:` prefixes serve as landmarks for screen reader navigation.

## Output labels

All output lines are prefixed with a label:

| Prefix | Meaning |
|---|---|
| `status:` | What axcli is doing (e.g., which command it is running) |
| `result:` | Successful command output |
| `error:` | Error messages from the wrapped command |

## Error handling

```bash
$ axcli oc get pods -n nonexistent
status: Running: oc get pods -n nonexistent
error: Error from server (NotFound): namespaces "nonexistent" not found
```

Errors go to stdout with the `error:` prefix so screen readers encounter them in reading order. The original exit code is preserved — scripts that check `$?` work as expected.

## Pipes

When stdout is not a terminal (piped or redirected), axcli passes raw output through without labels or formatting:

```bash
# Labels and formatting applied (stdout is a terminal)
axcli oc get pods

# Raw output, no labels (stdout is a pipe)
axcli oc get pods | grep nginx

# Raw output (stdout is a file)
axcli oc get pods > pods.txt
```

## Options

```
axcli --help       Show usage
axcli --version    Show version
```

Everything else is passed directly to the wrapped command.

## Requirements

Python 3.11 or later. No pip dependencies — stdlib only.

## How it works

axcli is a thin wrapper. It does not interpret commands, call APIs, or use AI. It runs the exact command you give it, captures stdout and stderr, strips escape sequences, detects table-formatted output, and reformats it with labels.

The accessibility compensations map to the CLI-ACS conformance criteria:

| Compensation | CLI-ACS criterion |
|---|---|
| Forces `NO_COLOR=1` | CV-2: NO_COLOR Support |
| Forces `TERM=dumb` | CV-5: TERM=dumb Respect |
| Strips ANSI sequences | CV-4: TTY-Aware Color |
| Labels output sections | OS-4: Linear Reading Order |
| Table to sentences | OS-5: No ASCII Art as Sole Information |

## License

Apache-2.0
