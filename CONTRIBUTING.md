# Contributing

## Principles

- keep background inspection non-mutating;
- never execute shell strings;
- require explicit confirmation for project mutations;
- keep core analysis independent of Sublime so it remains unit-testable;
- add a diagnostic code and regression test for every new state rule;
- prefer the shared CLI diagnostics protocol over editor-specific package logic.

## Checks

```sh
python -m unittest discover -s tests -v
python -m compileall -q zed_pkg_insights zed_sublimetext.py
```

When Sublime API behavior changes, test manually on the oldest supported build
and the current stable build.
