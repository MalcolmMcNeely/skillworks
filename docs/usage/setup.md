# Setup

Setup gets your repo ready for the loop. It checks your machine and your remote, copies a Seed of
each Steering file into your repo, points `CLAUDE.md` at them, and writes the settings the loop needs
to run with nobody watching. Run it once per repo. Run it again whenever you like: it brings in a
newer Seed and keeps your team's edits.

## Before you start

You need these on your machine:

- `git` 2.38 or later, with a `user.email`. The files Tracker claims each ticket in that name. The
  landing needs 2.38 to tell lost work from work the new base already holds.
- `gh`, logged in, with the GitHub Tracker only. Check with `gh auth status`.
- `claude` on your `PATH`. The loop starts a Session with it for each step.
- `uv` on your `PATH`. The loop's scripts are Python and run under it.

Your repo needs these:

- An `origin` remote. Setup stops in a repo with no remote, and prints the commands that add one. A
  bare repo on a shared drive is enough.
- A Tracker: where your team keeps its specs and tickets. `github` keeps them as GitHub issues, and
  needs `origin` on GitHub with Issues turned on. `files` keeps them as committed Markdown files in
  `.specs/`, and works on any remote, such as GitLab, Bitbucket or a bare repo.
- A Target branch: the branch the loop Lands every ticket on. It can be any branch, such as `master`
  or `develop`, and you must be able to push to it straight away. A rule that asks for a pull request
  or a status check on it stops the loop.
- Or, if your default branch is protected, the Target branch `pr`: you make the branch and open
  the pull request. You make a branch of your own for each spec and start the grill on it, and your
  team reviews it as one pull request to the default branch.

[The loop](the-loop/tracker.md) says how to choose a Tracker, and
[the Target branch](the-loop/target-branch.md) how to choose a Target branch.

## Install the Plugin

The Plugin comes from a Marketplace in a clone of Skillworks. Clone it once, anywhere on your
machine:

```
git clone https://github.com/MalcolmMcNeely/skillworks.git
```

Then open Claude Code in your repo and add the Marketplace. Its folder is `plugins` in that clone:

```
/plugin marketplace add <your clone>/plugins
/plugin install skillworks@skillworks
```

Then run setup:

```
/skillworks:skillworks-setup
```

Setup writes the Marketplace and the Plugin into `.claude/settings.json`, so a teammate who clones
your repo gets the Plugin on trust, with no install by hand. The Marketplace path is relative when
the clone of Skillworks sits inside your repo, and in full when it does not. In full, each teammate
needs their clone of Skillworks at the same path.

## What setup does

