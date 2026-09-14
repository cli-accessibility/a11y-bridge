# Configuration and Reference

## Options

```
axcli [options] <command> [args...]

Options:
  --domain color          Color & visual accessibility (default, adaptive)
  --domain screen-reader  Force screen reader mode regardless of context
  --domain audio          Speak output via TTS, voice input with 'v' key
  --askai                 Start an AI-powered interactive session
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

## Domain: audio

Speaks command output using text-to-speech. In `--askai` mode, also supports voice input via the `v` key.

```bash
# Speak output of any command
axcli --domain audio oc get pods

# AI session with voice output and input
axcli --domain audio --askai gh
```

In the AI session, type `v` then speak your command. Press Ctrl+C to stop recording.

### Audio Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AXCLI_TTS_ENGINE` | auto-detect | Force TTS engine: `piper`, `espeak-ng`, `say`, `none` |
| `AXCLI_TTS_RATE` | `170` | Speech rate in words per minute |
| `AXCLI_PIPER_MODEL` | `~/.cache/axcli/piper/en_US-lessac-medium.onnx` | Path to Piper voice model |

### TTS Engine Priority

| Engine | Quality | Latency | Install |
|---|---|---|---|
| Piper | Natural (neural) | ~3s/sentence | `pip install piper-tts` + voice model |
| espeak-ng | Robotic (formant) | ~50ms | System package (usually pre-installed) |
| say | System voice | ~100ms | macOS built-in |

### Voice Input (STT) Setup

```bash
pip install vosk
mkdir -p ~/.cache/axcli
cd ~/.cache/axcli
curl -sL https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip -o model.zip
unzip -q model.zip && mv vosk-model-small-en-us-0.15 vosk-model && rm model.zip
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

## AI Mode (--askai)

Start an interactive session where natural language is converted to CLI commands:

```bash
axcli --askai gh
axcli --askai oc
axcli --askai kubectl
```

### AI Environment Variables

| Variable | Required | Description |
|---|---|---|
| `AXCLI_AI_KEY` | Yes (unless Ollama) | API key for the AI provider |
| `AXCLI_AI_PROVIDER` | No | Explicit provider: `anthropic`, `openai`, `ollama`. Auto-detected if not set. |
| `AXCLI_AI_URL` | No | Custom API endpoint (default: provider's standard URL, or `http://localhost:11434` for Ollama) |
| `AXCLI_MODEL` | No | Model name override (default: `claude-sonnet-4-6` for Anthropic, `gpt-4o-mini` for OpenAI, `qwen2.5-coder:7b-instruct` for Ollama) |

Provider-specific keys are also supported as fallbacks:

| Variable | Provider |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic (Claude) |
| `OPENAI_API_KEY` | OpenAI / compatible APIs |

### Provider Detection Priority

1. `AXCLI_AI_PROVIDER` env var (explicit)
2. `AXCLI_AI_KEY` + `AXCLI_AI_URL` (provider inferred from URL)
3. `ANTHROPIC_API_KEY` (Anthropic)
4. `OPENAI_API_KEY` (OpenAI)
5. Ollama running on localhost:11434 (auto-detected, no key needed)

### Setup Examples

```bash
# Claude (Anthropic)
export AXCLI_AI_KEY=sk-ant-...
export AXCLI_AI_PROVIDER=anthropic

# OpenAI
export AXCLI_AI_KEY=sk-...
export AXCLI_AI_PROVIDER=openai

# Local Ollama (no key, no provider — auto-detected)
ollama serve &
ollama pull qwen2.5-coder:7b-instruct

# Azure OpenAI or other compatible endpoint
export AXCLI_AI_KEY=your-key
export AXCLI_AI_PROVIDER=openai
export AXCLI_AI_URL=https://your-endpoint.openai.azure.com/v1

# Custom model
export AXCLI_MODEL=claude-opus-4-20250514
```

### Safety Classification

| Level | Behavior | Verbs |
|---|---|---|
| **Safe** | Auto-executes | `get`, `list`, `describe`, `status`, `show`, `view`, `logs`, `whoami`, `version`, `help`, `projects`, `pr`, `issue`, `repo` |
| **Confirm** | Asks "Proceed? [Y/n]" | `create`, `apply`, `patch`, `edit`, `set`, `label`, `scale`, `expose`, `login`, `close`, `merge` |
| **Dangerous** | Requires typing "yes" | `delete`, `rm`, `remove`, `destroy`, `purge`, `drain`, `drop`, `reset`, `wipe`, `nuke` |

### REPL Commands

| Command | Action |
|---|---|
| Natural language | Converted to CLI command via AI |
| Raw command (e.g., `pr list`) | Executed directly with binary prefix |
| `repeat` | Repeat the last output |
| `help` | Show session help |
| `quit` / `exit` / `q` | End the session |

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
