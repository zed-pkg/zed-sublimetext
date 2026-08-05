# Security policy

Report vulnerabilities privately through GitHub Security Advisories after the
repository is published.

## Threat model

This plugin opens untrusted projects and may display output from a local CLI.
Accordingly:

- background scans never mutate the project;
- subprocesses use argument arrays with `shell=false`;
- recommended actions come from an internal allowlisted model;
- every lifecycle mutation requires user confirmation;
- package build hooks are not invoked by automatic checks;
- subprocess output is redacted before display;
- no registry token is passed on the command line;
- the future JSON diagnostics protocol is treated as untrusted input.

Do not include credentials, access tokens, private registry URLs with embedded
credentials, or proprietary manifests in a public issue.
