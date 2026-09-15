# Skillworks

Tools for building, testing and watching Claude Code agent skills.

Three parts are planned:

- **Catalogue** — the plugins we ship: skills, hooks, output styles and MCP servers, installed as a Claude Code plugin marketplace.
- **MCP server** — C#, exposing the catalogue and its telemetry to an agent.
- **Studio** — a local app for watching skill telemetry, authoring the catalogue, and running evals. React over an ASP.NET Core API, started by Aspire.

Studio reads Claude Code's telemetry from the Events store and shows which skills fired, how often,
where, and what they cost. The vocabulary is in [CONTEXT.md](CONTEXT.md), the decisions so far in
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

It creates the `ready-for-agent` label, writes `docs/agents/`, points `CLAUDE.md` at it, installs the permission allowlist the loop needs to run unattended, and sets the `skillworks` output style. It asks before it overwrites anything you have edited.

Then go to [the dev loop](#the-dev-loop).

## Running Studio

You need the .NET 10 SDK, Node 20 or later, the Aspire CLI, and Docker running. Then, from the repo
root:

```
aspire run
```

That starts the API, the front end, an OpenTelemetry Collector and Loki, and prints the address of
Aspire's own dashboard. The Collector and Loki run as Docker containers. Aspire runs `npm install`
and `npm run dev` for the front end itself, and hands it the API's address, so there is no port to
look up.

### Where Studio's numbers come from

Studio reads everything it measures from the Events store, a Loki that Claude Code's telemetry
reaches. It never reads the transcripts Claude Code writes to `~/.claude/projects`, and it keeps no
database. In an organisation the Events store is the organisation's Loki, so every developer's
Studio shows the same numbers. Until one exists, the AppHost's Collector and Loki stand in for it,
and Studio shows only what this machine sent.

Studio finds the Events store through these settings:

| Setting | What it does | Default |
|---|---|---|
| `Loki__Address` | Where Studio reads Loki. The AppHost sets it to its own Loki. | `http://localhost:3100` |
| `Loki__Tenant` | Sent as `X-Scope-OrgID`, for a Loki with several tenants. | Not sent |
| `Loki__LookbackDays` | The lookback: how many days a list covers when the Filter has no start day. | `7` |
| `Loki__MaxQueryDays` | The most days one Loki query may cover. Studio splits a longer span. | `30` |

### The telemetry switch

Claude Code sends nothing until telemetry is on. The Telemetry panel, at the foot of Studio's first
page, turns it on for this machine. It lists what it will write to the `env` block of `~/.claude/settings.json`, and writes
only when you say so:

| Variable | Value |
|---|---|
| `CLAUDE_CODE_ENABLE_TELEMETRY` | `1` |
| `OTEL_LOGS_EXPORTER` | `otlp` |
| `OTEL_LOG_TOOL_DETAILS` | `1` |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | The Collector, `http://localhost:4318` |
| `OTEL_METRICS_INCLUDE_REPOSITORY` | `true` |

The panel says telemetry is on only when all six hold these values. Turning it off puts back what
was there before. A Claude Code session that is already running picks up neither change, so restart
it.

The repository variable, `OTEL_METRICS_INCLUDE_REPOSITORY`, reaches past metrics despite its name.
It names the session's `origin` remote on every event, and Studio shows that as a Repository,
`owner/name`. Claude Code 2.1.269 is the first version that sends a Repository. An older Claude
Code, or a session with no `origin` remote, sends none, and Studio shows the Repository as not
recorded.

### Checks

The API tests start Loki in a container, so Docker must be running. The front-end ones must run
from `src/Skillworks.Studio.Web`, so they pick up the local tools rather than anything installed
globally:

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
| `src/Skillworks.Studio.Web/` | The React front end. Renders what the API shaped; any rule of its own lives in a `lib` folder, such as `src/skills/lib/`, with a test beside it. |
| `src/Skillworks.AppHost/` | The Aspire orchestrator. One command starts everything. |
| `src/Skillworks.ServiceDefaults/` | Aspire's shared health, telemetry and service-discovery setup. |
| `src/Skillworks.Architecture/` | The architecture check. Reads the rules files in `.claude/rules/` and lists the places the code breaks the rules it checks. |
| `tests/Skillworks.Studio.Api.Tests/` | The real API in memory, against a real Loki, asserting the JSON it returns. |
| `tests/Skillworks.Architecture.Tests/` | The architecture check on small folder trees, and on this repo. |
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
