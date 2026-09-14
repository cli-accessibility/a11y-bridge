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

The core package has zero dependencies. Install only the domains you need:

```bash
# Core only — color, screen reader, table formatting (zero deps)
pip install axcli

# With audio — TTS (Piper natural voice) + STT (Vosk voice input)
pip install axcli[audio]

# Everything
pip install axcli[all]
```

The AI mode (`--askai`) needs an API key but no extra pip packages — it uses stdlib urllib.

From source:

```bash
git clone https://github.com/cli-accessibility/axcli.git
cd axcli
pip install .              # core only
pip install .[audio]       # with audio
pip install .[all]         # everything
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

## AI-Powered Interactive Mode

Start a conversational session where you describe what you want in plain language:

```bash
axcli --askai gh
```

```
axcli: AI session for 'gh'. Type natural language or raw commands.

you: show me my open pull requests
status: List open pull requests
status: Running: gh pr list
result: 3 open pull requests. #123 "Fix login bug" updated yesterday,
        #456 "Add dark mode" updated 3 days ago, #789 "Refactor auth"
        updated last week.
axcli: You could try:
  1. View details of a specific PR
  2. Check CI status of a PR

you: close the second one
status: I will run: gh pr close 456
status: Proceed? [Y/n]
you: y
result: Pull request #456 closed.

you: quit
```

The AI converts your natural language to CLI commands, executes them safely, and summarizes the output in accessible text. Multi-turn context is preserved — "the second one" resolves against the previous result.

You can also type raw commands directly:

```
you: pr list --state closed
status: Running: gh pr list --state closed
result: 5 closed pull requests...
```

### Setup

Set your AI provider via environment variables:

```bash
# Option 1: Generic key (recommended)
export AXCLI_AI_KEY=your-api-key-here
export AXCLI_AI_PROVIDER=anthropic    # or: openai, ollama

# Option 2: Provider-specific keys (also works)
export ANTHROPIC_API_KEY=your-key     # for Claude
export OPENAI_API_KEY=your-key        # for OpenAI/compatible

# Option 3: Local Ollama (no key needed)
# Just start Ollama: ollama serve
# axcli auto-detects it on localhost:11434
```

Optional settings:

```bash
export AXCLI_AI_URL=http://localhost:11434   # custom API endpoint
export AXCLI_MODEL=claude-sonnet-4-6            # specific model name
```

### Safety

Commands are classified by safety level:

| Level | What happens | Examples |
|---|---|---|
| **Safe** | Auto-executes, no confirmation | `get`, `list`, `describe`, `logs`, `status`, `whoami` |
| **Confirm** | Asks "Proceed? [Y/n]" | `create`, `apply`, `merge`, `close`, `scale` |
| **Dangerous** | Requires typing "yes" | `delete`, `drain`, `destroy`, `purge`, `drop` |

The AI generates commands but never classifies their safety — that's done by the allowlist. The full command is always shown before execution.

## Audio Mode

Speak results aloud and use voice input — fully offline using Piper (natural voice) or espeak-ng:

```bash
# Command output spoken aloud
axcli --domain audio gh pr list

# AI session with voice — results spoken, type 'v' to speak input
axcli --domain audio --askai gh
```

```
axcli: AI session for 'gh' (using anthropic, audio enabled). Type 'v' to use voice input.

you: list all my repos
(each repo spoken one by one in a natural voice)

you: v
axcli: Listening... (speak now, press Ctrl+C to stop)
heard: show my pull requests
status: Running: gh pr list
(results spoken aloud)

you: quit
```

### Audio setup

TTS works out of the box if espeak-ng is installed (most Linux systems). For natural-sounding voice:

```bash
# Install Piper neural TTS (optional, recommended)
pip install piper-tts

# Download a voice model (~60MB, one-time)
mkdir -p ~/.cache/axcli/piper
cd ~/.cache/axcli/piper
curl -sL https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx -o en_US-lessac-medium.onnx
curl -sL https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json -o en_US-lessac-medium.onnx.json
```

For voice input:

```bash
# Install Vosk STT (optional)
pip install vosk

# Download speech model (~50MB, one-time)
mkdir -p ~/.cache/axcli
cd ~/.cache/axcli
curl -sL https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip -o model.zip
unzip -q model.zip && mv vosk-model-small-en-us-0.15 vosk-model && rm model.zip
```

### Audio settings

```bash
export AXCLI_TTS_RATE=170            # Words per minute (default 170)
export AXCLI_TTS_ENGINE=espeak-ng    # Force engine: piper, espeak-ng, say, none
```

Engine priority: Piper (natural) > espeak-ng (robotic, fast) > say (macOS).

## How It Works

In **wrapper mode** (default), axcli is a thin wrapper that does not use AI. Under the hood:

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

Python 3.11 or later.

| Install | What you get | Dependencies |
|---|---|---|
| `pip install axcli` | Color, screen reader mode, table formatting | None (stdlib only) |
| `pip install axcli[audio]` | + TTS (Piper natural voice) + STT (Vosk voice input) | piper-tts, vosk |
| `pip install axcli[all]` | Everything above | piper-tts, vosk |
| `--askai` flag | + AI interactive mode (natural language → commands) | None (set `AXCLI_AI_KEY`) |

Audio also needs system packages: `espeak-ng` (Linux, usually pre-installed) or Piper voice model (~60MB, one-time download).

## Documentation

- [Configuration and reference](docs/configuration.md) — all options, AI setup, environment variables, safety levels, color maps, symbol tables
- [CLI-ACS coverage](docs/cli-acs-coverage.md) — how axcli maps to the CLI-ACS conformance specification
- [Using axcli with oc](docs/oc-accessibility-guide.md) — real-world OpenShift CLI examples with before/after

## License

Apache-2.0
