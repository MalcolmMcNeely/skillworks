# Skillworks

Tools for building, testing and watching Claude Code agent skills.

Three parts are planned:

- **Plugins** — a shipped catalogue of agent skills, installed as a Claude Code plugin marketplace.
- **MCP server** — C#, exposing the catalogue and its telemetry to an agent.
- **Reader** — React, for reading skill telemetry and, later, for authoring and testing a skill by hand.

Nothing is built yet. The research behind it lives in
[skills-marketplace](https://github.com/MalcolmMcNeely/skills-marketplace).

## Getting started

You need three things on your machine:

- `gh`, logged in — check with `gh auth status`
- `claude` on your `PATH`
- an `origin` remote pointing at GitHub

Then, in Claude Code:

```
/skillworks-setup
```

That is the whole setup. One command, once per repo. Run it again any time to repair.

It creates the `ready-for-agent` label, writes `docs/agents/`, points `CLAUDE.md` at it, and installs the permission allowlist the loop needs to run unattended. It asks before it overwrites anything you have edited.

Then go to [the dev loop](#the-dev-loop).

## Repo layout

| Path | What it is |
|---|---|
| `.claude/skills/` | Dev tooling used while working in this repo. Mostly vendored, not shipped. |
| `scripts/` | Drivers the skills shell out to. Not meant to be run by hand. |
| `docs/agents/` | Written by `/skillworks-setup`. The tracker, label and domain-doc references the skills read. |

## The dev loop

Two stages. A human drives the first. A script drives the second.

```
/grill-with-docs        argue it out; CONTEXT.md and ADRs get written
/to-spec                a SPEC: issue on GitHub; docs committed and pushed
/spec-loop <spec#>      /to-tickets, then scripts/spec-loop.sh takes over
                          └─ per ticket: fresh `claude -p "/implement <n>"`
                                         commit, push, close, next
                          └─ at the end: /spec-drift against the spec
```

The tickets are GitHub **sub-issues of the spec**. The driver reads one spec's children and nothing else, so two people running the loop on two specs never take each other's work.

The script picks the next ticket, never the model. Control flow you can read, stop and resume beats control flow inside a context window.

Lost? `/what-next` is a router over every skill here and tells you which one fits your situation.

## Licence

Apache 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

Most skills under `.claude/skills/` are vendored from other projects and stay MIT.
See [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) for which are ours and which are theirs.
