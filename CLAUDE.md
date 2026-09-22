# Skillworks

## Agent skills

### Issue tracker

GitHub Issues, driven by the `gh` CLI. A spec is a parent issue; its tickets are its sub-issues. See `docs/agents/issue-tracker.md`.

### Domain docs

Multi-context: `CONTEXT-MAP.md` and `docs/adr/` at the repo root, and one `CONTEXT.md` per context.
See `docs/agents/domain.md`.

## Working in this repo

Commit straight to `main` and push. No branches, no pull requests.

### Checks

Docker has to be running, because the API tests start Loki in a container. `uv` has to be on PATH,
because the script tests are Python and carry no project file. The front-end checks run from
`src/Skillworks.Studio.Web`, so they use the local tools and not anything installed globally.

```
dotnet test Skillworks.slnx
uv run --with pytest pytest tests/scripts
cd src/Skillworks.Studio.Web && npm run typecheck && npm run lint && npm test
```

`README.md` has the rest, under Checks.

### The Aspire CLI

Installed, as `aspire.cmd`. Git Bash will not find it from the bare name `aspire` — run it from
PowerShell, or spell it `aspire.cmd` in Bash. `aspire --version` failing in Bash does not mean it is
missing.
