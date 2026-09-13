# Skillworks

Tools for building, testing and watching Claude Code agent skills.

Three parts are planned:

- **Catalogue** — the plugins we ship: skills, hooks, output styles and MCP servers, installed as a Claude Code plugin marketplace.
- **MCP server** — C#, exposing the catalogue and its telemetry to an agent.
- **Studio** — a local app for watching skill telemetry, authoring the catalogue, and running evals. React over an ASP.NET Core API, started by Aspire.

Studio reads the transcripts Claude Code already writes and shows which skills fired, how often,
and where. The vocabulary is in [CONTEXT.md](CONTEXT.md), the decisions so far in
[docs/adr/](docs/adr/), and the research behind it in
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

## Running Studio

You need the .NET 10 SDK, Node 20 or later, and the Aspire CLI. Then, from the repo root:

```
aspire run
```

That starts the API and the front end together, and prints the address of Aspire's own dashboard.
Aspire runs `npm install` and `npm run dev` for the front end itself, and hands it the API's
address, so there is no port to look up.

Studio finds your transcripts in `~/.claude/projects` on its own, and parses them into SQLite under
your local application data. The first pass runs in the background, so the app is usable while it
reads; later passes read only what changed. Set `Transcripts__Path` to read from somewhere else.

Checks. The front-end ones must run from `src/Skillworks.Studio.Web`, so they pick up the local
tools rather than anything installed globally:

```
dotnet test Skillworks.slnx

cd src/Skillworks.Studio.Web
npm run typecheck
npm run lint
npm test
```

## Repo layout

| Path | What it is |
|---|---|
| `src/Skillworks.Core/` | The domain. No HTTP. The API and the planned MCP server are both shells over it. |
| `src/Skillworks.Studio.Api/` | The ASP.NET Core shell. HTTP and nothing else. |
| `src/Skillworks.Studio.Web/` | The React front end. Renders what the API shaped; any rule of its own lives in `src/lib/` with a test beside it. |
| `src/Skillworks.AppHost/` | The Aspire orchestrator. One command starts everything. |
| `src/Skillworks.ServiceDefaults/` | Aspire's shared health, telemetry and service-discovery setup. |
| `tests/` | The one test seam: the real API in memory, asserting the JSON it returns. |
| `plugins/` | Where the catalogue will live. See [ADR 0003](docs/adr/0003-catalogue-lives-here-until-it-is-published.md). |
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
                                         commit, close ticket, next
                          └─ at the end: /spec-drift against the spec, then ONE push
```

The tickets are GitHub **sub-issues of the spec**. The driver reads one spec's children and nothing else, so two people running the loop on two specs never take each other's work.

The script picks the next ticket, never the model. Control flow you can read, stop and resume beats control flow inside a context window.

Lost? `/what-next` is a router over every skill here and tells you which one fits your situation.

## Licence

Apache 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

Most skills under `.claude/skills/` are vendored from other projects and stay MIT.
See [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) for which are ours and which are theirs.
