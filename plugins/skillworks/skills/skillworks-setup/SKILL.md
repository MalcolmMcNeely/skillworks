---
name: skillworks-setup
description: Configure a repo for the Skillworks dev loop — the Tracker, GitHub labels with the github Tracker, the Steering the skills read (rules, tracker docs, review files, a starting Suite file), the CLAUDE.md pointer, the Plugin and the permission allowlist the loop needs to run unattended, and auto-memory off. Run once per repo.
disable-model-invocation: true
---

# Skillworks Setup

Write the Steering the Skillworks skills read, and the settings the loop needs. Run it once. Re-run it to repair, or to bring in a newer seed.

The Plugin carries the Machinery: the skills, the scripts, the hooks and the output style. They run from the Plugin, so setup copies none of them. Steering is what the repo tells the loop about itself. Setup copies a starting version of each piece, and the team owns it from then on. A Plugin update never changes it by itself. A second run of setup brings in the newer seed and keeps the team's edits.

The Tracker is where the team keeps its specs and tickets: `github`, for GitHub Issues, or `files`, for Markdown files in the Sidecar, a local git repo beside the repo. Setup asks which one.

Setup refuses a repo with no remote, with either Tracker. The loop Lands every ticket by pushing to `origin`. A bare repo on a shared drive is enough, and `seed-steering` prints the commands that add one.

The outputs:

| Output | Why it exists |
|---|---|
| The `ready-for-agent` label, with `github` only | `/skillworks:to-spec` and `/skillworks:to-tickets` apply it, and `gh issue create` fails on a label that does not exist. Nothing in the loop reads it. |
| `docs/skillworks/rules/*.md` | The five rules: comments, determinism, file placement, testing and words. The review axes read them. The testing rule holds the team's taste in tests and has no settings. The settings that name what a rule judges start empty, so nothing is judged until the team fills them in: `contexts`, `slices`, `concerns`, `test-roots`, `banned-words` and the words rule's `skip-folders`. The others ship with a default the team can change: `doc-comments`, `clock`, `max-types-per-folder`, `source-files`, `test-files`, the placement rule's `skip-folders`, `banned-folder-names`, `name-map` and `test-placement`. `doc-comments` ships as `none`, so no source file holds a doc comment until the team picks `code` or `all`. `test-placement` ships as `mirror`, so each test mirrors the code file it tests until the team picks `free`. |
| `docs/skillworks/issue-tracker.md`, `docs/skillworks/domain.md` | One copy of the tracker calls and of where the domain docs live. Without one shared copy each skill carries its own and they drift. The YAML block at the end of `domain.md` holds `adr-folder`, the one folder every new ADR goes to. Setup asks for it. |
| `docs/skillworks/adr-format.md` | The ADR shape: the template and the optional sections every new ADR fills. It starts with the Skillworks shape, and a team edits it so new ADRs look like the ones it keeps. |
| `docs/skillworks/placement-checks.md`, `review-standards.md`, `review-architecture.md`, `review-spec.md` | What the review axes judge against. Each review file holds the baseline for its axis, if it has one, and a team's own checks, which start empty. `review-spec.md` holds no baseline. The placement checks start with no command listed. A team names the exact commands that prove placement, each with its folder and anything to run first, and the architecture review runs those and nothing else. |
| `docs/skillworks/suite.json` | The Suite: what green means for this repo's code. It starts with no checks, and a Suite with no checks is not ready, so the loop stops until the team names its checks. |
| `docs/skillworks/loop.json` | The loop's settings. `tracker` is `github` or `files`, and setup asks which. `target-branch` is the branch the loop Lands on, or `pr` for one pull request per spec. It starts as the remote's default branch, and setup asks the team to confirm it. `co-authored-by` is `show` or `hide`, the team's answer on the credit for Claude. It starts as `hide`, and setup asks. |
| `docs/skillworks/surfaces.md` | The Surfaces: the places a change can have to reach besides its code. It starts with the README and the user docs. The grill asks about each Surface a change touches. |
| `.gitignore` lines | The working folders: `.spec-loop/`, `.handoff/`, `.claude/worktrees/` and `.context-backfill/`. They are per machine and never committed. `.context-backfill/` holds the Answer sheet of the Context backfill. Setup also creates `.handoff/`, where `handoff` saves. Under Sidecar Steering they go to the repo's git exclude file instead, with `.claude/settings.local.json`. |
| A `## Agent skills` block in `CLAUDE.md` | The pointer. `CLAUDE.md` loads every session; `docs/skillworks/` does not. The block is a Seed: `seed-agent-skills` builds it, and a second run merges a person's edits. |
| The Marketplace and `enabledPlugins` in `.claude/settings.json` | A fresh clone gets the Plugin on trust, with no install by hand. |
| The allowlist in `.claude/settings.json` | Without it every `gh` and `git push` in the loop stops for a prompt, so the loop is not unattended. It names the Plugin's short commands and the `gh` and `git` calls the loop makes. It lets a skill read its own files, with `Read(~/.claude/plugins/**)` and, when the Marketplace folder sits outside the repo, a read rule for that folder, because a Session run by hand would stop to ask on a read outside the repo. The driver gives a loop Session its own read rule. It names no tool the Suite runs: those are the team's to add. |
| An `attribution` block in `.claude/settings.json`, rewritten from `co-authored-by` every time setup runs | Claude Code credits Claude on each commit and pull request unless `attribution` says otherwise. Its commit credit is always off, because the Plugin's hook adds the credit line when `co-authored-by` says `show`. Its pull request credit is off for `hide` only. The block follows the answer in `loop.json`, so a block someone edited by hand comes back into step. |
| Three trailer rules in `.git/config`, written by the Plugin's hook and not by setup, on the first commit it rewrites in each clone | `trailer.Skillworks-Session.ifExists=addIfDifferent`, `trailer.Co-Authored-By.ifExists=addIfDifferent` and `trailer.Ticket.ifExists=replace`. They make a typed `Ticket` line give way to the hook's, and keep an amend by the same Session from adding a line twice. They sit in the config and not in the command, so a team's allow rule for `git commit` still matches. Setup writes nothing for them. |
| `"promptCacheTtl": "1h"` and `"subagentPromptCacheTtl": "1h"` in `.claude/settings.json` | A loop Session waits on the Suite and on its sub-agents for longer than the default five minutes of prompt cache. With one hour, each ticket reads its prompt from a warm cache and does not pay for a cold one. |
| `"autoMemoryEnabled": false` in `.claude/settings.json` | Every Load comes from the repository. Claude Code keeps memory files under `~/.claude`, on the machine and outside the repository, and loads them into every session. With memory on, one commit steers two machines differently, and a run cannot be read back from what the repository holds. With it off, one commit steers every machine the same way. The memory files stay on disk, so removing the line brings them back. |

