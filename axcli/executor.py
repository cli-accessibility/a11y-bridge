"""Run a command with accessibility environment enforced."""
import os
import subprocess
from dataclasses import dataclass


@dataclass
class ExecResult:
    stdout: str
    stderr: str
    exit_code: int


def run(argv: list[str], timeout: int = 120) -> ExecResult:
    env = {**os.environ, "NO_COLOR": "1", "TERM": "dumb"}
    # ponytail: no shell=True ever — argv as list prevents injection
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )
        return ExecResult(proc.stdout, proc.stderr, proc.returncode)
    except subprocess.TimeoutExpired:
        return ExecResult("", f"error: command timed out after {timeout}s", 124)
    except FileNotFoundError:
        return ExecResult("", f"error: command not found: {argv[0]}", 127)
