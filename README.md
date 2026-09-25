# Skillworks

Skillworks is a proof of concept. It is an app an organisation runs to manage the Claude Code
skills its developers use.

The app is called Studio. It has four jobs, in this order:

1. **Dashboard.** Read the organisation's Claude Code telemetry. See which skills fire, how often, in
   which repositories, and what they cost.
2. **Author.** Write a skill and its evals.
3. **Test.** Run the evals before anyone else gets the skill.
4. **Publish.** Ship the skills to the organisation as a Claude Code plugin.

Then it goes round again. Once the plugin is out, the telemetry shows whether its skills fire.

| Job | Built? |
|---|---|
| Dashboard | Yes. The Dashboard lists every skill with its Activations, Cost, Tokens, Models, Efforts and Repositories. |
| Author | Not yet. |
| Test | Not yet. |
| Publish | Not yet. |

The words this README uses, such as Activation and Events store, are defined in
[CONTEXT.md](CONTEXT.md). The decisions so far are in [docs/adr/](docs/adr/), and the research
behind them is in [docs/research/](docs/research/).

## What each job will do

**Author.** Studio writes a skill's folder and its evals to disk, as plugin files Claude Code can
load.

**Test.** Studio runs two kinds of eval. A Firing eval checks that a skill fires on the prompts it
should, and stays quiet on the rest. It is cheap, and every skill Claude picks up on its own gets
one. An Outcome eval checks what a skill produces after it fires. It costs more, so only a skill
that promises something a test can check gets one.

**Publish.** A Claude Code plugin marketplace is a git repository. Studio puts the tested plugin in
the organisation's marketplace, and each developer's Claude Code installs it from there.

## Why Studio runs on your machine

Authoring writes files, and an eval starts `claude`. A hosted service can do neither, so each
developer runs their own Studio.

The numbers still come from one place. Studio reads them from the organisation's Events store, not
from the machine it runs on, so every developer's Studio shows the same numbers.

## Running Studio

You need these on your machine:

- the .NET 10 SDK
- Node 20 or later
- the Aspire CLI
- Docker, running

Then, from the repo root:

```
aspire run
```

In Git Bash, type `aspire.cmd run`. Git Bash does not find the bare name `aspire`.

That starts the API, the front end, an OpenTelemetry Collector and Loki. It prints the address of
Aspire's own dashboard, and the front end is the `web` resource there. The Collector and Loki run
as Docker containers. Aspire runs `npm install` and `npm run dev` for the front end, and hands it
the API's address, so there is no port to look up.

### Where Studio's numbers come from

Studio reads everything it measures from the Events store, a Loki that Claude Code's telemetry
reaches. It never reads the transcripts Claude Code writes to `~/.claude/projects`, and it keeps no
database.

In an organisation, the Events store is the organisation's Loki. Until one exists, the AppHost's
Collector and Loki stand in for it, and Studio shows only what this machine sent.

Studio finds the Events store and the Marketplace through these settings:

| Setting | What it does | Default |
|---|---|---|
| `Loki__Address` | Where Studio reads Loki. The AppHost sets it to its own Loki. | `http://localhost:3100` |
| `Loki__Tenant` | Sent as `X-Scope-OrgID`, for a Loki with several tenants. | Not sent |
| `Loki__LookbackDays` | The lookback: how many days a list covers when the Filter has no start day. | `7` |
| `Loki__MaxQueryDays` | The most days one Loki query may cover. Studio splits a longer span. | `30` |
| `Marketplace__Path` | The Marketplace folder. Studio reads the skill names of every plugin in it, so a skill that never fired still shows, with zero Activations. The AppHost sets it to `plugins/` in this repo. | `plugins` |

### What telemetry cannot tell you

A plugin from the organisation's own marketplace is a third-party plugin to Claude Code. Its
Activations arrive with the skill's real name. Its spend does not. On each request made while one of
its skills is in force, Claude Code sends the skill name as `third-party`, and no setting changes
that. Studio shows that spend as one
amount, Unnamed spend, and never splits it among skills.

### The telemetry switch