## Process

### 1. Seed the Steering

First ask one question: does the work go to a team that does not use Skillworks? Suggest no, so the common answer is one keypress. If the Sidecar already holds `docs/skillworks/loop.json`, an earlier run said yes, so suggest yes instead. The Sidecar is the folder beside the repo's main checkout with `-skillworks` on the end of its name.

Yes turns Sidecar Steering on. Every Steering file, the `## Agent skills` block with its imports, and the settings go into the Sidecar, and the repo's tracked files never change. Sidecar Steering always runs in PR mode, with the files Tracker. With yes, run the seed with the flag:

```bash
seed-steering --sidecar-steering
```

It writes `loop.json` in the Sidecar with `target-branch` as `pr` and `tracker` as `files`. It adds the working folders and `.claude/settings.local.json` to the repo's own git exclude file, and never to `.gitignore`, because `.gitignore` is a file the team tracks. Once the Sidecar holds `loop.json`, a run with no flag seeds the Sidecar too, because the Steering being there is what turns the mode on. With no, run the seed with no flag, as below.

Under Sidecar Steering, every `docs/skillworks/` path in the steps below names the Sidecar's copy. Read each one with `steering-file <path>`, and write each one in the Sidecar, never in the repo. That holds for `adr-folder` in `docs/skillworks/domain.md`, which you read before the seed and write in step 4.

Before you run it, read `adr-folder` from the YAML block at the end of `docs/skillworks/domain.md`, where the file is there and names one. That is an earlier run's answer, and step 4 suggests it. Read it first, because the seed writes `docs/adr` into a file that names none, and that default is not the team's answer.

```bash
seed-steering
```

It copies each seed in [seeds](./seeds) to its place in the repo, and adds the working folders to `.gitignore` where it does not name them yet, and creates `.handoff/` when it is missing. It ends with a `next step:` line, which the report in step 7 names. `loop.json` is written with the remote's default branch as its `target-branch`.

