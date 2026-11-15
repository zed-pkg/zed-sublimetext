from __future__ import annotations

import stat
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

MANIFEST_NAME = ".zpkg.toml"
LOCKFILE_NAME = ".zpkg.lock"
PROJECT_MARKERS = (
    MANIFEST_NAME,
    LOCKFILE_NAME,
    ".git",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pyproject.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "pubspec.yaml",
)


def find_project_root(start: Path, window_folders: Sequence[Path] = ()) -> Path:
    """Find the closest Zed project, then a native project, then a window folder."""
    start = start.expanduser()
    current = start if start.is_dir() else start.parent
    current = _safe_resolve(current)

    zed_root = _search_upward(current, (MANIFEST_NAME, LOCKFILE_NAME))
    if zed_root is not None:
        return zed_root

    native_root = _search_upward(current, PROJECT_MARKERS[2:])
    if native_root is not None:
        return native_root

    folder_roots = [_safe_resolve(path) for path in window_folders]
    manifest_folders = [
        folder for folder in folder_roots if _is_package_marker(folder / MANIFEST_NAME)
    ]
    if len(manifest_folders) == 1:
        return manifest_folders[0]

    containing = [folder for folder in folder_roots if _is_relative_to(current, folder)]
    if containing:
        return max(containing, key=lambda path: len(path.parts))

    if folder_roots:
        return folder_roots[0]
    return current


def discover_zed_roots(window_folders: Sequence[Path]) -> List[Path]:
    roots = []
    seen = set()
    for folder in window_folders:
        folder = _safe_resolve(folder)
        candidates = [folder]
        try:
            candidates.extend(path.parent for path in folder.rglob(MANIFEST_NAME))
        except OSError:
            pass
        for candidate in candidates:
            key = str(candidate)
            if key not in seen and (
                _is_package_marker(candidate / MANIFEST_NAME)
                or _is_package_marker(candidate / LOCKFILE_NAME)
            ):
                seen.add(key)
                roots.append(candidate)
    return roots


def _is_package_marker(path: Path) -> bool:
    """Do not follow a forged manifest/lock symlink (or accept a directory)."""
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except (OSError, ValueError):
        return False


def _marker_exists(path: Path) -> bool:
    if path.name in (MANIFEST_NAME, LOCKFILE_NAME):
        return _is_package_marker(path)
    return path.exists()


def _search_upward(start: Path, markers: Iterable[str]) -> Optional[Path]:
    marker_names = tuple(markers)
    current = start
    while True:
        if any(_marker_exists(current / marker) for marker in marker_names):
            return current
        if current.parent == current:
            return None
        current = current.parent


def _safe_resolve(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