Claude Code sends nothing until telemetry is on. The Telemetry switch, on the rail of Studio's first
page, turns it on for this machine. Before it acts it says in plain words what will be recorded: what
you type, what Claude Code writes back, what every tool was handed and what it returned, and how long
each step took. Everyone who can read the organisation's stores can read all of it. The switch writes
only when you say so.

It writes these to the `env` block of `~/.claude/settings.json`, all of them or none:

| Variable | Value | What it brings |
|---|---|---|
| `CLAUDE_CODE_ENABLE_TELEMETRY` | `1` | Nothing at all is sent without this one |
| `OTEL_LOGS_EXPORTER` | `otlp` | The events |
| `OTEL_LOG_TOOL_DETAILS` | `1` | A skill's real name, not `custom_skill` |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` | |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | The Collector, `http://localhost:4318` | |
| `OTEL_METRICS_INCLUDE_REPOSITORY` | `true` | The Repository on every event |
| `OTEL_LOG_USER_PROMPTS` | `1` | What you typed, not `<REDACTED>` |
| `OTEL_LOG_ASSISTANT_RESPONSES` | `1` | What Claude Code answered |
| `OTEL_LOG_TOOL_CONTENT` | `1` | What a tool was handed and returned |
| `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA` | `1` | Spans, which are beta |
| `OTEL_TRACES_EXPORTER` | `otlp` | The Spans, to the Trace store |

The switch says telemetry is on only when all eleven hold these values, because a Session recorded
with some of them cannot be read in full. Turning it off puts back what was there before. A Claude
Code session that is already running picks up neither change, so restart it.

The switch writes this machine and no other, and never a repository file. Beside the switch, Studio
shows the `.claude/settings.json` a team would commit to switch everyone on. It is text on a page:
Studio does not commit it, because that decision belongs in review.

The repository variable, `OTEL_METRICS_INCLUDE_REPOSITORY`, reaches past metrics despite its name.
It names the session's `origin` remote on every event, and Studio shows that as a Repository,
`owner/name`. Claude Code 2.1.269 is the first version that sends a Repository. An older Claude
Code, or a session with no `origin` remote, sends none, and Studio shows the Repository as not
recorded.

### What each Session was given

The Plugin's `SessionStart` and `InstructionsLoaded` hooks, in
`plugins/skillworks/hooks/hooks.json`, run `plugins/skillworks/scripts/session-watch.mjs`, so every
repo with the Plugin records its Loads.
`SessionStart` posts one record for each Session, with how it began. `InstructionsLoaded` posts one
Load for each instruction file that reaches it. Both go to `OTEL_EXPORTER_OTLP_ENDPOINT`, and both
carry the Session's `session.id`, so one Loki query reads them beside Claude Code's own events.
With `OTEL_METRICS_INCLUDE_REPOSITORY` on, both also carry the Repository as `vcs.owner.name` and
`vcs.repository.name`, read from the `origin` remote the way Claude Code reads it, so a query
filtered by Repository finds them too. With the switch off, or no `origin` to read, the Repository
is left off and the record still goes. A Session record with no Loads after it says the Rules did
not arrive. No records at all says the Collector was not there.

A hook that fails is silent. Its exit code and its errors reach no one, so the watcher can stop
watching and nothing says so. To see a hook fail, run `claude --debug hooks`.

### Which Session made a commit

Every commit a Session makes names that Session. The Plugin's `PreToolUse` hook adds a
`Skillworks-Session: <id>` trailer to each `git commit` Claude runs through the Bash or PowerShell
tool, whether telemetry is on or off, and the spec loop adds one to the commit it makes when it keeps
a stopped run's work. The id is the Session's `session.id`. Read a commit's Sessions back with:

```
git log -1 <commit> --format='%(trailers:key=Skillworks-Session,valueonly)'
```

Take the id to the Stores, or to `claude --resume <id>` on the machine that made the commit.
A commit you make by hand, outside Claude, carries no trailer.

### Studio on a seeded month

