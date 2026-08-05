# Project tracking

## Canonical mapping

| Surface | Destination |
|---|---|
| GitHub organization | `zed-pkg` |
| Repository | `zed-pkg/zed-sublimetext` |
| Linear project | `github.com/zed-pkg` |
| Linear delivery issue | [`DEN-2326`](https://linear.app/denman/issue/DEN-2326/zed-sublimetext-package-publish-and-track-the-sublime-text-extension) |
| Linear delivery document | [zed-sublimetext extension delivery and project tracking contract](https://linear.app/denman/document/zed-sublimetext-extension-delivery-and-project-tracking-contract-d848b2cadac8) |
| GitHub Project | `zed-pkg-project` |
| Shared CLI dependency | [`zed-pkg/zed-cli#191`](https://github.com/zed-pkg/zed-cli/issues/191) |

`zed-pkg` is an independent package manager and is unrelated to the Zed text
editor. This repository is specifically the Sublime Text integration for the
package manager.

## Delivery lanes

The `zed-pkg-project` board should track these lanes:

1. **IDE diagnostics** — project discovery, manifest/lock state, output panels,
   and safe recommended actions.
2. **CLI contract** — adoption of the non-mutating `zed inspect --format json`
   contract tracked in `zed-cli#191`.
3. **Packaging** — deterministic `.sublime-package` builds, CI artifacts,
   release checksums, and Package Control submission.
4. **Compatibility** — Sublime Python 3.8/3.14, Windows, macOS, and Linux.
5. **Security** — confirmation gates, argument-array execution, output
   redaction, and prevention of accidental editor-launcher invocation.

## Suggested GitHub Project fields

- **Status:** Backlog, Ready, In Progress, In Review, Done
- **Priority:** Urgent, High, Medium, Low
- **Area:** IDE Integration, CLI Contract, Packaging, Documentation, Testing
- **Repository:** `zed-sublimetext`

All implementation issues and pull requests should be associated with
`zed-pkg-project`. Linear remains the cross-repository planning and delivery
record; GitHub Project remains the repository-adjacent execution view.

## Artifact publication

CI runs the Python 3.8 and 3.14 test matrix before building
`dist/ZedPackageInsights.sublime-package`. The archive is deterministic and is
published as a GitHub Actions artifact named `ZedPackageInsights-<commit-sha>`.

Before a public release or Package Control submission:

1. download the artifact from a successful `main` workflow run;
2. verify the archive opens and contains no development-only paths;
3. install it in a clean Sublime Text profile;
4. verify diagnostics against healthy, stale-lock, lock-only, and interrupted
   transaction fixtures;
5. record the release checksum in the GitHub release notes and Linear issue.
