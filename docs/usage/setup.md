# Setup

Setup gets your repo ready for the loop. It checks your machine and your remote, copies a Seed of
each Steering file into your repo, points `CLAUDE.md` at them, and writes the settings the loop needs
to run with nobody watching. Run it once per repo. Run it again whenever you like: it brings in a
newer Seed and keeps your team's edits.

## Before you start

You need these on your machine:

- `git`, with a `user.email`. The files Tracker claims each ticket in that name.
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
- Or, if your default branch is protected, the Target branch `spec`. Each spec then gets a branch of
  its own, and your team reviews it as one pull request to the default branch.

[The loop](the-loop.md#the-tracker) says how to choose a Tracker, and
[the Target branch](the-loop.md#the-target-branch) how to choose a Target branch.

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

1. **Seed the Steering.** `seed-steering` copies each Seed to its place, keeps a base copy of it in
   `docs/agents/.seeds/`, and adds the loop's working folders to `.gitignore`. It stops in a repo with
   no remote.
2. **Ask for the Tracker.** Setup suggests `github` when `origin` names `github.com`, and `files`
   otherwise. It writes your answer into `tracker` in `docs/agents/loop.json`. With `files`, it tells
   you that `.specs/` is committed and must never be gitignored.
3. **Ask for the Target branch.** Setup suggests your remote's default branch, and offers `spec`. It
   writes your answer into `target-branch` in `docs/agents/loop.json`.
4. **Point `CLAUDE.md` at the docs.** Setup adds an `## Agent skills` block that names your Tracker,
   your tracker docs and your domain docs, and imports the five rules: comments, determinism, file
   placement, testing and words.
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
such as the guides `tdd` reads. In the loop's `acceptEdits` mode a read outside the repo is a Denial
unless a rule allows it, and the loop cannot ask you.

Expect a permission prompt on a first run, at the seeding and at the preflight. The allowlist that clears it is written
in step 6.

## The questions setup asks

Setup asks four things on a clean repo: your Tracker, your Target branch, whether commits credit
Claude, and the one yes it needs. It asks more only where your repo already holds an answer of its
own.

| Question | When setup asks it |
|---|---|
| Which Tracker does your team use? | Always. Setup suggests `github` when `origin` names `github.com`, and `files` otherwise, so the common answer is one keypress. If `tracker` in `docs/agents/loop.json` already names another answer, setup suggests that one. |
| Which is your Target branch? | Always. Setup suggests your remote's default branch, so the common answer is one keypress, and offers `spec` for one pull request per spec. If `docs/agents/loop.json` already names another answer, setup suggests that one. |
| Should commits and pull requests credit Claude? | Always. On a first run setup suggests `hide`, so the common answer is one keypress. If `co-authored-by` in `docs/agents/loop.json` already names an answer, setup suggests that one. [Credit for Claude](#credit-for-claude) says what each answer does. |
| Do you agree to the allowlist and to turning auto-memory off? | Always, once, before it writes `.claude/settings.json`. It reads each allowlist entry out, and the memory line and your answer on the credit for Claude with them. The allowlist lets the loop run `git push`, `gh issue close` and `tracker-publish` with no prompt. That is the point, and also the risk. |
| Which side of this overlap do you keep, yours or the Seed's? | On a second run, when your edit and the newer Seed's change touch the same lines. Setup shows both sides, and asks once for each overlap. |
| Which lines of the newer Seed do you want? | When a Steering file differs from its Seed and has no base copy, because your repo was set up before base copies existed. Setup shows the difference and changes the file only by the lines you pick. |
| Which Marketplace, or which Plugin setting, do you keep? | When `.claude/settings.json` already names the `skillworks` Marketplace or the Plugin with another value. Setup shows both. |
| Keep auto-memory on, or turn it off? | When `.claude/settings.json` says `"autoMemoryEnabled": true`. With memory on, memory files on each machine steer the loop, so it runs differently from one machine to the next. Setup never changes it without asking. |

## The files setup writes

Review these before you commit them.

| File | What it holds |
|---|---|
| `docs/agents/rules/comments.md` | The comments rule. `doc-comments` ships as `false`. |
| `docs/agents/rules/determinism.md` | The determinism rule. `contexts` starts empty. `clock` ships as `TimeProvider`. |
| `docs/agents/rules/file-placement.md` | The file placement rule. `slices`, `concerns` and `test-roots` start empty. `max-types-per-folder`, `source-files`, `test-files`, `skip-folders`, `banned-folder-names` and `name-map` ship with a default. |
| `docs/agents/rules/testing.md` | The testing rule: your team's taste in tests. It has no settings. |
| `docs/agents/rules/words.md` | The words rule. `banned-words` and `skip-folders` start empty. |
| `docs/agents/issue-tracker.md` | How the skills read and write each Tracker: the `gh` calls for `github`, and the `.specs/` files for `files`. The ticket shape, and the two conventions the loop leans on. |
| `docs/agents/domain.md` | Where your glossary and your ADRs live. |
| `docs/agents/placement-checks.md` | The commands that prove placement. It starts with none. |
| `docs/agents/review-standards.md` | What the `standards` review checks: the code smells, and your team's own checks. It starts with no check of your own. |
| `docs/agents/review-architecture.md` | What the `architecture` review checks: the failures of placement, and your team's own checks. It starts with no check of your own. |
| `docs/agents/review-spec.md` | What the `spec` review checks beyond the ticket: your team's own checks. It starts with no check. |
| `docs/agents/suite.json` | Your Suite. It starts with no checks, and the loop stops until you add one. |
| `docs/agents/loop.json` | The loop's settings. `tracker` holds your answer, `github` or `files`. `target-branch` starts as your remote's default branch. `co-authored-by` holds your answer on the credit for Claude, `show` or `hide`, and starts as `hide`. |
| `docs/agents/surfaces.md` | The places a change can have to reach besides its code. It starts with the README and the user docs. |
| `docs/agents/.seeds/` | A base copy of each Seed, exactly as setup last copied it, and a README. Setup keeps these, and a second run reads them. Do not edit them. |
| `.gitignore` | The loop's working folders: `.spec-loop/`, `.handoff/` and `.claude/worktrees/`. Each machine has its own, and nobody shares them. Setup also creates `.handoff/`, where `handoff` saves. |
| `CLAUDE.md` | The `## Agent skills` block. If your repo has `AGENTS.md` and no `CLAUDE.md`, setup edits `AGENTS.md` instead. |
| `.claude/settings.json` | The Marketplace, the Plugin, the allowlist with its read rules for the Plugin's folder, `"autoMemoryEnabled": false`, and the prompt cache keys `promptCacheTtl` and `subagentPromptCacheTtl`, each `"1h"`. An `attribution` block, which setup rewrites from `co-authored-by` each time it runs. On a second run, setup adds a cache key that is missing and keeps one your team set. |

Setup writes nothing under `~/.claude`, and it leaves `.claude/settings.local.json` alone.

Setup does not write `.git/config`. The Plugin's hook writes three rules there on the first commit it
rewrites in each clone: `trailer.Skillworks-Session.ifExists=addIfDifferent`,
`trailer.Co-Authored-By.ifExists=addIfDifferent` and `trailer.Ticket.ifExists=replace`. They tell git
to replace a `Ticket` line and not to add a line twice on an amend. The hook writes them again when
one goes missing or holds another value.

[Steering](steering.md) says what each of these files does and what your team can change in it.

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

The `Skillworks-Session` trailer stays on every commit, whichever you answer.

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
| `asks` | Your edit and the Seed's change touch the same lines. | Shows both sides and asks which to keep. |
| `kept ..., which differs from the seed` | The file has no base copy, because your repo was set up before base copies existed. | Shows the difference, and asks which lines to take. |
| `kept ..., as you settled it` | You decided on a file with no base copy. | Keeps the file as you left it, and writes its base copy. |

The labels on a shown change say what each side holds:

| Outcome | `---` side | `+++` side |
|---|---|---|
| `updated` | `old-seed/`: the old Seed, which you never edited | `new-seed/`: the new Seed |
| `merged` | `yours/`: your file | `merged/`: your file with the Seed's change applied |
| `kept ..., which differs from the seed` | `yours/`: your file | `seed/`: the current Seed |

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
- **`CLAUDE.md`.** Setup updates the `## Agent skills` block in place. It never adds a second copy,
  and it leaves every other section alone.
- **`.claude/settings.json`.** Setup adds the allowlist entries that are missing and removes none. It
  rewrites the `attribution` block from `co-authored-by` in `docs/agents/loop.json`. It adds `promptCacheTtl` or `subagentPromptCacheTtl`
  where one is missing, and keeps a value your team set. It sets `autoMemoryEnabled` to `false` where
  nothing sets it, and asks before it changes a `true`. It leaves every other key as you have it.
