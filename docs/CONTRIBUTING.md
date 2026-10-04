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

## Changing a Plugin skill

The tests and the driver match a skill's exact text. Read this before you change a file under
`plugins/skillworks/skills/`. Each fact here points at the code or the test that holds it. Where
this page and the code differ, the code is right, so mend this page.

### Tests match the text

`tests/plugins/skillworks/scripts/` holds tests that read the skills as text. Most are in
`seed_steering_test.py`. More are in `suite_test.py`, `spec_loop_test.py` and `count/`. Before you
change a skill, search those files for the skill's name and for each string you mean to touch. They
pin four kinds of thing:

- A sentence, a heading or a command that must be there, word for word.
- A word that must not be there. Some bans match inside a longer word: an axis file may hold no
  first word of a Suite command.
- A position: the last sentence of a description, four strings inside one paragraph, the first
  fenced block of a file, a stub with no `## ` heading.
- The front matter: which skills are hidden, and the keys a Plugin skill may use, in
  `FRONT_MATTER_KEYS`. Add a new key there in the same commit.

Several tests sweep every skill: no Skill tool call to a hidden skill, no path into a hidden skill's
folder, no link out of the Plugin, no habit of this repo. A new line in any skill can trip one.

Where a test pins the old words and the change needs new ones, change the test in the same commit.
Where the new text can keep the old words, keep them.

### The driver matches the text

The driver is `plugins/skillworks/scripts/spec_loop.py`, with `land_ticket.py`, `count/` and
`tracker/` beside it. It types each loop skill's command name and flags, and it reads what the
Session writes:

- The heading an axis ends under, `## Standards`, `## Spec` or `## Architecture`, anywhere in the
  last message.
- `BLOCKED` at the start of the first line that is not empty.
- `DEPARTS`, `CHOSE` and `HAND CHECK` at the start of any line.
- `REFUSED <n>` at the start of any line of a resolve.
- The reports on the Tracker: the first line, the `###` lists, and the shape of each line in a list.

Read the reader's code before you change a shape or write one of these markers into a skill.
`docs/usage/the-loop/` describes each shape for a person, so a change to a shape changes that page
too.

### What the driver already says

The driver adds one paragraph to every Session it starts, and ends every Nudge the same way. The
texts are `UNATTENDED` and `NUDGE_TAIL` in `spec_loop.py`, and
[Nobody answers in the loop](usage/the-loop/sessions.md#nobody-answers-in-the-loop) gives them in
plain words. They say that nobody will answer, and they ask for three kinds of line: a Choice
(`CHOSE`), a Hand check (`HAND CHECK`), and Blocked (`BLOCKED`, only when the work cannot be done).

So a loop skill:

- Does not repeat that paragraph. It is the driver's, and a skill run by hand still asks the person.
- Says which mode a rule is for, where the loop and a hand run differ.
- Ends a step that cannot be done on the `BLOCKED` line. It does not end it by leaving a check to
  fail, because a failed check earns a Nudge, and the Nudge says to do what is owed.
- Starts no other line with one of the three openings.

### A loop Session

- It is a fresh `claude -p` Session in the ticket's worktree. `build`, `fix` and `finish` share one
  Session. Each axis, the sweep, the Cut and each check has its own.
- The Plugin loads from the main checkout. So a ticket that changes a skill does not change its own
  later steps.
- A tool call outside the allow rules is a Denial, and nobody can approve it. The rules are in
  `.claude/settings.json`, seeded from `plugins/skillworks/skills/skillworks-setup/settings.json`.
  Check that each command a loop skill names is allowed in the form the skill gives it.
- Scratch files go under `.spec-loop/` in the worktree. A temp folder, or a path outside the
  worktree, is refused.
- `spec-loop-counts` prints how the steps of past runs ended, with their Nudges and Denials. Read it
  before and after a change to a loop skill. It costs nothing.

### The output style

`plugins/skillworks/output-styles/skillworks.md` is forced on every Session, loop Sessions too. It
asks for few, plain words and for two options at most. A skill that fixes what a report holds says
that every item is written. A skill that needs its own terms in a reply says where they go.

### Steering and Machinery

A Plugin skill is Machinery: every repo runs the same text. So it carries no fact of one repo. It
reads the fact from the repo's Steering under `docs/agents/`, and a test fails a skill that states a
habit of this repo.

- Where the glossary and the ADRs live: `docs/agents/domain.md`. A bare `CONTEXT.md` is the wrong
  file in a repo with more than one context.
- How to read and write a ticket: `docs/agents/issue-tracker.md`, in words that fit either Tracker.
- A Steering file that is missing gets the stop that `tdd` has: stop, name the file, say that
  `/skillworks:skillworks-setup` writes it, and say that nothing was done.

The seeds under `skillworks-setup/seeds/` become each team's own files. An edit to a seed shows as a
diff in every team's next setup run, so do not edit one for style.

### With the change

- Files that share a sentence change together: the three axis files, the three axis stubs, a skill
  and the user page that describes it.
- A vendored skill is listed in `THIRD-PARTY-NOTICES.md`. Update the notice when the body stops
  being upstream.
- Run `skillworks-suite`.
- A running Session keeps the Plugin text it started with. Restart it after the change Lands. A
  project skill under `.claude/skills/` needs no restart.

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
| `plugins/skillworks/bin/` | The short commands the Plugin puts on PATH: `spec-loop`, `land-ticket`, `ticket-worktree`, `skillworks-preflight`, `seed-steering`, `set-co-authored-by`, `allow-commands`, `skillworks-suite`, `tracker-publish`, `spec-commits` and `spec-loop-counts`. Each runs its script from the Plugin. |
| `.claude/skills/` | The skills that are not in the Plugin. Dev tooling for this repo, mostly vendored. |
| `tools/` | Dev tools you run by hand, such as `seeded-studio.mjs`. |
| `docs/agents/` | Reference text more than one skill reads. `/skillworks:skillworks-setup` seeds a starting version of each, and of the rules, in a repo that has none. This repo's copies are its own. |
| `docs/agents/suite.json` | The Suite file: the checks that decide green for this repo, in order, each with its folder and what must be ready first. The loop runs these and nothing else. |
| `docs/usage/` | How a team uses Skillworks, and how the loop works, for a human reading it rather than a skill. |
| `docs/studio/` | How to run Studio, its settings, and how it gets its telemetry. Studio's glossary, `CONTEXT.md`, sits here too, and `CONTEXT-MAP.md` points at it. |
| `docs/assets/` | The pictures the README shows. |

The top folder under a code root is a Slice, named for a job Studio does, with `Shared` beside the
Slices for the code no one job owns. `docs/agents/rules/file-placement.md` holds the rules.

