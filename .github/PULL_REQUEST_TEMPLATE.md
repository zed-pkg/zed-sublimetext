## What changed

## Why

## Safety impact

- [ ] Background inspection remains non-mutating.
- [ ] No shell strings are executed.
- [ ] Project mutations still require explicit confirmation.
- [ ] CLI output is redacted before display.

## Validation

- [ ] `python -m unittest discover -s tests -v`
- [ ] `python -m compileall -q zed_pkg_insights zed_sublimetext.py`
- [ ] Manual Sublime Text smoke test, when UI behavior changed