To judge a screen at real volume without your own telemetry, run Studio against a throwaway Loki.
Docker must be running. The tool runs the front end from its `node_modules`, so run `npm install` in
`src/Skillworks.Studio.Web` once first. Then, from the repo root:

```
node tools/seeded-studio.mjs
```

It starts a Loki container, `skillworks-seeded-loki`, on port 3101. It fills it with a made-up month
of telemetry that ends now. Then it runs the API on port 5199 and the front end on port 5173, both
pointed at that Loki. Open `http://localhost:5173/`. Ctrl+C stops all three and removes the
container, and the seeded events with it.

To seed the Loki and nothing else, add `--seed-only`. The container keeps running after the tool
exits. Remove it with `docker rm -f skillworks-seeded-loki`.

The tool never touches the AppHost's Loki, so your real telemetry stays as it is.

### Checks

`docs/agents/suite.json` is the Suite file. It lists these checks in order, with the folder each one
runs in and what must be ready first. The loop runs the checks it names and nothing else, so a check
added here goes in that file too. Its `runs` is 2, because the container-backed Span tests flake here,
so the loop runs a red Suite a second time before it believes it.

The API tests start Loki in a container, so Docker must be running. Run the front-end checks from
`src/Skillworks.Studio.Web`, so they use the local tools and not anything installed globally. The
loop's scripts live in the Plugin, at `plugins/skillworks/scripts/`, and their tests sit at the same
path under `tests/`. The script tests build a throwaway repository in a temporary directory and touch
nothing else. The scripts are Python, so `uv` has to be on PATH for their tests to run. pytest is
asked for on the command line, because the scripts carry no project file. The hook script that
records each Load is node, and its tests sit beside the script tests and use the test runner built
into node, so they add no dependency. node expands the quoted pattern itself:

```
dotnet test Skillworks.slnx

uv run --with pytest pytest tests/plugins/skillworks/scripts

node --test "tests/plugins/skillworks/scripts/**/*.test.mjs"

cd src/Skillworks.Studio.Web
npm run typecheck
npm run lint
npm test
```

The script tests come in two sets, told apart by one flag on the same path. The command above runs
the fast set, which answers for `gh` and `claude` through the Runner, so it needs neither installed
and starts no model session. It is the set a landing runs, so landing is never gated on a login.

The other set starts the real `gh` and the real `claude`, far enough to prove each one accepts the
argument lines the driver builds for it and no further. It also starts `claude` with the Plugin, to
prove the Plugin forces its output style and resolves a `skillworks:` skill. That session asks for a
model the API does not offer, so no model answers. One more session, on Haiku, makes a commit in a
throwaway repository, to prove the Plugin's hook names the Session in it. That is the one model
session the set starts. It needs both programs on PATH. It changes no issue, and it takes under a
minute:

```
uv run --with pytest pytest tests/plugins/skillworks/scripts --real-binaries
```

A session waits ten minutes on a command before it gives up, rather than the two minutes it would
otherwise. `.claude/settings.json` sets that. The script suite took 184, 299, 321 and 413 seconds
across four runs of the same tests on this machine, and the spread is machine load, so two minutes
loses the result and a session has to run the suite in the background and poll it instead. The wait
is a ceiling and never a delay, so a run that takes three minutes still answers in three.

This does not reach the loop itself, which runs for hours and still has to be started in the
background.

## Repo layout

