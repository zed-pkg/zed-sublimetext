# Zed Package Insights for Sublime Text

`zed-sublimetext` brings Zed Package Manager state into Sublime Text. It finds
the active package root, checks the manifest/lock/materialization relationship,
flags interrupted transactions, verifies that the configured `zed` executable
is the package-manager CLI, and offers guided resolutions.

## Why Python, not C/C++/Rust?

Sublime Text plugins run inside a Python plugin host. The editor-facing layer is
therefore Python so it can use native commands, event listeners, output panels,
quick panels, settings, and status messages directly. Zed's package logic stays
in the Rust `zed` CLI. A native helper can be added later only for functionality
that cannot live behind the CLI boundary.

## Current insights

- missing `.zpkg.toml` / package initialization;
- lock-only projects and the explicit frozen restore command;
- manifest without `.zpkg.lock`;
- manifest newer than the lockfile;
- configured `[install].dir` not materialized;
- generated consumer identity that must be reviewed before publishing;
- invalid TOML with an open-file action;
- interrupted `.zpkg-staging` transactions;
- missing, failing, timed-out, or incorrect `zed` executable;
- healthy package state.

All automatic checks are local and non-mutating. Commands such as `zed init`,
`zed install`, and frozen restore are displayed as recommendations and require
an explicit confirmation before execution.

## Commands

Open the Command Palette and use:

- `Zed: Refresh Package Insights`
- `Zed: Show Package Insights`
- `Zed: Recommended Actions`
- `Preferences: Zed Package Insights Settings`

## Installation for development

1. Clone this repository into Sublime Text's `Packages` directory as
   `ZedPackageInsights`, or symlink it there.
2. Open a folder containing `.zpkg.toml` or `.zpkg.lock`.
3. Run `Zed: Show Package Insights`.

The source includes `.python-version` set to `3.8` so supported Sublime Text 4
builds use the compatible plugin environment while newer builds can map that
selector to their current Python host.

## Configuration

Edit `ZedPackageInsights.sublime-settings` through Package Settings. The most
important option is:

```json
{
  "zed_binary": "/absolute/path/to/zed"
}
```

An absolute path is strongly recommended when the Zed editor launcher is also
installed under the name `zed`.

## Architecture

```text
Sublime commands/events
        |
        v
background analyzer -----> local files (.zpkg.toml, .zpkg.lock, .zpkg-staging)
        |
        +-----------------> zed --version / zed --help
        |
        v
snapshot + diagnostics + declarative recommended actions
        |
        v
output panel / status bar / confirmation-gated action runner
```

The proposed common CLI contract for every editor integration is documented in
[`docs/DIAGNOSTICS-PROTOCOL.md`](docs/DIAGNOSTICS-PROTOCOL.md). Until the CLI
ships that endpoint, this plugin performs the deterministic local subset. The CLI work is tracked in [`zed-cli#191`](https://github.com/zed-pkg/zed-cli/issues/191).

## Development

```sh
python -m unittest discover -s tests -v
python -m compileall -q zed_pkg_insights zed_sublimetext.py
```

No runtime PyPI dependencies are required.

## Publishing the repository

With an authenticated GitHub CLI that can create repositories in `zed-pkg`:

```sh
./scripts/publish-repository.sh
```

The script creates the public `zed-pkg/zed-sublimetext` repository and pushes
`main`. It refuses to overwrite an existing remote.

## License

MIT
