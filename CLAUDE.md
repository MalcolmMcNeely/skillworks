# Skillworks

## Agent skills

### Issue tracker

GitHub Issues, driven by the `gh` CLI. A spec is a parent issue; its tickets are its sub-issues. See `docs/agents/issue-tracker.md`.

### Domain docs

Multi-context: `CONTEXT-MAP.md` and `docs/adr/` at the repo root, and one `CONTEXT.md` per context.
See `docs/agents/domain.md`.

### Rules

The rules load into every session through these imports. Each one lives in `docs/agents/rules/`.

@docs/agents/rules/comments.md
@docs/agents/rules/determinism.md
@docs/agents/rules/file-placement.md
@docs/agents/rules/words.md

## Working in this repo

Commit straight to `main` and push. No branches, no pull requests.

### Checks

Run the checks with the Plugin's command, and not with the test commands one by one:

```
skillworks-suite
```

It runs every check in `docs/agents/suite.json` and keeps a Proof of each one that passes. A check
whose inputs match a Proof does not run again, so a second run after a small change is cheap.
In a loop the driver runs the Suite as a step of its own, and it reads the Proofs your run kept.

Docker has to be running, because the API tests start Loki in a container and the script tests run
in a Linux image. `uv` has to be on PATH, because the command is Python.

`README.md` has the rest, under Checks.

### The Aspire CLI

Installed, as `aspire.cmd`. Git Bash will not find it from the bare name `aspire` — run it from
PowerShell, or spell it `aspire.cmd` in Bash. `aspire --version` failing in Bash does not mean it is
missing.
