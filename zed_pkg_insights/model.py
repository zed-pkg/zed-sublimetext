from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    OK = "ok"


class ActionKind(str, Enum):
    RUN_ZED = "run_zed"
    COPY_COMMAND = "copy_command"
    OPEN_FILE = "open_file"
    OPEN_SETTINGS = "open_settings"


@dataclass(frozen=True)
class Action:
    id: str
    title: str
    description: str
    kind: ActionKind
    argv: Tuple[str, ...] = ()
    path: Optional[Path] = None
    requires_confirmation: bool = False

    def display_command(self) -> str:
        return " ".join(_quote_argument(part) for part in self.argv)


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: Severity
    summary: str
    detail: str = ""
    path: Optional[Path] = None
    line: Optional[int] = None
    actions: Tuple[Action, ...] = ()


@dataclass(frozen=True)
class Snapshot:
    root: Path
    manifest: Optional[Path]
    lockfile: Optional[Path]
    dependency_dir: Path
    diagnostics: Tuple[Diagnostic, ...]
    cli_version: Optional[str] = None
    generated_at_epoch: float = 0.0

    @property
    def errors(self) -> int:
        return sum(item.severity == Severity.ERROR for item in self.diagnostics)

    @property
    def warnings(self) -> int:
        return sum(item.severity == Severity.WARNING for item in self.diagnostics)

    @property
    def infos(self) -> int:
        return sum(item.severity == Severity.INFO for item in self.diagnostics)

    @property
    def actions(self) -> Tuple[Action, ...]:
        seen = set()
        result: List[Action] = []
        for diagnostic in self.diagnostics:
            for action in diagnostic.actions:
                if action.id not in seen:
                    seen.add(action.id)
                    result.append(action)
        return tuple(result)

    @property
    def health(self) -> Severity:
        if self.errors:
            return Severity.ERROR
        if self.warnings:
            return Severity.WARNING
        if self.infos:
            return Severity.INFO
        return Severity.OK

    def status_text(self) -> str:
        if self.errors:
            return "Zed: {0} error(s), {1} warning(s)".format(self.errors, self.warnings)
        if self.warnings:
            return "Zed: {0} warning(s)".format(self.warnings)
        return "Zed: package state healthy"


def _quote_argument(value: str) -> str:
    if not value:
        return "''"
    if all(char.isalnum() or char in "-._/:=@" for char in value):
        return value
    return "'" + value.replace("'", "'\\''") + "'"
