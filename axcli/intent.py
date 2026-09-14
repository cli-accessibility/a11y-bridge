"""LLM intent engine: natural language → CLI command + output summarization.

Supports Claude (Anthropic) and OpenAI-compatible APIs (Ollama, OpenAI, etc.)
via stdlib urllib — zero dependencies.
"""
import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass, field


@dataclass
class IntentResult:
    command: list[str]
    explanation: str
    is_read_only: bool = True
    confidence: float = 0.0
    error: str = ""


@dataclass
class SummaryResult:
    summary: str
    next_actions: list[str] = field(default_factory=list)
    error: str = ""


def _get_provider() -> str:
    """Detect LLM provider from environment.

    Priority:
    1. AXCLI_AI_PROVIDER env var (explicit: "anthropic", "openai", "ollama")
    2. AXCLI_AI_KEY + AXCLI_AI_URL → provider auto-detected from URL
    3. Provider-specific keys (ANTHROPIC_API_KEY, OPENAI_API_KEY)
    4. Ollama running locally
    """
    explicit = os.environ.get("AXCLI_AI_PROVIDER", "").lower()
    if explicit:
        return explicit

    # Generic key — detect provider from URL
    if os.environ.get("AXCLI_AI_KEY"):
        url = os.environ.get("AXCLI_AI_URL", "")
        if "anthropic" in url:
            return "anthropic"
        if "openai" in url or "api.openai" in url:
            return "openai"
        # Default to OpenAI-compatible API
        return "openai"

    # Provider-specific keys
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"

    # Try local Ollama
    url = os.environ.get("AXCLI_AI_URL", "http://localhost:11434")
    try:
        urllib.request.urlopen(f"{url}/api/tags", timeout=2)
        return "ollama"
    except Exception:
        pass
    return ""


def _get_api_key() -> str:
    """Get API key from generic or provider-specific env var."""
    return (
        os.environ.get("AXCLI_AI_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    )


def _call_anthropic(messages: list[dict], system: str) -> str:
    key = _get_api_key()
    body = json.dumps({
        "model": os.environ.get("AXCLI_MODEL", "claude-sonnet-4-20250514"),
        "max_tokens": 1024,
        "system": system,
        "messages": messages,
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        raise ConnectionError(f"Anthropic API error {e.code}: {body}")


def _call_openai_compatible(messages: list[dict], system: str, url: str, key: str) -> str:
    msgs = [{"role": "system", "content": system}] + messages
    model = os.environ.get("AXCLI_MODEL", "gpt-4o-mini")
    body = json.dumps({"model": model, "messages": msgs, "max_tokens": 1024}).encode()
    req = urllib.request.Request(
        f"{url}/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def _call_ollama(messages: list[dict], system: str) -> str:
    url = os.environ.get("AXCLI_AI_URL", "http://localhost:11434")
    model = os.environ.get("AXCLI_MODEL", "qwen2.5-coder:7b-instruct")
    msgs = [{"role": "system", "content": system}] + messages
    body = json.dumps({"model": model, "messages": msgs, "stream": False}).encode()
    req = urllib.request.Request(f"{url}/api/chat", data=body, headers={"Content-Type": "application/json"})
    # ponytail: 180s timeout — first call loads model into GPU memory, can take 30-90s
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
        return data["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        raise ConnectionError(f"Ollama API error {e.code}: {body}")


def _call_llm(messages: list[dict], system: str) -> str:
    provider = _get_provider()
    if not provider:
        raise ConnectionError(
            "No LLM available. Set AXCLI_AI_KEY and AXCLI_AI_PROVIDER, or start Ollama locally."
        )
    if provider == "anthropic":
        return _call_anthropic(messages, system)
    elif provider == "openai":
        url = os.environ.get("AXCLI_AI_URL", os.environ.get("AXCLI_AI_URL", "https://api.openai.com/v1"))
        return _call_openai_compatible(messages, system, url, _get_api_key())
    elif provider == "ollama":
        return _call_ollama(messages, system)
    else:
        raise ConnectionError(
            "No LLM available. Set AXCLI_AI_KEY and AXCLI_AI_PROVIDER, or start Ollama locally."
        )


INTENT_SYSTEM = """You are a CLI command generator for the tool: {binary}.
The user describes what they want in natural language. You return a JSON object with:
- "command": array of strings (the binary args to run, NOT including the binary name itself)
- "explanation": one sentence explaining what this command does
- "is_read_only": boolean, true if the command only reads data (get, list, describe, status, logs)

Rules:
- Return ONLY valid JSON, no markdown, no explanation outside the JSON
- Never invent flags that don't exist for this tool
- Prefer simple commands over complex pipelines
- For ambiguous requests, pick the most common interpretation
- If you cannot determine a command, set command to [] and explain why

Examples for gh:
User: "show my pull requests" → {{"command": ["pr", "list"], "explanation": "List open pull requests", "is_read_only": true}}
User: "create an issue about the login bug" → {{"command": ["issue", "create", "--title", "Login bug"], "explanation": "Create a new issue", "is_read_only": false}}
"""

SUMMARY_SYSTEM = """You are summarizing CLI output for a user who may be using a screen reader or audio interface.

Rules:
- Lead with the key result in one sentence
- Use plain language, no jargon
- Use cardinal numbers ("3 pods") not ordinal ("the third pod")
- If there are items, count them and list the most important ones
- If there are errors, explain what went wrong and what to do
- Suggest 1-2 natural follow-up actions the user might want
- Keep the summary under 5 sentences
- Return JSON: {{"summary": "...", "next_actions": ["...", "..."]}}
- Return ONLY valid JSON
"""


def get_intent(user_input: str, binary: str, context: list[dict] | None = None) -> IntentResult:
    """Convert natural language to a CLI command."""
    system = INTENT_SYSTEM.format(binary=binary)
    messages = list(context or [])
    messages.append({"role": "user", "content": user_input})

    try:
        raw = _call_llm(messages, system)
        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0]
        data = json.loads(raw)
        return IntentResult(
            command=data.get("command", []),
            explanation=data.get("explanation", ""),
            is_read_only=data.get("is_read_only", False),
            confidence=data.get("confidence", 0.8),
        )
    except (ConnectionError, urllib.error.URLError, TimeoutError) as e:
        return IntentResult(command=[], explanation="", error=f"LLM unavailable: {e}")
    except (json.JSONDecodeError, KeyError) as e:
        return IntentResult(command=[], explanation="", error=f"LLM returned invalid response: {e}")
    except Exception as e:
        return IntentResult(command=[], explanation="", error=f"LLM error: {e}")


def summarize_output(command: str, stdout: str, stderr: str, exit_code: int) -> SummaryResult:
    """Summarize CLI output for accessible consumption."""
    # Truncate long output
    max_chars = 3000
    if len(stdout) > max_chars:
        stdout = stdout[:max_chars] + f"\n... ({len(stdout) - max_chars} more characters)"

    prompt = f"""Command: {command}
Exit code: {exit_code}
Stdout:
{stdout}
Stderr:
{stderr}

Summarize this output."""

    try:
        raw = _call_llm([{"role": "user", "content": prompt}], SUMMARY_SYSTEM)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0]
        data = json.loads(raw)
        return SummaryResult(
            summary=data.get("summary", raw),
            next_actions=data.get("next_actions", []),
        )
    except Exception:
        # Fallback: return first 3 lines as summary
        lines = stdout.strip().splitlines()[:3]
        return SummaryResult(summary="\n".join(lines) if lines else stderr.strip()[:200])
