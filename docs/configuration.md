# Configuration and Reference

## Options

```
a11y-bridge [options] <command> [args...]

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
a11y-bridge oc get pods                       # same as --domain color
a11y-bridge --domain color oc get pods        # explicit
```

## Domain: screen-reader

Forces screen reader mode regardless of terminal context. Use when you want text labels and table conversion even in a normal terminal.

```bash
a11y-bridge --domain screen-reader oc projects
status: Running: oc projects
result: You have access to the following projects...
result:   * arewm-tenant - arewm
result:     gatekeeper-tenant - gatekeeper
```

## Domain: audio

Speaks command output using text-to-speech. In `--askai` mode, also supports voice input via the `v` key.

```bash
# Speak output of any command
a11y-bridge --domain audio oc get pods

# AI session with voice output and input
a11y-bridge --domain audio --askai gh
```

In the AI session, type `v` then speak your command. Press Ctrl+C to stop recording.

### Audio Environment Variables

| Variable | Default | Description |
|---|---|---|
| `A11Y_TTS_ENGINE` | auto-detect | Force TTS engine: `piper`, `espeak-ng`, `say`, `none` |
| `A11Y_TTS_RATE` | `170` | Speech rate in words per minute |
| `A11Y_PIPER_MODEL` | `~/.cache/a11y-bridge/piper/en_US-lessac-medium.onnx` | Path to Piper voice model |

### TTS Engine Priority

| Engine | Quality | Latency | Install |
|---|---|---|---|
| Piper | Natural (neural) | ~3s/sentence | `pip install piper-tts` + voice model |
| espeak-ng | Robotic (formant) | ~50ms | System package (usually pre-installed) |
| say | System voice | ~100ms | macOS built-in |

### System Prerequisites

Audio features require system packages for playback and recording:

```bash
# Linux (Fedora/RHEL)
sudo dnf install espeak-ng pulseaudio-utils alsa-utils

# Linux (Ubuntu/Debian)
sudo apt install espeak-ng pulseaudio-utils alsa-utils

# macOS — use built-in 'say' for TTS, or:
brew install espeak-ng
```

- `espeak-ng` — fallback TTS engine (robotic but instant)
- `pulseaudio-utils` — provides `paplay` for Piper audio output
- `alsa-utils` — provides `arecord` for microphone recording (voice input)

### Voice Input (STT) Setup

```bash
pip install vosk
mkdir -p ~/.cache/a11y-bridge
cd ~/.cache/a11y-bridge
curl -sL https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip -o model.zip
unzip -q model.zip && mv vosk-model-small-en-us-0.15 vosk-model && rm model.zip
```

Requires `arecord` (Linux) or `sox` (cross-platform) for microphone capture.

## --raw

Strips all ANSI escape sequences but preserves the original output structure. No table conversion, no labels, no color additions.

```bash
a11y-bridge --raw kubectl logs my-pod
```

## --passthrough

Runs the command with `NO_COLOR=1` and `TERM=dumb` environment variables set but does not process the output at all.

```bash
a11y-bridge --passthrough git diff
```

## AI Mode (--askai)

Start an interactive session where natural language is converted to CLI commands:

```bash
a11y-bridge --askai gh
a11y-bridge --askai oc
a11y-bridge --askai kubectl
```

### AI Environment Variables

| Variable | Required | Description |
|---|---|---|
| `A11Y_AI_KEY` | Yes (unless Ollama) | API key for the AI provider |
| `A11Y_AI_PROVIDER` | No | Explicit provider: `anthropic`, `openai`, `ollama`. Auto-detected if not set. |
| `A11Y_AI_URL` | No | Custom API endpoint (default: provider's standard URL, or `http://localhost:11434` for Ollama) |
| `A11Y_MODEL` | No | Model name override (default: `claude-sonnet-4-6` for Anthropic, `gpt-4o-mini` for OpenAI, `qwen2.5-coder:7b-instruct` for Ollama) |

Provider-specific keys are also supported as fallbacks:

| Variable | Provider |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic (Claude) |
| `OPENAI_API_KEY` | OpenAI / compatible APIs |

### Provider Detection Priority

1. `A11Y_AI_PROVIDER` env var (explicit)
2. `A11Y_AI_KEY` + `A11Y_AI_URL` (provider inferred from URL)
3. `ANTHROPIC_API_KEY` (Anthropic)
4. `OPENAI_API_KEY` (OpenAI)
5. Ollama running on localhost:11434 (auto-detected, no key needed)

### Setup Examples

```bash
# Claude (Anthropic)
export A11Y_AI_KEY=sk-ant-...
export A11Y_AI_PROVIDER=anthropic

# OpenAI
export A11Y_AI_KEY=sk-...
export A11Y_AI_PROVIDER=openai

# Local Ollama (no key, no provider — auto-detected)
# Install from https://ollama.com/download, then:
ollama serve
ollama pull qwen2.5-coder:7b-instruct   # ~4.7GB download, one-time &
ollama pull qwen2.5-coder:7b-instruct

# Azure OpenAI or other compatible endpoint
export A11Y_AI_KEY=your-key
export A11Y_AI_PROVIDER=openai
export A11Y_AI_URL=https://your-endpoint.openai.azure.com/v1

# Custom model
export A11Y_MODEL=claude-opus-4-20250514
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

a11y-bridge automatically detects screen reader usage:

| Signal | Triggers accessible mode |
|---|---|
| `NO_COLOR` env var set (non-empty) | Yes |
| `TERM=dumb` | Yes |
| `A11Y_SCREEN_READER=1` env var | Yes |
| `orca` process running (Linux) | Yes |
| `nvda` or `jaws` process running (Windows) | Yes |
| None of the above | No — sighted mode |

To force screen reader mode without setting global env vars:

```bash
A11Y_SCREEN_READER=1 a11y-bridge oc get pods
```

## Pipe Behavior

When stdout is not a terminal (piped or redirected), a11y-bridge strips ANSI but passes output through without labels, colors, or reformatting:

```bash
a11y-bridge oc get pods              # Adaptive (terminal)
a11y-bridge oc get pods | grep nginx  # Raw stripped output (pipe)
a11y-bridge oc get pods > pods.txt    # Raw stripped output (file)
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
| `status:` | What a11y-bridge is doing (the command being run) |
| `result:` | Successful command output |
| `error:` | Error messages from the wrapped command |
| `[ERROR]` | Injected by color interpretation (was red) |
| `[OK]` | Injected by color interpretation (was green) |
| `[WARN]` | Injected by color interpretation (was yellow) |
| `[SELECTED: ...]` | Text shown in inverse video |