First, setup asks whether the work goes to a team that does not use Skillworks. With no, it runs the
steps below on the branch you are on, as it always has. With yes, it runs them on the Steering
branch instead, as [Work for a team that does not use Skillworks](#work-for-a-team-that-does-not-use-skillworks)
says.

1. **Seed the Steering.** `seed-steering` copies each Seed to its place, keeps a base copy of it in
   `docs/agents/.seeds/`, and adds the loop's working folders to `.gitignore`. It stops in a repo with
   no remote.
2. **Ask for the Tracker.** Setup suggests `github` when `origin` names `github.com`, and `files`
   otherwise. It writes your answer into `tracker` in `docs/agents/loop.json`. With `files`, it tells
   you that `.specs/` is committed and must never be gitignored.
3. **Ask for the Target branch.** Setup suggests your remote's default branch, and offers `pr`. It
   writes your answer into `target-branch` in `docs/agents/loop.json`.
4. **Point `CLAUDE.md` at the docs.** Setup asks where your ADRs go, and writes your answer into
   `adr-folder` in `docs/agents/domain.md`. Then `seed-agent-skills` builds the `## Agent skills`
   block from your answers. The block names your Tracker, your tracker docs and your domain docs, with
   the folder `adr-folder` names, and imports each rule in `docs/agents/rules/`. The block is a Seed,
   so on a second run the script merges it with your edits, as it merges a Steering file.
5. **Preflight.** `skillworks-preflight` checks the tools, the remote, the Target branch
   `docs/agents/loop.json` names, and that `CLAUDE.md` imports each rule. With `github`, it checks the
   `gh` login too, and then creates the `ready-for-agent` label on GitHub. With `files`, it needs no
   `gh` and creates no label. If a check fails, setup stops there. The `CLAUDE.md` block from step 4
   is safe to leave: fix the fault and run setup again.
6. **Write the settings.** Setup writes the Marketplace, the Plugin, the allowlist,
   `"autoMemoryEnabled": false` and the prompt cache keys into `.claude/settings.json`. Then
   `set-co-authored-by` writes your answer on the credit for Claude into `co-authored-by` in
   `docs/agents/loop.json`, and rewrites the `attribution` block from it, as
   [Credit for Claude](#credit-for-claude) says.
7. **Report.** Setup says what it wrote and what it kept, and what your team fills in before the loop
   can finish a ticket.

The allowlist holds two read rules as well. `Read(~/.claude/plugins/**)` opens an installed Plugin's
folder to reading. When the Marketplace folder sits outside your repo, setup adds a read rule for
that folder too, such as `Read(//c/tools/skillworks/plugins/**)`. A skill must read its own files,
such as the guides `tdd` reads. The loop's driver gives each of its Sessions a read rule for the
Plugin's folder, so these two rules are for a Session you run by hand. Without them it stops to ask
you before each read outside the repo.

Expect a permission prompt on a first run, at the seeding and at the preflight. The allowlist that clears it is written
in step 6.

## The questions setup asks

Setup asks six things on a clean repo: whether the work goes to a team that does not use
Skillworks, your Tracker, your Target branch, where your ADRs go, whether commits credit Claude, and
the one yes it needs. With a yes to the first, it asks no Target branch. It asks more only where your repo already holds an answer of its
own.

| Question | When setup asks it |
|---|---|
| Will the work go to a team that does not use Skillworks? | Always, first. Setup suggests no, so the common answer is one keypress. If `origin` already holds `skillworks/steering`, and its `docs/agents/loop.json` sets `export` to `true`, setup suggests yes. With yes and the `files` Tracker, setup tells you to make `origin` a remote of your own first, such as a bare repo on your machine, so the loop's pushes do not reach your team's remote by mistake. [Work for a team that does not use Skillworks](#work-for-a-team-that-does-not-use-skillworks) says what yes does. |
| Which Tracker does your team use? | Always. Setup suggests `github` when `origin` names `github.com`, and `files` otherwise, so the common answer is one keypress. If `tracker` in `docs/agents/loop.json` already names another answer, setup suggests that one. |
| Which is your Target branch? | Always, unless you answered yes to the first question. Then setup asks nothing and writes `pr`. Setup suggests your remote's default branch, so the common answer is one keypress, and offers `pr` for one pull request per spec: you make the branch and open the pull request. If `docs/agents/loop.json` already names another answer, setup suggests that one. |
| Where do your ADRs go? | Always. Setup writes your answer into `adr-folder` in `docs/agents/domain.md`, and every new ADR goes to that one folder. It suggests one folder. On a second run, it suggests the folder `adr-folder` already names, so your answer survives. Else it looks for folders that hold numbered Markdown files, such as `0001-event-sourced-orders.md`, and have `adr` or `decision` in their path. It lists every one it finds, and suggests the one with the most files. Else it suggests `docs/adr`. A repo set up before this question existed stops at preflight until setup runs again, and one run clears the stop. |
| Should commits and pull requests credit Claude? | Always. On a first run setup suggests `hide`, so the common answer is one keypress. If `co-authored-by` in `docs/agents/loop.json` already names an answer, setup suggests that one. [Credit for Claude](#credit-for-claude) says what each answer does. |
| Do you agree to the allowlist and to turning auto-memory off? | Always, once, before it writes `.claude/settings.json`. It reads each allowlist entry out, and the memory line and your answer on the credit for Claude with them. The allowlist lets the loop run `git push`, `gh issue close` and `tracker-publish` with no prompt. That is the point, and also the risk. |
| Which do you keep for this overlap: yours, the Seed's, or a blend? | On a second run, when your edit and the newer Seed's change touch the same lines, in a Steering file or in the `## Agent skills` block. Setup shows both sides, and a blend of the two that the agent writes to fit your repo. It asks once for each overlap, and the script writes the one you pick. |
| Which lines of the newer Seed do you want? | When a Steering file, or the `## Agent skills` block, differs from its Seed and has no base copy, because your repo was set up before base copies existed. Setup shows the difference and changes the file only by the lines you pick. |
| Which Marketplace, or which Plugin setting, do you keep? | When `.claude/settings.json` already names the `skillworks` Marketplace or the Plugin with another value. Setup shows both. |
| Keep auto-memory on, or turn it off? | When `.claude/settings.json` says `"autoMemoryEnabled": true`. With memory on, memory files on each machine steer the loop, so it runs differently from one machine to the next. Setup never changes it without asking. |

## The files setup writes

Review these before you commit them.

| File | What it holds |
|---|---|
| `docs/agents/rules/comments.md` | The comments rule. `doc-comments` ships as `none`. |
| `docs/agents/rules/determinism.md` | The determinism rule. `contexts` starts empty. `clock` ships as `TimeProvider`. |
| `docs/agents/rules/file-placement.md` | The file placement rule. `slices`, `concerns` and `test-roots` start empty. `max-types-per-folder`, `source-files`, `test-files`, `skip-folders`, `banned-folder-names` and `name-map` ship with a default. `test-placement` ships as `mirror`. |
| `docs/agents/rules/testing.md` | The testing rule: your team's taste in tests. It has no settings. |
| `docs/agents/rules/words.md` | The words rule. `banned-words` and `skip-folders` start empty. |
| `docs/agents/issue-tracker.md` | How the skills read and write each Tracker: the `gh` calls for `github`, and the `.specs/` files for `files`. The ticket shape, and the two conventions the loop leans on. |
| `docs/agents/domain.md` | Where your glossary and your ADRs live. `adr-folder` holds your answer on where new ADRs go. |
| `docs/agents/adr-format.md` | The shape of an ADR: its template and its optional sections. It starts with the Skillworks shape. |
| `docs/agents/placement-checks.md` | The commands that prove placement. It starts with none. |
| `docs/agents/review-standards.md` | What the `standards` review checks: the code smells, and your team's own checks. It starts with no check of your own. |
| `docs/agents/review-architecture.md` | What the `architecture` review checks: the failures of placement, and your team's own checks. It starts with no check of your own. |
| `docs/agents/review-spec.md` | What the `spec` review checks beyond the ticket: your team's own checks. It starts with no check. |
| `docs/agents/suite.json` | Your Suite. It starts with no checks, and the loop stops until you add one. |
| `docs/agents/loop.json` | The loop's settings. `tracker` holds your answer, `github` or `files`. `target-branch` starts as your remote's default branch. `co-authored-by` holds your answer on the credit for Claude, `show` or `hide`, and starts as `hide`. |
| `docs/agents/surfaces.md` | The places a change can have to reach besides its code. It starts with the README and the user docs. |
| `docs/agents/.seeds/` | A base copy of each Seed, exactly as setup last copied it, and a README. `agent-skills.md` is the base copy of the `## Agent skills` block, exactly as setup last wrote it. Setup keeps these, and a second run reads them. Do not edit them. |
| `.gitignore` | The working folders: `.spec-loop/`, `.handoff/`, `.claude/worktrees/` and `.context-backfill/`. Each machine has its own, and nobody commits them. Setup also creates `.handoff/`, where `handoff` saves. `.context-backfill/` holds the Answer sheet of the [Context backfill](context-backfill.md). |
| `CLAUDE.md` | The `## Agent skills` block. A second run merges the block with your edits to it. If your repo has `AGENTS.md` and no `CLAUDE.md`, setup edits `AGENTS.md` instead. |
| `.claude/settings.json` | The Marketplace, the Plugin, the allowlist with its read rules for the Plugin's folder, `"autoMemoryEnabled": false`, and the prompt cache keys `promptCacheTtl` and `subagentPromptCacheTtl`, each `"1h"`. An `attribution` block, which setup rewrites from `co-authored-by` each time it runs. On a second run, setup adds a cache key that is missing and keeps one your team set. |

Setup writes nothing under `~/.claude`, and it leaves `.claude/settings.local.json` alone.

Setup does not write `.git/config`. The Plugin's hook writes three rules there on the first commit it
rewrites in each clone: `trailer.Skillworks-Session.ifExists=addIfDifferent`,
`trailer.Co-Authored-By.ifExists=addIfDifferent` and `trailer.Ticket.ifExists=replace`. They tell git
to replace a `Ticket` line and not to add a line twice on an amend. The hook writes them again when
one goes missing or holds another value.

[Steering](steering.md) says what each of these files does and what your team can change in it.

## Work for a team that does not use Skillworks

Answer yes to the first question when your team does not use Skillworks, and must be able to go on
without it. The loop then [Exports](the-loop/export.md) each finished spec onto your own branch, with
no trace of the Plugin.

- **With the `files` Tracker, make `origin` your own first.** Use a remote of your own, such as a bare
  repo on your machine, with your default branch pushed to it. The loop pushes its claims, its Target
  branches and the Steering branch to `origin`, so with your team's remote as `origin`, those pushes
  reach your team by mistake. If `origin` is not yet yours, setup stops, and you run it again after.
  With the `github` Tracker, `origin` is the GitHub repo whose Issues the loop uses.
- **Your working tree must be clean.** Setup stops when it is not.
- **Setup writes the Steering on the Steering branch, `skillworks/steering`.** It cuts the branch from
  your remote's default branch, and runs every step there. It asks no Target branch: it writes
  `"target-branch": "pr"` and `"export": true` into `docs/agents/loop.json`.
- **Setup commits the Steering there, and pushes it.** It shows you each file to review first. Then it
  commits, pushes `skillworks/steering` to `origin`, and switches you back to the branch you were on.
  That branch holds no Steering file, because setup never writes one there.

A later change to the Steering, such as the checks you add to `docs/agents/suite.json`, goes on
`skillworks/steering` too. Commit it there, and push it.

## Credit for Claude

Setup asks your team one question: should commits and pull requests credit Claude? The one answer,
`show` or `hide`, covers both. `set-co-authored-by` writes it to `co-authored-by` in `docs/agents/loop.json`,
which your team commits, so every developer and every loop Session follows it. Then it writes
Claude Code's `attribution` block in `.claude/settings.json` from the answer.

| Answer | What happens |
|---|---|
| `hide`, the default | No commit and no pull request credits Claude. The `attribution` block holds empty strings for `commit` and `pr`. |
| `show` | The Plugin's hook adds the credit line to each commit Claude makes. The line is always `Co-Authored-By: Claude <noreply@anthropic.com>`. The `attribution` block holds an empty string for `commit` and no `pr`, so Claude Code's own pull request credit applies. |

- **Claude Code's commit credit is always off.** Left on, it tells the model to type a credit line,
  and a typed line can push the `Ticket` trailer out of the lines git reads as trailers. The hook
  adds the line instead, in the right place.
- **Pull requests follow the same answer through Claude Code**, by its own `attribution.pr`.
- **The hook refuses a Claude credit line the model typed**, with `show` and with `hide`. The
  Session removes the line and commits again. The hook never touches a line that credits a person.
- **A repo with no answer keeps Claude Code's own credit.** With no `co-authored-by`, the hook adds
  no credit line and refuses none.
- **Setup rewrites the block from your answer each time it runs.** A block someone edited by hand
  comes back into step. To change your mind, run setup again, or run `set-co-authored-by show` or
  `set-co-authored-by hide`.
- **Setup never writes `"attribution": false`.** Claude Code before v2.1.281 rejects it and skips the
  whole file, which drops the allowlist and the Plugin too. Empty strings hide the line on every
  version.
- **Setup never writes `.claude/settings.local.json`.** It is gitignored, so a loop worktree never
  sees it, and the choice is your team's and not one developer's.

The `Skillworks-Session` trailer stays on every commit, whichever you answer. With the Export, a
commit on your own branch is the one exception: it gets no trailer, as [the Export](the-loop/export.md)
says.

## What your team fills in

The Seeds judge nothing until your team fills them in. Before the loop can finish a ticket:

- **`docs/agents/suite.json`**: add the checks that prove your code. [The Suite](suite.md) has the whole
  file. [Turn the rules into tests](#turn-the-rules-into-tests) adds the checks for the rules.
- **The allowlist** in `.claude/settings.json`: add each tool your Suite runs, such as a build or a
  test runner. A Session with nobody watching cannot ask you, so a missing entry is a Denial.
- **The rules' settings**, as your team settles them.

Then the loop is ready:

```
/skillworks:grill  →  /skillworks:spec-loop <spec#>
```

## Turn the rules into tests

Setup leaves the rules as prose. An agent reads their settings, but no check enforces them. Run
`/skillworks:architecture-tests` after setup to turn the rules into tests your team owns.

For a repo with a history and no glossary, run `/skillworks:context-backfill` first. It fills your
glossary and your ADRs once, from your code and your history, and writes nothing until you accept
it.
Setup names it as the next step when a commit touches a file setup does not write, and your repo has
no `CONTEXT.md` and no `CONTEXT-MAP.md`. [Context backfill](context-backfill.md) says how it works.

- **What it reads.** Each rule in `docs/agents/rules/` and the settings at its end, `CONTEXT-MAP.md`
  where your repo has one, and your repo's languages and test runners.
- **What it asks.** Which rules your team wants enforced. It recommends the rules whose settings are
  filled in, because a rule with empty settings judges nothing.
- **How it chooses.** For each rule and each language, it picks one of two ways. A **common tool** for
  the language, where one fits, such as dependency-cruiser for TypeScript or ArchUnitNET for .NET. It
  prefers a tool your repo already has. Or a **starter test** in your own language and test runner,
  which reads the rule's settings at every run and checks the files. Some rules no tool or file check
  can prove, and it leaves those to your team and says why.
- **How it proves each test.** It writes each test red first, on a breach it builds for the test, so
  you know the test can fail. Then it runs the test on your code and proves it green. A rule your code
  breaks today is reported to you, and never weakened. You choose: fix the code, or change the setting.
- **What it writes.** You approve each write before it happens:
  - `docs/agents/suite.json`: each test's command, with the `ignores` that keep it asleep.
  - `docs/agents/placement-checks.md`: both tables, which check proves which rule, and the exact
    command that runs each check.
  - `.claude/settings.json`: the command of any new tool, in the allowlist. It writes the entries with
    `allow-commands`, which adds each missing entry and removes none. Claude Code can turn down a
    write to this file, even one you approve. If it does, the skill shows you the exact entries and
    the file, and asks you to add them. It reads the file back before it calls the step done, and its
    report names any entry still missing, because the loop can hit a Denial on that command.

Run it again when your team adds a language or a rule. A second run tests only what is new, and keeps
every test you already have.

## Run setup again

A second run repairs, and brings in a newer Seed after a Plugin update. A Plugin update alone never
changes your Steering.

### Each Steering file

Setup compares three versions of each Steering file: the base copy in `docs/agents/.seeds/`, your
file, and the Plugin's current Seed. The base copy is the Seed as setup last copied it, so setup can
tell your edits from the Plugin's. It says what it did to each file in one line:

| Outcome | When | What setup does |
|---|---|---|
| `wrote` | The Seed is new to your repo, or the file is missing. | Writes the file and its base copy. |
| `updated` | You never edited the file, and the Seed moved on. | Replaces the file and its base copy with the new Seed, and shows the change. |
| `kept ..., which you edited` | You edited the file, and the Seed did not move. | Nothing. |
| `kept ..., the same as the seed` | Your file and its base copy are the same as the Seed. | Nothing. |
| `kept ..., the same as the seed, and brought its base copy up to the seed` | Your file is the same as the Seed, and its base copy is an older Seed. | Replaces the base copy with the Seed. |
| `kept ..., the same as the seed, and wrote its base copy` | Your file is the same as the Seed, and has no base copy. | Writes the base copy. |
| `merged` | You edited the file, and the Seed moved on in other lines. | Applies the Seed's change, keeps your edit, and shows the change. |
| `asks` | Your edit and the Seed's change touch the same lines. | Shows both sides and a blend of the two, and asks which to keep. |
| `kept ..., which differs from the seed` | The file has no base copy, because your repo was set up before base copies existed. | Shows the difference, and asks which lines to take. |
| `kept ..., as you settled it` | You decided on a file with no base copy. | Keeps the file as you left it, and writes its base copy. |

The labels on a shown change say what each side holds:

| Outcome | `---` side | `+++` side |
|---|---|---|
| `updated` | `old-seed/`: the old Seed, which you never edited | `new-seed/`: the new Seed |
| `merged` | `yours/`: your file | `merged/`: your file with the Seed's change applied |
| `kept ..., which differs from the seed` | `yours/`: your file | `seed/`: the current Seed |

An overlap can take a blend in place of either side. The agent writes a blend of your edit and the
Seed's change to fit your repo, and shows it beside both sides. If you pick it, the script writes the
blend in place of the overlap, and the base copy takes the new Seed. The agent writes nothing into
your file itself.

The `## Agent skills` block merges like a Steering file. Setup compares the block in `CLAUDE.md` with
its base copy, `docs/agents/.seeds/agent-skills.md`, and with the block your answers build today. It
says what it did in the same outcome lines, names the block by its file, and asks the same questions,
with a blend for an overlap. The block runs from its heading to the next `## ` heading, and setup
changes nothing outside it.

Setup writes a deleted Steering file again. Every step of the loop needs its file, so a file never
stays deleted. To use less of a file, empty it down, and keep the file.

Setup changes no file until you have answered every question. A file with no base copy is a question too,
so while one waits, setup changes no other file either. Then it writes the files you decided on and
their base copies, all in one run.

A file with no base copy gets one after you decide on it, even if you take no lines. From then on,
setup can merge it like any other file.

Setup commits nothing. Review each changed file before you commit.

### The other outputs

- **The label.** With `github`, a label that is there is left alone.
- **`.gitignore`.** Setup adds only the working folders it does not name yet. It never adds one twice.
- **`CLAUDE.md`.** Setup merges your edits to the `## Agent skills` block, as
  [Each Steering file](#each-steering-file) says. It writes a deleted block again, never adds a second
  copy, and leaves every other section alone.
- **`.claude/settings.json`.** Setup adds the allowlist entries that are missing and removes none. It
  rewrites the `attribution` block from `co-authored-by` in `docs/agents/loop.json`. It adds `promptCacheTtl` or `subagentPromptCacheTtl`
  where one is missing, and keeps a value your team set. It sets `autoMemoryEnabled` to `false` where
  nothing sets it, and asks before it changes a `true`. It leaves every other key as you have it.