| Path | What it is |
|---|---|
| `src/Skillworks.Core/` | The domain. No HTTP. The API is a thin shell over it. |
| `src/Skillworks.Studio.Api/` | The ASP.NET Core shell. HTTP and nothing else. |
| `src/Skillworks.Studio.Web/` | The React front end. Renders what the API shaped. Any rule of its own lives in a `lib` folder, such as `src/dashboard/lib/`, with a test beside it. |
| `src/Skillworks.AppHost/` | The Aspire orchestrator. One command starts everything. |
| `src/Skillworks.ServiceDefaults/` | Aspire's shared health, telemetry and service discovery setup. |
| `src/Skillworks.Architecture/` | The architecture check. Reads the rules files in `.claude/rules/` and lists the places the code breaks them. |
| `tests/Skillworks.Studio.Api.Tests/` | The real API in memory, against a real Loki, asserting the JSON it returns. |
| `tests/Skillworks.Architecture.Tests/` | The architecture check on small folder trees, and on this repo. |
| `tests/plugins/skillworks/scripts/` | The Plugin's scripts, run against a throwaway repository. |
| `plugins/` | The local Marketplace. It holds the one Plugin, `skillworks`, and this repo loads its skills from there. Studio reads it by default. |
| `plugins/skillworks/scripts/` | The loop's scripts: the driver, the landing, the worktrees, the Suite, the preflight, and the hook script that records each Load. They read the repo from the git top level of the folder they start in, never from where the Plugin sits. |
| `plugins/skillworks/hooks/` | The Plugin's hooks. They run the hook script on `SessionStart` and `InstructionsLoaded`, and do nothing unless telemetry is on. |
| `plugins/skillworks/bin/` | The short commands the Plugin puts on PATH: `spec-loop`, `land-ticket`, `ticket-worktree`, `skillworks-preflight` and `seed-steering`. Each runs its script from the Plugin. |
| `.claude/skills/` | The skills that are not in the Plugin. Dev tooling for this repo, mostly vendored. |
| `tools/` | Dev tools you run by hand, such as `seeded-studio.mjs`. |
| `docs/agents/` | Reference text more than one skill reads. `/skillworks:skillworks-setup` seeds a starting version of each, and of the rules, in a repo that has none. This repo's copies are its own. |
| `docs/agents/suite.json` | The Suite file: the checks that decide green for this repo, in order, each with its folder and what must be ready first. The loop runs these and nothing else. |
| `docs/agentic-development/` | How the dev loop works, for a human reading it rather than a skill. |

### How much of Studio is Shared

The top folder under a code root is a Slice, named for a job Studio does, with `Shared` beside the
Slices for the code no one job owns. `.claude/rules/file-placement.md` holds the rules, and
[ADR 0017](docs/adr/0017-a-slice-is-named-for-a-job-studio-does.md) says why the line is drawn there
and why `Shared` is close to half.

Counted on 19 September 2026. The count covers three code roots — `Skillworks.Core`,
`Skillworks.Studio.Api` and the front end's `src` — and code files only, so no test and nothing
generated. Studio's test projects lay out in Slices too, and are left out on purpose.

| Folder | Files | Share |
|---|---|---|
| `Dashboard` | 33 | 15% |
| `Sessions` | 82 | 38% |
| `Shared` | 103 | 47% |

Recount when a job lands. Watch the ratio rather than worry about it: if `Shared` keeps growing
faster than the Slices as Author, Test and Publish arrive, the Slice boundary is in the wrong place,
and the answer is to redraw it rather than to push code out of `Shared`.

## Working on Skillworks

### Setup

You need three things on your machine:

- `gh`, logged in. Check with `gh auth status`.
- `claude` on your `PATH`
- an `origin` remote pointing at GitHub

Then, in Claude Code:

```
/skillworks:skillworks-setup
```

Run it once per clone. Run it again any time to repair.

It creates the `ready-for-agent` label, seeds the Steering (the rules, `docs/agents/` and a starting
Suite file) where it is missing, points `CLAUDE.md` at it, enables the Plugin, and installs the
permission allowlist the loop needs to run unattended. It never overwrites a file you have edited: it
shows you the difference instead.

### The dev loop

Two stages, and two commands. A human drives the first. A script drives the second.

```
/skillworks:grill-with-docs        argue the design out, and publish the spec
/skillworks:spec-loop <spec#>      build it, ticket by ticket, unattended
```

[docs/agentic-development/agentic-loop.md](docs/agentic-development/agentic-loop.md) explains what
each one does.

Lost? `/skillworks:what-next` looks at where you are and tells you which skill fits.

## Licence

Apache 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

Most skills under `plugins/skillworks/skills/` and `.claude/skills/` are vendored from other projects and stay MIT.
See [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) for which are ours and which are theirs.
