#!/usr/bin/env python3
"""Build a deterministic Sublime Text .sublime-package archive."""

from __future__ import print_function

import argparse
import os
import stat
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "dist" / "ZedPackageInsights.sublime-package"
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
EXCLUDED_TOP_LEVEL = {
    ".git",
    ".github",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "scripts",
    "tests",
}
EXCLUDED_ROOT_FILES = {
    ".gitignore",
    ".zpkg.lock",
    ".zpkg.toml",
    "pyproject.toml",
}


def package_files(root):
    """Return package files in deterministic archive order."""
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.parts[0] in EXCLUDED_TOP_LEVEL:
            continue
        if len(relative.parts) == 1 and relative.name in EXCLUDED_ROOT_FILES:
            continue
        if "__pycache__" in relative.parts:
            continue
        if path.suffix in {".pyc", ".pyo", ".zip", ".sublime-package"}:
            continue
        files.append(relative)
    return sorted(files, key=lambda item: item.as_posix())


def build_package(root, output):
    """Build the archive and return its path."""
    root = root.resolve()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(
        str(output),
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for relative in package_files(root):
            source = root / relative
            info = zipfile.ZipInfo(relative.as_posix(), FIXED_TIMESTAMP)
            info.create_system = 3
            mode = stat.S_IFREG | 0o644
            if os.access(str(source), os.X_OK):
                mode = stat.S_IFREG | 0o755
            info.external_attr = mode << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, source.read_bytes())

    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build_package(args.root, args.output)
    print(result)


if __name__ == "__main__":
    main()
