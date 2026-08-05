from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .model import Action, ActionKind, Diagnostic, Severity, Snapshot
from .project import LOCKFILE_NAME, MANIFEST_NAME
from .runner import CommandRunner

try:
    import tomllib  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - old Sublime builds using actual Python 3.8
    tomllib = None  # type: ignore[assignment]


class Analyzer:
    def __init__(self, runner: Optional[CommandRunner] = None) -> None:
        self.runner = runner or CommandRunner()

    def analyze(
        self,
        root: Path,
        zed_binary: str = "zed",
        probe_cli: bool = True,
        command_timeout_seconds: float = 8.0,
    ) -> Snapshot:
        root = root.expanduser().absolute()
        manifest = root / MANIFEST_NAME
        lockfile = root / LOCKFILE_NAME
        manifest_path = manifest if manifest.is_file() else None
        lockfile_path = lockfile if lockfile.is_file() else None
        diagnostics: List[Diagnostic] = []
        manifest_data: Optional[Mapping[str, Any]] = None
        lock_data: Optional[Mapping[str, Any]] = None

        if lockfile_path is not None:
            lock_data, lock_diagnostic = _read_lockfile(lockfile_path)
            if lock_diagnostic is not None:
                diagnostics.append(lock_diagnostic)

        if manifest_path is None and lockfile_path is None:
            diagnostics.append(
                Diagnostic(
                    code="ZED001",
                    severity=Severity.INFO,
                    summary="This folder is not a Zed-managed package yet",
                    detail="No .zpkg.toml or .zpkg.lock was found at the selected project root.",
                    path=root,
                    actions=(
                        _run_action(
                            "zed-init",
                            "Initialize a Zed package",
                            "Create an annotated .zpkg.toml in this folder.",
                            (zed_binary, "init"),
                            confirm=True,
                        ),
                    ),
                )
            )
        elif manifest_path is None and lockfile_path is not None:
            diagnostics.append(
                Diagnostic(
                    code="ZED002",
                    severity=Severity.WARNING,
                    summary="Lock-only Zed project",
                    detail=(
                        "The lockfile cannot identify direct versus transitive dependencies. "
                        "Use the explicit lock-only frozen restore mode."
                    ),
                    path=lockfile_path,
                    actions=(
                        _run_action(
                            "zed-lock-only-restore",
                            "Restore the lock-only project",
                            "Install exactly the pinned graph without inventing a manifest.",
                            (
                                zed_binary,
                                "install",
                                "--frozen",
                                "--do-not-write-new-manifest",
                            ),
                            confirm=True,
                        ),
                    ),
                )
            )

        if manifest_path is not None:
            manifest_data, parse_diagnostic = _read_manifest(manifest_path)
            if parse_diagnostic is not None:
                diagnostics.append(parse_diagnostic)

            if lockfile_path is None:
                diagnostics.append(
                    Diagnostic(
                        code="ZED003",
                        severity=Severity.WARNING,
                        summary="Manifest has no lockfile",
                        detail=(
                            "Dependencies are not pinned yet. Run a normal install to resolve and "
                            "write .zpkg.lock."
                        ),
                        path=manifest_path,
                        actions=(
                            _run_action(
                                "zed-install",
                                "Resolve and install dependencies",
                                "Run zed install in the package root.",
                                (zed_binary, "install"),
                                confirm=True,
                            ),
                        ),
                    )
                )
            elif _is_newer(manifest_path, lockfile_path):
                diagnostics.append(
                    Diagnostic(
                        code="ZED004",
                        severity=Severity.WARNING,
                        summary="Manifest is newer than the lockfile",
                        detail=(
                            "The dependency intent may have changed since the lock was generated. "
                            "Resolve again before relying on the locked graph."
                        ),
                        path=manifest_path,
                        actions=(
                            _run_action(
                                "zed-refresh-lock",
                                "Refresh the lockfile",
                                "Run zed install to reconcile manifest intent and pins.",
                                (zed_binary, "install"),
                                confirm=True,
                            ),
                        ),
                    )
                )

            if manifest_data and _looks_generated_consumer(manifest_data, manifest_path):
                diagnostics.append(
                    Diagnostic(
                        code="ZED005",
                        severity=Severity.INFO,
                        summary="Generated consumer manifest needs identity review before publishing",
                        detail=(
                            "The package appears to use the generated local identity. Review the "
                            "organization, package name, repository URL, and generated marker."
                        ),
                        path=manifest_path,
                        actions=(
                            Action(
                                id="open-manifest",
                                title="Open .zpkg.toml",
                                description="Review and replace the generated package identity.",
                                kind=ActionKind.OPEN_FILE,
                                path=manifest_path,
                            ),
                        ),
                    )
                )

        dependency_dir = _dependency_dir(root, manifest_data)
        has_dependency_intent = _has_dependency_intent(
            manifest_data, lockfile_path, lock_data
        )
        if lockfile_path is not None and has_dependency_intent and not dependency_dir.exists():
            command = (zed_binary, "install", "--frozen")
            if manifest_path is None:
                command += ("--do-not-write-new-manifest",)
            diagnostics.append(
                Diagnostic(
                    code="ZED006",
                    severity=Severity.WARNING,
                    summary="Pinned dependencies are not materialized",
                    detail="The lockfile exists, but the configured Zed dependency directory does not.",
                    path=dependency_dir,
                    actions=(
                        _run_action(
                            "zed-frozen-restore",
                            "Restore pinned dependencies",
                            "Materialize exactly the versions recorded in .zpkg.lock.",
                            command,
                            confirm=True,
                        ),
                    ),
                )
            )

        staging = root / ".zpkg-staging"
        if staging.is_dir() and _directory_has_entries(staging):
            recovery_command = [zed_binary, "install"]
            if lockfile_path is not None:
                recovery_command.append("--frozen")
                if manifest_path is None:
                    recovery_command.append("--do-not-write-new-manifest")
            diagnostics.append(
                Diagnostic(
                    code="ZED007",
                    severity=Severity.ERROR,
                    summary="Interrupted Zed transaction needs recovery",
                    detail=(
                        ".zpkg-staging contains transaction state. The next lifecycle command should "
                        "recover it before starting new work."
                    ),
                    path=staging,
                    actions=(
                        _run_action(
                            "zed-recover",
                            "Run lifecycle recovery",
                            "Run a Zed lifecycle command; recovery happens before new work starts.",
                            tuple(recovery_command),
                            confirm=True,
                        ),
                    ),
                )
            )

        cli_version: Optional[str] = None
        if probe_cli:
            cli_version, cli_diagnostic = self._probe_cli(
                root, zed_binary, command_timeout_seconds
            )
            if cli_diagnostic is not None:
                diagnostics.append(cli_diagnostic)

        if not diagnostics:
            diagnostics.append(
                Diagnostic(
                    code="ZED000",
                    severity=Severity.OK,
                    summary="No package-state problems detected",
                    detail="Manifest, lockfile, dependency materialization, and CLI probe look consistent.",
                    path=root,
                )
            )

        return Snapshot(
            root=root,
            manifest=manifest_path,
            lockfile=lockfile_path,
            dependency_dir=dependency_dir,
            diagnostics=tuple(diagnostics),
            cli_version=cli_version,
            generated_at_epoch=time.time(),
        )

    def _probe_cli(
        self, root: Path, zed_binary: str, timeout_seconds: float
    ) -> Tuple[Optional[str], Optional[Diagnostic]]:
        version_result = self.runner.run((zed_binary, "--version"), root, timeout_seconds)
        if version_result.launch_error:
            return None, Diagnostic(
                code="ZED008",
                severity=Severity.ERROR,
                summary="Zed package CLI was not found",
                detail=version_result.launch_error,
                path=root,
                actions=(
                    Action(
                        id="open-plugin-settings",
                        title="Configure the Zed CLI path",
                        description="Set zed_binary to the package-manager executable.",
                        kind=ActionKind.OPEN_SETTINGS,
                    ),
                ),
            )
        if version_result.timed_out:
            return None, Diagnostic(
                code="ZED009",
                severity=Severity.ERROR,
                summary="Zed CLI version probe timed out",
                detail="The configured executable did not answer within the plugin timeout.",
                path=root,
            )
        if not version_result.ok:
            detail = (version_result.stderr or version_result.stdout).strip()
            return None, Diagnostic(
                code="ZED010",
                severity=Severity.ERROR,
                summary="Configured Zed executable failed its version probe",
                detail=detail or "The process exited with code {0}.".format(version_result.returncode),
                path=root,
            )

        version = (version_result.stdout or version_result.stderr).strip().splitlines()
        cli_version = version[0] if version else "unknown"

        help_result = self.runner.run((zed_binary, "--help"), root, timeout_seconds)
        help_text = (help_result.stdout + "\n" + help_result.stderr).lower()
        if help_result.ok and "universal package manager" not in help_text:
            return cli_version, Diagnostic(
                code="ZED011",
                severity=Severity.ERROR,
                summary="The configured 'zed' appears to be a different application",
                detail=(
                    "The Zed editor also installs a zed executable. Configure zed_binary to the "
                    "zed-pkg CLI whose help identifies it as the universal package manager."
                ),
                path=root,
                actions=(
                    Action(
                        id="open-plugin-settings",
                        title="Configure the Zed CLI path",
                        description="Point the plugin at the zed-pkg executable.",
                        kind=ActionKind.OPEN_SETTINGS,
                    ),
                ),
            )
        return cli_version, None


