# Working on Skillworks

This page is for working on Skillworks itself: its checks, and where its code lives. The
[README](../README.md) says what Skillworks is, how to run Studio, and how to use the Dev loop. This
repo runs on its own Plugin, so the Dev loop works here as it does in any repo.

## Checks

Run every check with `skillworks-suite`. It keeps a Proof of each check that passes, so a check
whose inputs have not changed does not run again. It needs Docker, because the API tests start Loki
in a container and the script tests run in a Linux image. It needs `uv` on PATH, because the command
is Python.

These are the same checks, one by one. Run by hand, they need Docker for the API tests, and `uv` on
PATH because the script tests are Python. Run the front-end checks from `src/Skillworks.Studio.Web`,
so they use the local tools and not anything installed globally.

```
dotnet test tests/Skillworks.Architecture.Tests

dotnet test Skillworks.Studio.slnf --blame-crash --blame-crash-dump-type mini

uv run --with pytest --with pytest-xdist --with filelock pytest -n auto tests/plugins/skillworks/scripts -m "not this_repo"

uv run --with pytest pytest tests/plugins/skillworks/scripts/suite_test.py -m this_repo

node --test "tests/plugins/skillworks/scripts/**/*.test.mjs"

claude plugin validate plugins/skillworks

cd src/Skillworks.Studio.Web
npm run typecheck
npm run lint
npm test
```

The loop runs the same checks from `docs/agents/suite.json`. A new check goes in both places.
[The Suite](usage/suite.md) says how the loop runs them. This repo's Suite file sets `runs` to 2,
so that a check that goes red and then passes shows as a Flake. The Architecture tests run
alone, so they never wait on Docker. The Core and API tests run over one solution filter,
`Skillworks.Studio.slnf`, so they build once. The loop runs the script
tests in the Linux image `docs/agents/script-tests.Dockerfile`, because on Windows each git and bash
process they start is slow to start. Run by hand, the command above runs them on your own machine.
The tests marked `this_repo` run on the host in a check of their own, because they read the paths
the script tests ignore, and the image gets no copy of those.
`claude plugin validate` reads each skill's frontmatter with the parser Claude Code uses at runtime.
Claude Code drops a skill whose frontmatter does not parse, so this check goes red on it. A Plugin
with only warnings, such as no version or no author, leaves it green.

### The script tests

The loop's scripts live in the Plugin, at `plugins/skillworks/scripts/`, and their tests sit at the
same path under `tests/`. The script tests build a throwaway repository in a temporary directory and
touch nothing else. The scripts are Python, so `uv` has to be on PATH for their tests to run. pytest,
and `filelock` for the landing lock, are asked for on the command line, because the scripts carry no
project file. The hook scripts are node, and their tests sit beside the script tests and use the
test runner built into node, so they add no dependency. node expands the quoted pattern itself.

The script tests come in two sets, told apart by one flag on the same path. The commands above run
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
uv run --with pytest --with filelock pytest tests/plugins/skillworks/scripts --real-binaries
```

### The ten-minute wait

A session waits ten minutes on a command before it gives up, rather than the two minutes it would
otherwise. `.claude/settings.json` sets that. The script suite took 184, 299, 321 and 413 seconds
across four runs of the same tests on this machine, and the spread is machine load, so two minutes
loses the result and a session has to run the suite in the background and poll it instead. The wait
is a ceiling and never a delay, so a run that takes three minutes still answers in three.

Every Session the loop starts gets a Bash limit of 45 minutes, by default and at most, beside the
ten minutes the settings file sets for a session at the keyboard. Under `claude -p` a command moved to
the background dies with the Session's last turn, so a long check has to finish in the foreground.
[ADR 0033](adr/0033-a-session-that-stops-short-is-nudged-by-the-driver.md) records why.

This does not reach the loop itself, which runs for hours and still has to be started in the
background.

### A Python with nothing to run

`.claude/settings.json` also sets `PYTHON_BASIC_REPL=1`. On Windows, Python 3.13 handed an empty
script, such as `python - <<'EOF'` with nothing before the `EOF`, opens its new prompt. That prompt
fails to read the console, starts again, and never stops, so the command holds a session for the
whole of its wait. The basic prompt reads the empty input and exits at once.

## Repo layout

| Path | What it is |
|---|---|
| `src/Skillworks.Core/` | The domain. No HTTP. The API is a thin shell over it. |
| `src/Skillworks.Studio.Api/` | The ASP.NET Core shell. HTTP and nothing else. |
| `src/Skillworks.Studio.Web/` | The React front end. Renders what the API shaped. Any rule of its own lives in a `lib` folder, such as `src/dashboard/lib/`, with a test beside it. |
| `src/Skillworks.AppHost/` | The Aspire orchestrator. One command starts everything. |
| `src/Skillworks.ServiceDefaults/` | Aspire's shared health, telemetry and service discovery setup. |
| `src/Skillworks.Architecture/` | The architecture check. Reads the rules files in `docs/agents/rules/` and lists the places the code breaks them. |
| `tests/Skillworks.Core.Tests/` | The stores Studio reads, tested against real containers, and the stand-ins for a store that stalls. |
| `tests/Skillworks.Studio.Api.Tests/` | The real API in memory, against a real Loki, asserting the JSON it returns. |
| `tests/Skillworks.Architecture.Tests/` | The architecture check on small folder trees, and on this repo. |
| `tests/plugins/skillworks/scripts/` | The Plugin's scripts, run against a throwaway repository. |
| `plugins/` | The local Marketplace. It holds the one Plugin, `skillworks`, and this repo loads its skills from there. Studio reads it by default. |
| `plugins/skillworks/scripts/` | The loop's scripts: the driver, the landing, the worktrees, the Suite, the preflight, and the hook scripts. They read the repo from the git top level of the folder they start in, never from where the Plugin sits. |
| `plugins/skillworks/hooks/` | The Plugin's hooks. On `SessionStart` and `InstructionsLoaded` they record what the Session was given, when telemetry is on. On `PreToolUse` they name the Session in each commit Claude makes, always. |
| `plugins/skillworks/bin/` | The short commands the Plugin puts on PATH: `spec-loop`, `land-ticket`, `ticket-worktree`, `skillworks-preflight`, `seed-steering`, `set-co-authored-by`, `allow-commands`, `skillworks-suite`, `tracker-publish` and `spec-commits`. Each runs its script from the Plugin. |
| `.claude/skills/` | The skills that are not in the Plugin. Dev tooling for this repo, mostly vendored. |
| `tools/` | Dev tools you run by hand, such as `seeded-studio.mjs`. |
| `docs/agents/` | Reference text more than one skill reads. `/skillworks:skillworks-setup` seeds a starting version of each, and of the rules, in a repo that has none. This repo's copies are its own. |
| `docs/agents/suite.json` | The Suite file: the checks that decide green for this repo, in order, each with its folder and what must be ready first. The loop runs these and nothing else. |
| `docs/usage/` | How a team uses Skillworks, and how the loop works, for a human reading it rather than a skill. |
| `docs/studio/` | How to run Studio, its settings, and how it gets its telemetry. |
| `docs/assets/` | The pictures the README shows. |

The top folder under a code root is a Slice, named for a job Studio does, with `Shared` beside the
Slices for the code no one job owns. `docs/agents/rules/file-placement.md` holds the rules.

