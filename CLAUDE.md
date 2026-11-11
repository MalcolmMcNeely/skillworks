# Skillworks

## Agent skills

### Issue tracker

GitHub Issues, driven by the `gh` CLI. A spec is a parent issue; its tickets are its sub-issues. See `docs/skillworks/issue-tracker.md`.

### Domain docs

Multi-context: `CONTEXT-MAP.md` and `docs/adr/` at the repo root, and one `CONTEXT.md` per context.
See `docs/skillworks/domain.md`.

### Rules

The rules load into every session through these imports. Each one lives in `docs/skillworks/rules/`.

@docs/skillworks/rules/comments.md
@docs/skillworks/rules/determinism.md
@docs/skillworks/rules/file-placement.md
@docs/skillworks/rules/testing.md
@docs/skillworks/rules/words.md

## Working in this repo

Commit straight to `main` and push. No branches, no pull requests.

### Checks

Run the checks with the Plugin's command, and not with the test commands one by one:

```
skillworks-suite
```

It runs every check in `docs/skillworks/suite.json` and keeps a Proof of each one that passes. A check
whose inputs match a Proof does not run again, so a second run after a small change is cheap.
In a loop the driver runs the Suite as a step of its own, and it reads the Proofs your run kept.

Docker has to be running, because the API tests start Loki in a container and the script tests run
in a Linux image. `uv` has to be on PATH, because the command is Python.

`docs/CONTRIBUTING.md` has the rest, under Checks.

### Changing a Plugin skill

The tests and the driver match the exact text of a Plugin skill. Before you change a file under
`plugins/skillworks/skills/`, read `docs/CONTRIBUTING.md`, under Changing a Plugin skill.

### After a Plugin change Lands

When a change to the Plugin Lands on `main`, quit and restart every running Claude Code Session
before you type a Plugin command. A Claude Code process keeps the skill text it loaded when it
started, so a Session that started before the change serves the old skills. `/clear` is not enough,
because it does not reload them.

### The Aspire CLI

Installed, as `aspire.cmd`. Git Bash will not find it from the bare name `aspire` — run it from
PowerShell, or spell it `aspire.cmd` in Bash. `aspire --version` failing in Bash does not mean it is
missing.