A repo set up before the Steering folder carried the Plugin's name holds its Steering in `docs/agents/`. When `docs/agents/` holds a Steering file and `docs/skillworks/` holds none, `seed-steering` moves the Steering first. It moves each Steering file, the base copies in `docs/agents/.seeds/`, and each file in `docs/agents/` that `suite.json` names, with `git mv` for a file git tracks. It changes those paths in `suite.json`, and changes each `@docs/agents/...` import of a moved file in `CLAUDE.md` to its new path. Every other file in `docs/agents/` stays, so another tool still finds it. Nothing is left at a path it moved. It prints one `moved <old path> to <new path>` line for each file. Show the user every one, so they can put back a file another tool still needs. When both folders hold Steering files, it moves nothing.

It keeps a base copy of each seed in `docs/skillworks/.seeds/`, exactly as it copied it. On a later run it weighs three versions of each file: the base copy, the team's file and the current seed. It prints one line per file:

| Outcome | What happened |
|---|---|
| `wrote` | The seed is new, or the file is missing, even one the team deleted. The file and its base copy are written. |
| `updated` | The team never edited the file, and the seed moved on. The file and its base copy take the new seed, and the diff under the line shows the change. |
| `kept ..., which you edited` | The team edited the file, and the seed did not move. Nothing changes. |
| `kept ..., the same as the seed` | The team's file and its base copy are the same as the seed. Nothing changes. |
| `kept ..., the same as the seed, and brought its base copy up to the seed` | The team's file is the same as the seed, and its base copy is an older seed. The base copy takes the seed. |
| `kept ..., the same as the seed, and wrote its base copy` | The team's file is the same as the seed, and has no base copy. The base copy is written. |
| `merged` | The team edited the file, and the seed moved on in other lines. The seed's change is applied, and the diff under the line shows it. |
| `asks` | The team's edit and the seed's change touch the same lines. Both sides of each overlap are printed, numbered. |
| `kept ..., which differs from the seed` | The file has no base copy, because the repo was set up before base copies existed. The diff against the seed is printed. |
| `kept ..., as you settled it` | The file had no base copy, and the run named it with `--settled`. The file is kept, and its base copy is written. |

Show the user each outcome line and each diff under it. The labels on a diff say what each side holds:

| Outcome | `---` side | `+++` side |
|---|---|---|
| `updated` | `old-seed/`: the old seed, which the team never edited | `new-seed/`: the new seed |
| `merged` | `yours/`: the team's file | `merged/`: the team's file with the seed's change applied |
| `kept ..., which differs from the seed` | `yours/`: the team's file | `seed/`: the current seed |

When a line says `asks` or `kept ..., which differs from the seed`, the script has written nothing, and every other line says what it would do. No file changes until every question is answered. Put each overlap to the user: show the `yours` side, the `seed` side, and a blend you write to fit the repo, and ask which of the three to keep. Ask every question before you change anything. Then run it again with one choice per overlap:

```bash
seed-steering --keep docs/skillworks/domain.md:1=yours --keep docs/skillworks/domain.md:2=seed
```

For a blend, write its text to a file outside the repo, and name the overlap and that file. The script writes the text in place of the overlap's lines. You write nothing into the Steering file yourself:

```bash
seed-steering --blend docs/skillworks/domain.md:1=/tmp/domain-1.md
```

When a line says `kept ..., which differs from the seed`, treat the file as edited. Show the user the diff, and change the file only by the lines they pick. When they have decided, even to take no lines, give the file back so the script writes its base copy, and the merge works from the next run on:

```bash
seed-steering --settled docs/skillworks/domain.md
```

Give the `--keep`, `--blend` and `--settled` choices in one run when they are due. A choice or a blend that names no overlap, or a `--settled` for a file that has a base copy, is refused, and nothing is written.

The user reviews every changed file before they commit. Setup commits nothing.

Expect a permission prompt here on a first run. The allowlist that would clear it is written in step 6, which has not happened yet.

If it stops because the repo has no `origin` remote, stop setup and show the user the commands it printed. Setup refuses a repo with no remote, with either Tracker. A bare repo on a shared drive is enough.

### 2. Ask for the Tracker

Under Sidecar Steering, ask nothing here. The Tracker is `files`, and the seed has written it. Refuse `github`, and say why: an issue on the other team's GitHub would show them Skillworks. Preflight and `seed-agent-skills` refuse it too.

The Tracker is where the team keeps its specs and tickets. Ask the team which one it uses, and offer two answers:

- `github`: GitHub Issues, driven by `gh`. A spec is a parent issue, and its tickets are its sub-issues.
- `files`: Markdown files in `.specs/` in the Sidecar, one folder per spec and one file per ticket. It works with any remote: GitLab, Bitbucket, or a bare repo on a shared drive. It needs no `gh`, and it pushes nothing but the work.

Read `git remote get-url origin`. When it names `github.com`, suggest `github`. Otherwise suggest `files`. So the common answer is one keypress. If `tracker` in `docs/skillworks/loop.json` already names another value, a team's answer from an earlier run, suggest that one instead.

Write the answer into `tracker` in `docs/skillworks/loop.json`, and change no other key.

With `files`, tell the team that `.specs/` sits in the Sidecar, the folder beside the repo's main checkout with `-skillworks` on the end of its name. The Sidecar is a git repo with no remote, so it is never pushed and it serves this machine alone. Every worktree of the repo finds the same Sidecar, and a Session reads it with `tracker-show` and closes a ticket with `tracker-close`.

### 3. Ask for the Target branch

Under Sidecar Steering, ask nothing here. The Target branch is `pr`, and the seed has written it: each spec's work goes to a branch of its own for the other team to review.

The Target branch is the branch the loop Lands each ticket on. Ask the team which one it is, and suggest the remote's default branch, so the common answer is one keypress. `seed-steering` has already written that branch into `docs/skillworks/loop.json`. If `target-branch` there names another value, a team's answer from an earlier run, suggest that one instead.

Offer one other answer: `pr`. With `pr`, you name the branch and open the pull request. For each spec the grill asks you to name the spec's branch, and Skillworks makes it, so you name it by your team's own rule. The grill writes the design there, and the loop Lands each ticket there. Then you open the one pull request from it, and a person reviews and merges it. Pick `pr` when the default branch is protected, or when the team reviews its work through pull requests.

Write the answer into `target-branch` in `docs/skillworks/loop.json`, and change no other key.

### 4. Point CLAUDE.md at the docs

First ask the team where its ADRs go. Every new ADR goes to this one folder, whatever context it is about, and the Domain docs line below names it. Suggest one folder, the first of these that holds:

1. The folder `adr-folder` names in `docs/skillworks/domain.md`, as you read it before step 1. So a second run keeps the team's answer.
2. Else a folder that holds numbered Markdown files and has `adr` or `decision` in its path. A numbered file is named `<number>-<slug>.md`, such as `0001-event-sourced-orders.md`. Match `adr` and `decision` in any letter case. List every such folder you find, and suggest the one with the most files.
3. Else `docs/adr`.

Write the answer into `adr-folder` in the YAML block at the end of `docs/skillworks/domain.md`, and change no other line. Write it as a path from the repo root, with no `/` at its end. Where the file has no YAML block at its end, add one that holds `adr-folder` alone. Preflight in step 5 stops while the setting is missing or empty.

Then build the `## Agent skills` block in `CLAUDE.md`. The block is a Seed, and a script builds it from your answers, so you write none of it yourself:

```bash
seed-agent-skills --tracker <github|files> --adr-folder <adr-folder> --contexts <single|multi>
```

Give the Tracker from step 2, and the folder `adr-folder` names. Under Sidecar Steering the script writes the block into the Sidecar's `CLAUDE.md`, and refuses any Tracker but `files`. Give `--contexts multi` when the repo has `CONTEXT-MAP.md` at its root, and `--contexts single` otherwise. The script imports each rule file in `docs/skillworks/rules/`, and writes the multi-context Domain docs line in the words Context backfill writes when it switches the line.

The block runs from its heading to the next `## ` heading, or to the end of the file. The script changes nothing outside it. It keeps a base copy of the block in `docs/skillworks/.seeds/agent-skills.md`, and on a later run it weighs the block as step 1 weighs a Steering file. It prints the same outcome lines and the same diffs, and names the block by its file, such as `CLAUDE.md`. A missing block, or a missing file, is `wrote`. If the repo has `AGENTS.md` and no `CLAUDE.md`, the script uses `AGENTS.md`, and it never creates the one that is missing when the other exists.

When a line says `asks` or `kept ..., which differs from the seed`, the script has written nothing. Put each question to the user as step 1 does: for each overlap, show the `yours` side, the `seed` side, and a blend you write to fit the repo, and ask which of the three to keep. For a block with no base copy, show the diff, change the block only by the lines they pick, and then settle it. Ask every question before you change anything. Then run it again with the same answers and every choice at once:

