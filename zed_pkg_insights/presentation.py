from __future__ import annotations

import datetime
from pathlib import Path
from typing import List

from .model import Diagnostic, Severity, Snapshot

_ICONS = {
    Severity.ERROR: "ERROR",
    Severity.WARNING: "WARN ",
    Severity.INFO: "INFO ",
    Severity.OK: "OK   ",
}


def render_snapshot(snapshot: Snapshot) -> str:
    generated = datetime.datetime.fromtimestamp(snapshot.generated_at_epoch).isoformat(timespec="seconds")
    lines: List[str] = [
        "Zed Package Insights",
        "=" * 80,
        "Root:       {0}".format(snapshot.root),
        "Manifest:   {0}".format(snapshot.manifest or "not present"),
        "Lockfile:   {0}".format(snapshot.lockfile or "not present"),
        "Dependencies: {0}".format(snapshot.dependency_dir),
        "CLI:        {0}".format(snapshot.cli_version or "not available"),
        "Generated:  {0}".format(generated),
        "",
        "Summary: {0} error(s), {1} warning(s), {2} informational".format(
            snapshot.errors, snapshot.warnings, snapshot.infos
        ),
        "",
    ]

    for diagnostic in snapshot.diagnostics:
        lines.extend(_render_diagnostic(diagnostic, snapshot.root))

    if snapshot.actions:
        lines.extend(["Recommended actions", "-" * 80])
        for index, action in enumerate(snapshot.actions, 1):
            lines.append("{0}. {1}".format(index, action.title))
            if action.description:
                lines.append("   {0}".format(action.description))
            if action.argv:
                lines.append("   Command: {0}".format(action.display_command()))
        lines.append("")
        lines.append("Run 'Zed: Recommended Actions' from the Command Palette to apply one.")

    return "\n".join(lines).rstrip() + "\n"


def _render_diagnostic(diagnostic: Diagnostic, root: Path) -> List[str]:
    location = ""
    if diagnostic.path is not None:
        try:
            relative = diagnostic.path.relative_to(root)
            location = " [{0}]".format(relative or ".")
        except ValueError:
            location = " [{0}]".format(diagnostic.path)
        if diagnostic.line is not None:
            location = location[:-1] + ":{0}]".format(diagnostic.line)

    lines = [
        "{0} {1}: {2}{3}".format(
            _ICONS[diagnostic.severity], diagnostic.code, diagnostic.summary, location
        )
    ]
    if diagnostic.detail:
        lines.append("      {0}".format(diagnostic.detail))
    for action in diagnostic.actions:
        lines.append("      -> {0}".format(action.title))
    lines.append("")
    return lines
