# axcli

Make any CLI tool accessible. Zero config, zero dependencies.

## The Problem

CLI tools like `oc`, `kubectl`, `gh`, and `docker` produce output that is hard to use for people with disabilities:

- **Screen reader users** hear tables as a stream of words with no column association — "NAME READY STATUS nginx one one Running" tells you nothing about which value belongs to which header
- **Low-vision users** get plain monochrome output with no color to distinguish healthy pods from crashing ones
- **Color-blind users** can't tell red errors from green successes when a tool uses color as the only indicator

Most CLI tools don't have built-in accessibility features. Even when they do, they're inconsistent — every tool has different flags, different env vars, different output formats.

## The Solution

axcli wraps any CLI binary and adapts its output to the user's needs:

```bash
axcli oc get pods -n myns
```

That's it. axcli detects who you are and adapts:

**Sighted user** (normal terminal) — adds semantic color:

```
NAME          READY   STATUS             RESTARTS   AGE
nginx-abc     1/1     Running            0          3d      ← green
postgres-xy   0/1     CrashLoopBackOff   5          4d      ← red
```

**Screen reader user** (NO_COLOR set, or screen reader running) — converts tables to labeled sentences:

```
status: Running: oc get pods -n myns
result: 2 item(s).
result: 1. [OK] NAME: nginx-abc. READY: 1/1. STATUS: Running. RESTARTS: 0. AGE: 3d.
result: 2. [ERROR] NAME: postgres-xy. READY: 0/1. STATUS: CrashLoopBackOff. RESTARTS: 5. AGE: 4d.
```

Every value paired with its header. `[OK]` and `[ERROR]` prefixes replace color. `result:` labels serve as screen reader navigation landmarks.

## Install

From PyPI:

```bash
pip install axcli
```

From source:

```bash
git clone https://github.com/cli-accessibility/axcli.git
cd axcli
pip install .
```

Or run without installing:

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
axcli git status
```

axcli detects your context automatically. To force a specific mode:

```bash
# Force screen reader mode
axcli --domain screen-reader oc get pods

# Force it via environment
NO_COLOR=1 axcli oc get pods
AXCLI_SCREEN_READER=1 axcli oc get pods

# Strip ANSI only, no reformatting
axcli --raw kubectl logs my-pod

# Just set NO_COLOR=1 TERM=dumb, don't touch output
axcli --passthrough git diff
```

## How It Works

axcli is a thin wrapper. It does not interpret commands, call APIs, or use AI. Under the hood:

1. Runs your command with `NO_COLOR=1` and `TERM=dumb` to suppress color at source
2. Captures stdout and stderr
3. **Sighted mode:** parses status words (Running, Error, Pending) and adds ANSI color
4. **Screen reader mode:** strips remaining ANSI, converts tables to labeled sentences, interprets color semantics as text prefixes, replaces Unicode symbols with text alternatives, extracts hyperlink URLs
5. Outputs the result with `status:`/`result:`/`error:` labels

Pipe-safe: when stdout is not a terminal, output passes through raw (ANSI-stripped, no labels) so scripts and pipes work normally.

## What Gets Adapted

**For sighted users** — color is added to: status words (Running→green, Error→red, Pending→yellow), active markers (bold green), table headers (bold), URLs (cyan).

**For screen reader users:**
- Tables → labeled sentences (`NAME: nginx. STATUS: Running.`)
- Color → text prefixes (`[OK]`, `[ERROR]`, `[WARN]`)
- Unicode symbols → text (`✓`→`[OK]`, `✗`→`[FAIL]`, `⚠`→`[WARN]`)
- Inverse video → `[SELECTED: text]`
- OSC 8 hyperlinks → `text (link: URL)`
- All output labeled with `result:`/`error:`/`status:`

## Requirements

Python 3.11 or later. No pip dependencies — stdlib only.

## Documentation

- [Configuration and reference](docs/configuration.md) — all options, detection signals, color maps, symbol tables
- [CLI-ACS coverage](docs/cli-acs-coverage.md) — how axcli maps to the CLI-ACS conformance specification
- [Using axcli with oc](docs/oc-accessibility-guide.md) — real-world OpenShift CLI examples with before/after

## License

Apache-2.0