def _read_lockfile(path: Path) -> Tuple[Optional[Mapping[str, Any]], Optional[Diagnostic]]:
    if tomllib is None:
        return None, None
    try:
        with path.open("rb") as handle:
            value = tomllib.load(handle)
    except (OSError, UnicodeError) as error:
        return None, Diagnostic(
            code="ZED015",
            severity=Severity.ERROR,
            summary="Could not read .zpkg.lock",
            detail=str(error),
            path=path,
        )
    except tomllib.TOMLDecodeError as error:
        return None, Diagnostic(
            code="ZED016",
            severity=Severity.ERROR,
            summary=".zpkg.lock is not valid TOML",
            detail=str(error),
            path=path,
            line=getattr(error, "lineno", None),
            actions=(
                Action(
                    id="open-invalid-lock",
                    title="Open the invalid lockfile",
                    description="Inspect .zpkg.lock; normally it should be regenerated by Zed.",
                    kind=ActionKind.OPEN_FILE,
                    path=path,
                ),
            ),
        )

    version = value.get("version")
    if version != 1:
        return value, Diagnostic(
            code="ZED017",
            severity=Severity.WARNING,
            summary="Unsupported Zed lockfile schema version",
            detail="Expected lockfile version 1, found {0!r}.".format(version),
            path=path,
        )
    return value, None


