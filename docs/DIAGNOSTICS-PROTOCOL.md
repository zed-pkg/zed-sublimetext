# Zed IDE diagnostics protocol

The Sublime plugin works today without a special CLI endpoint by checking the
manifest, lockfile, configured dependency directory, interrupted transaction
state, and the identity of the configured `zed` executable.

A shared machine-readable protocol is still the preferred long-term boundary
for Sublime Text, VS Code, IntelliJ, JetBrains Air, and other editor clients.
Implementation is tracked in https://github.com/zed-pkg/zed-cli/issues/191.
The proposed CLI surface is:

```sh
zed inspect --format json --root /absolute/project/root
```

## Protocol rules

- stdout contains exactly one UTF-8 JSON document; progress and logs go to stderr.
- inspection is credential-free and non-mutating.
- the command does not download packages, execute build hooks, repair state, or
  contact a registry unless an explicit network flag is added.
- paths are absolute or explicitly rooted.
- every suggested action is declarative. An editor must independently decide
  whether to display, copy, or execute it.
- commands are argument arrays, never shell strings.
- secrets and bearer tokens never appear in either stream.
- schema versions are additive within a major version.

## Proposed schema

```json
{
  "schema_version": "1.0",
  "root": "/work/project",
  "package": {
    "manifest": "/work/project/.zpkg.toml",
    "lockfile": "/work/project/.zpkg.lock",
    "materialization_dir": "/work/project/zed_modules"
  },
  "summary": {
    "health": "warning",
    "errors": 0,
    "warnings": 1
  },
  "diagnostics": [
    {
      "code": "LOCK_STALE",
      "severity": "warning",
      "message": "Manifest intent is newer than the lockfile",
      "detail": "Resolve again before using frozen mode",
      "location": {
        "path": "/work/project/.zpkg.toml",
        "line": 12,
        "column": 1
      },
      "actions": [
        {
          "id": "refresh-lock",
          "title": "Refresh the lockfile",
          "kind": "zed-command",
          "argv": ["zed", "install"],
          "mutates_project": true,
          "requires_network": true,
          "executes_package_code": false
        }
      ]
    }
  ]
}
```

## Editor safety policy

The plugin must not trust an action merely because it came from the CLI. It
must enforce all of the following:

1. only known action kinds are accepted;
2. command arrays begin with the configured Zed executable;
3. shell metacharacters have no special meaning because `shell=false` is used;
4. every project mutation requires explicit confirmation;
5. actions that execute package-authored build hooks require a stronger warning;
6. output is redacted before display;
7. no action is run during background refresh.
