from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Sequence, Tuple

from .redaction import redact


@dataclass(frozen=True)
class CommandResult:
    argv: Tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    launch_error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out and self.launch_error is None


class CommandRunner:
    def run(
        self,
        argv: Sequence[str],
        cwd: Path,
        timeout_seconds: float = 15.0,
        extra_env: Optional[Mapping[str, str]] = None,
    ) -> CommandResult:
        command = tuple(str(part) for part in argv)
        if not command:
            return CommandResult(command, 2, "", "", launch_error="empty command")

        environment = os.environ.copy()
        environment.update({"NO_COLOR": "1", "CLICOLOR": "0", "TERM": "dumb"})
        if extra_env:
            environment.update({str(key): str(value) for key, value in extra_env.items()})

        try:
            completed = subprocess.run(
                command,
                cwd=str(cwd),
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                shell=False,
                check=False,
            )
            return CommandResult(
                command,
                completed.returncode,
                redact(completed.stdout),
                redact(completed.stderr),
            )
        except subprocess.TimeoutExpired as error:
            stdout = _coerce_text(error.stdout)
            stderr = _coerce_text(error.stderr)
            return CommandResult(
                command,
                124,
                redact(stdout),
                redact(stderr),
                timed_out=True,
            )
        except OSError as error:
            return CommandResult(command, 127, "", "", launch_error=redact(str(error)))


def _coerce_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