```bash
seed-agent-skills --tracker github --adr-folder docs/adr --contexts single --keep CLAUDE.md:1=yours --blend CLAUDE.md:2=/tmp/claude-2.md
seed-agent-skills --tracker github --adr-folder docs/adr --contexts single --settled CLAUDE.md
```

A choice or a blend that names no overlap, or a `--settled` for a block that has a base copy, is refused, and nothing is written.

### 5. Preflight and labels

```bash
skillworks-preflight
```

It reads the Tracker and the Target branch from `docs/skillworks/loop.json`, and checks that `CLAUDE.md` imports each rule in `docs/skillworks/rules/`. It warns, and does not fail, when another enabled plugin also forces an output style. Safe to run again.

With `github`, it checks `gh`, the login, that `origin` is GitHub, and the Target branch. A branch name must be on the remote and must take a direct push from this login. With `pr`, the default branch must be on the remote, and its protection does not matter. Then it creates the `ready-for-agent` label. It creates only what is missing and never overwrites an existing label.

With `files`, it needs no `gh` and creates no label. It checks that `origin` exists and holds the Target branch, or with `pr`, the remote's default branch.

It runs after the Tracker and the Target branch are written, because it reads `loop.json`, and after the `CLAUDE.md` block is written, because it refuses a rule with no import. Expect a permission prompt here too on a first run.

If it fails, stop and report. Every step below assumes the remote works, and with `github` a working `gh`, and the script is what proves that. The `CLAUDE.md` block step 4 wrote is safe to leave: a second run of setup merges it, so the team fixes the fault and runs setup again.

### 6. Write the settings

Under Sidecar Steering, write the settings below to two files, and never to the repo's `.claude/settings.json`, which the team owns. Write them to the Sidecar's `.claude/settings.json`, which the driver hands to every loop Session. Write the same to `.claude/settings.local.json` in the main checkout, because the developer's own sessions run there and never read the Sidecar's file. Merge into each file as below. Ask no credit question, and run `set-co-authored-by hide`: the team the work goes to sees no credit for Claude, so the command turns Claude Code's own credit off in both files, whatever the answer.

Copy [settings.json](./settings.json) to `.claude/settings.json`. The Marketplace `path` in it is a placeholder. Write the folder that holds this Plugin's `.claude-plugin/marketplace.json`, which is three folders above this skill's base directory. Write it relative to the repo root, starting `./`, when it sits inside the repo, and in full otherwise.

When the Marketplace folder sits outside the repo, add a read rule for it to `permissions.allow`: `Read(//<the folder in full>/**)`. Write the folder with forward slashes, and on Windows write its drive as a folder, so `C:\tools\skillworks\plugins` becomes `Read(//c/tools/skillworks/plugins/**)`. A skill reads its own files from the Plugin's folder, and a read outside the repo needs a rule that allows it. `Read(~/.claude/plugins/**)` in the file already opens an installed Plugin's folder. The driver gives each loop Session a read rule for the Plugin's folder itself, so these rules are for a Session run by hand: without them, `tdd` stops to ask before it reads its guides.

If the file exists, merge:

- Keep `$schema` as the file has it, and add it where missing.
- Add the missing entries to `permissions.allow`. Remove none.
- Add `extraKnownMarketplaces.skillworks` and `enabledPlugins["skillworks@skillworks"]` where missing. If either is there with another value, show the user both and ask which to keep.
- Add `promptCacheTtl` and `subagentPromptCacheTtl` where missing, each as `"1h"`. Where the team set one, keep its value.
- Settle `autoMemoryEnabled` by the table below.
- Leave every other key as the user has it.

| What is there | What to do |
|---|---|
| No `autoMemoryEnabled`, or no file | Set it to `false`. Leave every other key alone. |
| `false` | Nothing. |
| `true` | Show the user the key and what it costs: memory files on each machine steer the loop, so it runs differently from one machine to the next. Ask which to keep. Never change it without asking. |

Ask the team one question: should commits and pull requests credit Claude? The one answer covers both. Offer two answers. On a first run, suggest `hide`, so the common answer is one keypress. If `co-authored-by` in `docs/skillworks/loop.json` already names an answer, a team's answer from an earlier run, suggest that one instead.

- `hide`: `set-co-authored-by hide`. No commit and no pull request credits Claude.
- `show`: `set-co-authored-by show`. The Plugin's hook adds the credit line to each commit Claude makes, and Claude Code's own pull request credit applies.

