#!/usr/bin/env bash
set -euo pipefail

owner="${ZED_GITHUB_OWNER:-zed-pkg}"
repo="${ZED_GITHUB_REPO:-zed-sublimetext}"
full_name="${owner}/${repo}"
description="Sublime Text package insights, diagnostics, and guided resolutions for Zed Package Manager projects"

command -v gh >/dev/null 2>&1 || {
  echo "gh is required: https://cli.github.com" >&2
  exit 1
}

gh auth status >/dev/null

if gh repo view "${full_name}" >/dev/null 2>&1; then
  echo "Refusing to overwrite existing repository ${full_name}" >&2
  exit 2
fi

if [[ ! -d .git ]]; then
  git init -b main
fi

if ! git config user.email >/dev/null; then
  git config user.email "zed-pkg-automation@users.noreply.github.com"
fi
if ! git config user.name >/dev/null; then
  git config user.name "zed-pkg automation"
fi

git add -A
if ! git diff --cached --quiet; then
  git commit -m "scaffold Sublime Text package insights plugin"
fi

gh repo create "${full_name}" \
  --public \
  --description "${description}" \
  --source . \
  --remote origin \
  --push

echo "Published https://github.com/${full_name}"
