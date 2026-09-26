# Skillworks

Skillworks is an app an organisation runs to manage the Claude Code skills its developers use.

The app is called Studio. It has four jobs, in this order:

1. **Dashboard.** Read the organisation's Claude Code telemetry. See which skills fire, how often, in
   which repositories, and what they cost.
2. **Author.** Write a skill and its evals.
3. **Test.** Run the evals before anyone else gets the skill.
4. **Publish.** Ship the skills to the organisation as a Claude Code plugin.

Then it goes round again. Once the plugin is out, the telemetry shows whether its skills fire.

Beside the four jobs, **Sessions** shows each run of Claude Code: what it was given, and what it did,
step by step.

| Job | Built? |
|---|---|
| Dashboard | Yes. The Dashboard lists every skill with its Activations, Cost, Tokens, Models, Efforts and Repositories. |
| Sessions | Yes. Sessions lists each Session, and opens one to show its Exchanges, Steps and Findings. |
| Author | Not yet. |
| Test | Not yet. |
| Publish | Not yet. |

The words this README uses, such as Activation and Events store, are defined in
[CONTEXT.md](CONTEXT.md). The decisions so far are in [docs/adr/](docs/adr/), and the research
behind them is in [docs/research/](docs/research/).

## What each job will do

**Author.** Studio writes a skill's folder and its evals to disk, as plugin files Claude Code can
load.

**Test.** Studio runs two kinds of eval. An Activation eval checks that a skill fires on the prompts
it should, and stays quiet on the rest. It is cheap, and every skill Claude picks up on its own gets
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

### Turn telemetry on

Studio reads its numbers from Loki, and Claude Code sends nothing until telemetry is on. Use the
Telemetry switch on the rail of Studio's first page. It writes eleven variables to the `env` block
of `~/.claude/settings.json`. Restart any Claude Code session that is already running.

The switch records what you type and what Claude Code answers.
[docs/studio/telemetry.md](docs/studio/telemetry.md) lists each variable, says what telemetry
cannot tell you, and says how the Plugin's hooks record each Session.

### Settings

Studio finds the Events store and the Marketplace through these settings:

| Setting | What it does | Default |
|---|---|---|
| `Loki__Address` | Where Studio reads Loki. The AppHost sets it to its own Loki. | `http://localhost:3100` |
| `Loki__Tenant` | Sent as `X-Scope-OrgID`, for a Loki with several tenants. | Not sent |
| `Loki__PatienceSeconds` | How long Studio waits on Loki before it shows a Gap. | `5` |
| `Loki__LookbackDays` | The lookback: how many days a list covers when the Filter has no start day. | `7` |
| `Loki__MaxQueryDays` | The most days one Loki query may cover. Studio splits a longer span. | `30` |
| `Marketplace__Path` | The Marketplace folder. Studio reads the skill names of every plugin in it, so a skill that never fired still shows, with zero Activations. The AppHost sets it to `plugins/` in this repo. | `plugins` |

### Studio on a seeded month

To judge a screen at real volume without your own telemetry, run Studio against a throwaway Loki.
Docker must be running. Run `npm install` in `src/Skillworks.Studio.Web` once first. Then, from the
repo root:

```
node tools/seeded-studio.mjs
```

Open `http://localhost:5173/`. The tool fills a Loki container, `skillworks-seeded-loki`, on port
3101 with a made-up month of telemetry that ends now, and runs the API on port 5199. Ctrl+C stops
all three and removes the container. The AppHost's Loki is not touched.

To seed the Loki and nothing else, add `--seed-only`. The container keeps running after the tool
exits. Remove it with `docker rm -f skillworks-seeded-loki`.

### Checks

Docker must be running, because the API tests start Loki in a container. `uv` must be on PATH,
because the script tests are Python. Run the front-end checks from `src/Skillworks.Studio.Web`, so
they use the local tools and not anything installed globally.

```
dotnet test Skillworks.slnx

uv run --with pytest pytest tests/plugins/skillworks/scripts --ignore=tests/plugins/skillworks/scripts/skillworks-preflight_test.py
uv run --with pytest pytest tests/plugins/skillworks/scripts/skillworks-preflight_test.py

node --test "tests/plugins/skillworks/scripts/**/*.test.mjs"

cd src/Skillworks.Studio.Web
npm run typecheck
npm run lint
npm test
```

The loop runs the same checks from `docs/agents/suite.json`. A new check goes in both places.
[docs/agentic-development/checks.md](docs/agentic-development/checks.md) says how the loop runs
them, and how to run the script tests against the real `gh` and `claude`.

## Repo layout

| Path | What it is |
|---|---|
| `src/Skillworks.Core/` | The domain. No HTTP. The API is a thin shell over it. |
| `src/Skillworks.Studio.Api/` | The ASP.NET Core shell. HTTP and nothing else. |
| `src/Skillworks.Studio.Web/` | The React front end. Renders what the API shaped. Any rule of its own lives in a `lib` folder, such as `src/dashboard/lib/`, with a test beside it. |
| `src/Skillworks.AppHost/` | The Aspire orchestrator. One command starts everything. |
| `src/Skillworks.ServiceDefaults/` | Aspire's shared health, telemetry and service discovery setup. |
| `src/Skillworks.Architecture/` | The architecture check. Reads the rules files in `.claude/rules/` and lists the places the code breaks them. |
| `tests/Skillworks.Core.Tests/` | The stores Studio reads, tested against real containers, and the stand-ins for a store that stalls. |
| `tests/Skillworks.Studio.Api.Tests/` | The real API in memory, against a real Loki, asserting the JSON it returns. |
| `tests/Skillworks.Architecture.Tests/` | The architecture check on small folder trees, and on this repo. |
| `tests/plugins/skillworks/scripts/` | The Plugin's scripts, run against a throwaway repository. |
| `plugins/` | The local Marketplace. It holds the one Plugin, `skillworks`, and this repo loads its skills from there. Studio reads it by default. |
| `plugins/skillworks/scripts/` | The loop's scripts: the driver, the landing, the worktrees, the Suite, the preflight, and the hook scripts. They read the repo from the git top level of the folder they start in, never from where the Plugin sits. |
| `plugins/skillworks/hooks/` | The Plugin's hooks. On `SessionStart` and `InstructionsLoaded` they record what the Session was given, when telemetry is on. On `PreToolUse` they name the Session in each commit Claude makes, always. |
| `plugins/skillworks/bin/` | The short commands the Plugin puts on PATH: `spec-loop`, `land-ticket`, `ticket-worktree`, `skillworks-preflight` and `seed-steering`. Each runs its script from the Plugin. |
| `.claude/skills/` | The skills that are not in the Plugin. Dev tooling for this repo, mostly vendored. |
| `tools/` | Dev tools you run by hand, such as `seeded-studio.mjs`. |
| `docs/agents/` | Reference text more than one skill reads. `/skillworks:skillworks-setup` seeds a starting version of each, and of the rules, in a repo that has none. This repo's copies are its own. |
| `docs/agents/suite.json` | The Suite file: the checks that decide green for this repo, in order, each with its folder and what must be ready first. The loop runs these and nothing else. |
| `docs/agentic-development/` | How the dev loop works, for a human reading it rather than a skill. |
| `docs/studio/` | How Studio gets its telemetry. |

The top folder under a code root is a Slice, named for a job Studio does, with `Shared` beside the
Slices for the code no one job owns. `.claude/rules/file-placement.md` holds the rules.

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