def _read_manifest(path: Path) -> Tuple[Optional[Mapping[str, Any]], Optional[Diagnostic]]:
    if tomllib is None:
        return None, Diagnostic(
            code="ZED012",
            severity=Severity.INFO,
            summary="Full TOML validation is unavailable in this Sublime runtime",
            detail=(
                "The plugin can still inspect file state. A current Sublime Text build provides "
                "Python with tomllib for precise manifest validation."
            ),
            path=path,
        )
    try:
        with path.open("rb") as handle:
            value = tomllib.load(handle)
        return value, None
    except (OSError, UnicodeError) as error:
        return None, Diagnostic(
            code="ZED013",
            severity=Severity.ERROR,
            summary="Could not read .zpkg.toml",
            detail=str(error),
            path=path,
        )
    except tomllib.TOMLDecodeError as error:
        line = getattr(error, "lineno", None)
        return None, Diagnostic(
            code="ZED014",
            severity=Severity.ERROR,
            summary=".zpkg.toml is not valid TOML",
            detail=str(error),
            path=path,
            line=line,
            actions=(
                Action(
                    id="open-invalid-manifest",
                    title="Open the invalid manifest",
                    description="Jump to .zpkg.toml and correct the TOML syntax.",
                    kind=ActionKind.OPEN_FILE,
                    path=path,
                ),
            ),
        )


def _dependency_dir(root: Path, manifest_data: Optional[Mapping[str, Any]]) -> Path:
    configured = None
    if manifest_data:
        install = manifest_data.get("install")
        if isinstance(install, Mapping):
            value = install.get("dir")
            if isinstance(value, str) and value.strip():
                configured = value.strip()
    return root / (configured or "zed_modules")


def _has_dependency_intent(
    manifest_data: Optional[Mapping[str, Any]],
    lockfile_path: Optional[Path],
    lock_data: Optional[Mapping[str, Any]],
) -> bool:
    if manifest_data:
        for section_name in ("dependencies", "dev-dependencies", "build-dependencies"):
            section = manifest_data.get(section_name)
            if isinstance(section, Mapping) and bool(section):
                return True

    if lockfile_path is None:
        return False

    if lock_data is not None:
        return any(key != "version" and bool(value) for key, value in lock_data.items())

    if tomllib is not None:
        # A malformed/unreadable lock should not be treated as proof of an empty graph.
        return True

    try:
        meaningful_lines = [
            line.strip()
            for line in lockfile_path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    except OSError:
        return True
    return meaningful_lines != ["version = 1"]


def _looks_generated_consumer(data: Mapping[str, Any], path: Path) -> bool:
    package = data.get("package")
    if isinstance(package, Mapping):
        org = package.get("org")
        repository = package.get("repository") or package.get("repo")
        generated = package.get("generated") or package.get("generated_consumer")
        if isinstance(org, str) and org == "zed-local":
            return True
        if isinstance(repository, str) and "localhost" in repository:
            return True
        if generated is True or generated == "zed-generated-consumer":
            return True
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "zed-generated-consumer" in text or "zed-local/" in text


def _is_newer(first: Path, second: Path, tolerance_seconds: float = 1.0) -> bool:
    try:
        return first.stat().st_mtime > second.stat().st_mtime + tolerance_seconds
    except OSError:
        return False


def _directory_has_entries(path: Path) -> bool:
    try:
        return next(path.iterdir(), None) is not None
    except OSError:
        return False


def _run_action(
    action_id: str,
    title: str,
    description: str,
    argv: Sequence[str],
    confirm: bool,
) -> Action:
    return Action(
        id=action_id,
        title=title,
        description=description,
        kind=ActionKind.RUN_ZED,
        argv=tuple(argv),
        requires_confirmation=confirm,
    )
