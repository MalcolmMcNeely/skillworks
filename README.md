# Skillworks

Tools for building, testing and watching Claude Code agent skills.

Three parts are planned:

- **Plugins** — a shipped catalogue of agent skills, installed as a Claude Code plugin marketplace.
- **MCP server** — C#, exposing the catalogue and its telemetry to an agent.
- **Reader** — React, for reading skill telemetry and, later, for authoring and testing a skill by hand.

Nothing is built yet. The research behind it lives in
[skills-marketplace](https://github.com/MalcolmMcNeely/skills-marketplace).

## Repo layout

| Path | What it is |
|---|---|
| `.claude/skills/` | Dev tooling used while working in this repo. Vendored, not shipped. |

## Licence

Apache 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

The skills under `.claude/skills/` are vendored from other projects and stay MIT.
See [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
