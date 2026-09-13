# Skillworks

## Agent skills

### Issue tracker

GitHub Issues, driven by the `gh` CLI. A spec is a parent issue; its tickets are its sub-issues. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Working in this repo

Commit straight to `main` and push. No branches, no pull requests.

### The Aspire CLI

Installed, as `aspire.cmd`. Git Bash will not find it from the bare name `aspire` — run it from
PowerShell, or spell it `aspire.cmd` in Bash. `aspire --version` failing in Bash does not mean it is
missing.