The command writes the answer into `co-authored-by` in `docs/skillworks/loop.json`, and rewrites the `attribution` block of `.claude/settings.json` from the answer every time it runs. Claude Code's commit credit is always off, because the hook adds the line itself. A block someone edited by hand comes back into step.

Settle `co-authored-by` and `attribution` with `set-co-authored-by` and never by hand. Never write `"attribution": false`: Claude Code before v2.1.281 rejects it and skips the whole file, which drops the allowlist and the Plugin with it.

Read the allowlist out loud to the user before writing, the read rules among it, and read the memory line and the credit answer out with it. The allowlist lets an unattended loop run `git push` and `gh issue close` with no prompt, which is the whole point and also the whole risk. The memory line turns off the memory files Claude Code keeps on this machine, for this repository only. They should agree to all three knowingly, in this one pass, with no second prompt. Then write the file, and run `set-co-authored-by` with the answer.

Without Sidecar Steering, leave `.claude/settings.local.json` alone. Do not read it and do not change it. The `/config` memory toggle writes to the user's own settings, which lose to `.claude/settings.json`, so a local file that turns memory back on was put there on purpose.

Write nothing under `~/.claude`.

### 7. Report

Say what was written and what was kept. Under Sidecar Steering, say that each path below sits in the Sidecar and not in the repo, and that the repo's tracked files did not change. Say where each Steering file lives:

- `docs/skillworks/rules/`: `comments.md`, `determinism.md`, `file-placement.md`, `testing.md` and `words.md`. `CLAUDE.md` imports each one, so they load into every session.
- `docs/skillworks/`: `issue-tracker.md`, `domain.md`, `adr-format.md`, `placement-checks.md`, `review-standards.md`, `review-architecture.md`, `review-spec.md`, `suite.json`, `loop.json` and `surfaces.md`. A skill reads each one when it needs it.

Say that auto-memory is off for this repository, or that the user chose to keep it on. Say whether commits and pull requests credit Claude. Then tell them what the team fills in before the loop can finish a ticket:

- `docs/skillworks/suite.json`: the checks that prove their code, each with a command, the folder it runs in, and optionally a readiness command with its message. A check that passes keeps a Proof of its inputs, and does not run again until one of them changes. A check may also name the paths it cannot be changed by, as `"ignores": ["docs", "web"]`: each is a git pathspec from the repo root. A path left off only costs a run, so a slow check is the one to give `ignores`. A check may name an `image`, a Dockerfile in `docs/skillworks/`, to run in a container. A check that did not run says so in the Suite output, and names its Proof. `runs` says how many times a red Suite runs before the loop believes it. It starts at 1, and a team with tests that flake raises it. `baseline` names one quick command, such as a build of the solution, with its `folder` and optionally an `image`: the command a run checks the Target branch with before the Cut, so a red Target branch stops the run before any Session starts. Until it names a check, the loop stops with the Suite not ready.
- The allowlist: each tool the Suite runs, such as a build or a test runner, so the loop can run it without a prompt.
- The rules' settings, as the team settles them.

Name the next step that the `next step:` line of `seed-steering` printed. For a repo with a history and no glossary, it names `/skillworks:context-backfill` first: it fills `CONTEXT.md` or `CONTEXT-MAP.md`, and the folder `adr-folder` names, once from the code and the history, and writes nothing until a person accepts it. A repo has a history when a commit touches a file setup does not write, and no glossary when it has no `CONTEXT.md` and no `CONTEXT-MAP.md` at its root. Then, and for every other repo first, name `/skillworks:architecture-tests`. It turns the rules into tests the team owns: it writes each test red first, proves it green, then fills `docs/skillworks/suite.json`, both tables of `docs/skillworks/placement-checks.md` and the allowlist. A team runs it again when it adds a language or a rule. Under Sidecar Steering the `next step:` line names `/skillworks:grill` in place of `/skillworks:architecture-tests`, which refuses there, because a test that reads Steering would reach the team's build.

Then tell them the loop is ready:

```
/skillworks:grill  →  /skillworks:spec-loop <spec#>
```

The grill runs `/skillworks:to-spec` itself once the user confirms the shape it settled, so it hands them a
spec number rather than a command to type.

Mention they can edit the Steering by hand at any time. Re-running this skill repairs, and brings in a newer seed after a Plugin update.

End the report with a link to the usage docs, so the team finds them at the moment it needs them: [Using Skillworks](https://github.com/MalcolmMcNeely/skillworks/blob/main/docs/usage/README.md)
