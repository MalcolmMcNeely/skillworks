---
name: skillworks-setup
description: Configure a repo for the Skillworks dev loop — the Tracker, GitHub labels with the github Tracker, the Steering the skills read (rules, tracker docs, review baselines, a starting Suite file), the CLAUDE.md pointer, the Plugin and the permission allowlist the loop needs to run unattended, and auto-memory off. Run once per repo.
disable-model-invocation: true
---

# Skillworks Setup

Write the Steering the Skillworks skills read, and the settings the loop needs. Run it once. Re-run it to repair, or to bring in a newer seed.

The Plugin carries the Machinery: the skills, the scripts, the hooks and the output style. They run from the Plugin, so setup copies none of them. Steering is what the repo tells the loop about itself. Setup copies a starting version of each piece, and the team owns it from then on. A Plugin update never changes it by itself. A second run of setup brings in the newer seed and keeps the team's edits.

The Tracker is where the team keeps its specs and tickets: `github`, for GitHub Issues, or `files`, for committed files in `.specs/` on any remote. Setup asks which one.

Setup refuses a repo with no remote, with either Tracker. The loop Lands every ticket by pushing to `origin`. A bare repo on a shared drive is enough, and `seed-steering` prints the commands that add one.

The outputs:

| Output | Why it exists |
|---|---|
| The `ready-for-agent` label, with `github` only | `/skillworks:to-spec` and `/skillworks:to-tickets` apply it, and `gh issue create` fails on a label that does not exist. Nothing in the loop reads it. |
| `docs/agents/rules/*.md` | The five rules: comments, determinism, file placement, testing and words. The review axes read them. The testing rule holds the team's taste in tests and has no settings. The settings that name what a rule judges start empty, so nothing is judged until the team fills them in: `contexts`, `slices`, `concerns`, `test-roots`, `banned-words` and the words rule's `skip-folders`. The others ship with a default the team can change: `doc-comments`, `clock`, `max-types-per-folder`, `source-files`, `test-files`, the placement rule's `skip-folders`, `banned-folder-names` and `name-map`. |
| `docs/agents/issue-tracker.md`, `docs/agents/domain.md` | One copy of the tracker calls and of where the domain docs live. Without one shared copy each skill carries its own and they drift. |
| `docs/agents/placement-checks.md`, `review-standards.md`, `review-architecture.md` | What the review axes judge against. Each review file holds the Plugin's own list for its axis, and a team's own checks, which start empty. The placement checks start with no command listed. A team names the exact commands that prove placement, each with its folder and anything to run first, and the architecture review runs those and nothing else. |
| `docs/agents/suite.json` | The Suite: what green means for this repo's code. It starts with no checks, and a Suite with no checks is not ready, so the loop stops until the team names its checks. |
| `docs/agents/loop.json` | The loop's settings. `tracker` is `github` or `files`, and setup asks which. `target-branch` is the branch the loop Lands on, or `spec` for one pull request per spec. It starts as the remote's default branch, and setup asks the team to confirm it. |
| `docs/agents/surfaces.md` | The Surfaces: the places a change can have to reach besides its code. It starts with the README and the user docs. The grill asks about each Surface a change touches. |
| `.gitignore` lines | The loop's working folders: `.spec-loop/`, `.handoff/` and `.claude/worktrees/`. They are per machine and never shared. Setup also creates `.handoff/`, where `handoff` saves. |
| A `## Agent skills` block in `CLAUDE.md` | The pointer. `CLAUDE.md` loads every session; `docs/agents/` does not. |
| The Marketplace and `enabledPlugins` in `.claude/settings.json` | A fresh clone gets the Plugin on trust, with no install by hand. |
| The allowlist in `.claude/settings.json` | Without it every `gh` and `git push` in the loop stops for a prompt, so the loop is not unattended. It names the Plugin's short commands and the `gh` and `git` calls the loop makes, the pull request calls of a `spec` Target branch among them. It names no tool the Suite runs: those are the team's to add. |
| An `attribution` block in `.claude/settings.json`, when the team hides the credit | Claude Code credits Claude on each commit and pull request unless `attribution` says otherwise. The choice is the team's, so it goes in the file the team commits, and every developer and every loop Session follows it. |
| `"promptCacheTtl": "1h"` and `"subagentPromptCacheTtl": "1h"` in `.claude/settings.json` | A loop Session waits on the Suite and on its sub-agents for longer than the default five minutes of prompt cache. With one hour, each ticket reads its prompt from a warm cache and does not pay for a cold one. |
| `"autoMemoryEnabled": false` in `.claude/settings.json` | Every Load comes from the repository. Claude Code keeps memory files under `~/.claude`, on the machine and outside the repository, and loads them into every session. With memory on, one commit steers two machines differently, and a run cannot be read back from what the repository holds. With it off, one commit steers every machine the same way. The memory files stay on disk, so removing the line brings them back. |

## Process

### 1. Seed the Steering

```bash
seed-steering
```

It copies each seed in [seeds](./seeds) to its place in the repo, and adds the working folders to `.gitignore` where it does not name them yet, and creates `.handoff/` when it is missing. `loop.json` is written with the remote's default branch as its `target-branch`.

It keeps a base copy of each seed in `docs/agents/.seeds/`, exactly as it copied it. On a later run it weighs three versions of each file: the base copy, the team's file and the current seed. It prints one line per file:

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

When a line says `asks` or `kept ..., which differs from the seed`, the script has written nothing, and every other line says what it would do. No file changes until every question is answered. Put each overlap to the user: show the `yours` side and the `seed` side, and ask which to keep. Ask every question before you change anything. Then run it again with one choice per overlap:

```bash
seed-steering --keep docs/agents/domain.md:1=yours --keep docs/agents/domain.md:2=seed
```

When a line says `kept ..., which differs from the seed`, treat the file as edited. Show the user the diff, and change the file only by the lines they pick. When they have decided, even to take no lines, give the file back so the script writes its base copy, and the merge works from the next run on:

```bash
seed-steering --settled docs/agents/domain.md
```

Give the `--keep` and `--settled` choices in one run when both are due. A choice that names no overlap, or a `--settled` for a file that has a base copy, is refused, and nothing is written.

The user reviews every changed file before they commit. Setup commits nothing.

Expect a permission prompt here on a first run. The allowlist that would clear it is written in step 6, which has not happened yet.

If it stops because the repo has no `origin` remote, stop setup and show the user the commands it printed. Setup refuses a repo with no remote, with either Tracker. A bare repo on a shared drive is enough.

### 2. Ask for the Tracker

The Tracker is where the team keeps its specs and tickets. Ask the team which one it uses, and offer two answers:

- `github`: GitHub Issues, driven by `gh`. A spec is a parent issue, and its tickets are its sub-issues.
- `files`: committed Markdown files in `.specs/`, one folder per spec and one file per ticket. It works on any remote: GitLab, Bitbucket, or a bare repo on a shared drive. It needs no `gh`.

Read `git remote get-url origin`. When it names `github.com`, suggest `github`. Otherwise suggest `files`. So the common answer is one keypress. If `tracker` in `docs/agents/loop.json` already names another value, a team's answer from an earlier run, suggest that one instead.

Write the answer into `tracker` in `docs/agents/loop.json`, and change no other key.

With `files`, tell the team that `.specs/` is committed and cannot be gitignored. Each job builds in a worktree of its own, and a worktree cannot see a gitignored folder. A ticket that its job cannot see cannot be built or closed.

### 3. Ask for the Target branch

The Target branch is the branch the loop Lands each ticket on. Ask the team which one it is, and suggest the remote's default branch, so the common answer is one keypress. `seed-steering` has already written that branch into `docs/agents/loop.json`. If `target-branch` there names another value, a team's answer from an earlier run, suggest that one instead.

Offer one other answer: `spec`. With `spec`, each spec gets a branch of its own, `spec/<slug>`, and the team reviews the spec as one pull request to the default branch. The loop marks the pull request ready for review, and a person merges it. Pick `spec` when the default branch is protected, or when the team reviews its work through pull requests.

Write the answer into `target-branch` in `docs/agents/loop.json`, and change no other key.

### 4. Point CLAUDE.md at the docs

Add this block to `CLAUDE.md`. Create the file if it is missing. If the block is already there, update it in place — never append a second copy. Leave every other section alone.

```markdown
## Agent skills

### Issue tracker

GitHub Issues, driven by the `gh` CLI. A spec is a parent issue; its tickets are its sub-issues. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Steering

The rules in `docs/agents/rules/`, the review baselines in `docs/agents/`, and the Suite in `docs/agents/suite.json`. The team owns them.

### Rules

The rules load into every session through these imports. Each one lives in `docs/agents/rules/`.

@docs/agents/rules/comments.md
@docs/agents/rules/determinism.md
@docs/agents/rules/file-placement.md
@docs/agents/rules/testing.md
@docs/agents/rules/words.md
```

The imports are what load the rules, so keep one for each file in `docs/agents/rules/`. An import path is relative to `CLAUDE.md`.

With `files`, write the Issue tracker line as: committed files in `.specs/`, one folder per spec and one file per ticket. See `docs/agents/issue-tracker.md`, under The files Tracker.

If the repo has `CONTEXT-MAP.md`, write the Domain docs line as multi-context: `CONTEXT-MAP.md` and `docs/adr/` at the repo root, and one `CONTEXT.md` per context.

If the repo has `AGENTS.md` and no `CLAUDE.md`, edit `AGENTS.md` instead. Never create the one that is missing when the other exists.

### 5. Preflight and labels

```bash
skillworks-preflight
```

It reads the Tracker and the Target branch from `docs/agents/loop.json`, and checks that `CLAUDE.md` imports each rule in `docs/agents/rules/`. It warns, and does not fail, when another enabled plugin also forces an output style. Safe to run again.

With `github`, it checks `gh`, the login, that `origin` is GitHub, and the Target branch. A branch name must be on the remote and must take a direct push from this login. With `spec`, the default branch must be on the remote, and its protection does not matter. Then it creates the `ready-for-agent` label. It creates only what is missing and never overwrites an existing label.

With `files`, it needs no `gh` and creates no label. It checks that `origin` exists and holds the Target branch, or with `spec`, the remote's default branch.

It runs after the Tracker and the Target branch are written, because it reads `loop.json`, and after the `CLAUDE.md` block is written, because it refuses a rule with no import. Expect a permission prompt here too on a first run.

If it fails, stop and report. Every step below assumes the remote works, and with `github` a working `gh`, and the script is what proves that. The `CLAUDE.md` block step 4 wrote is safe to leave: a second run of setup updates it in place, so the team fixes the fault and runs setup again.

### 6. Write the settings

Copy [settings.json](./settings.json) to `.claude/settings.json`. The Marketplace `path` in it is a placeholder. Write the folder that holds this Plugin's `.claude-plugin/marketplace.json`, which is three folders above this skill's base directory. Write it relative to the repo root, starting `./`, when it sits inside the repo, and in full otherwise.

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

Ask the team one question: should commits and pull requests credit Claude? Offer two answers, and suggest `hide`, so the common answer is one keypress:

- `hide`: `set-attribution hide` writes an `attribution` block with empty strings for `commit` and `pr`, so Claude Code adds no credit.
- `show`: `set-attribution show` writes no `attribution` block, so Claude Code's own default applies.

An `attribution` block already in the file is the team's earlier answer. `set-attribution` keeps it, whatever the answer, and says so. Tell the user it was kept.

Settle `attribution` with `set-attribution` and never by hand. Never write `"attribution": false`: Claude Code before v2.1.281 rejects it and skips the whole file, which drops the allowlist and the Plugin with it.

Read the allowlist out loud to the user before writing, and read the memory line and the attribution answer out with it. The allowlist lets an unattended loop run `git push` and `gh issue close` with no prompt, which is the whole point and also the whole risk. The memory line turns off the memory files Claude Code keeps on this machine, for this repository only. They should agree to all three knowingly, in this one pass, with no second prompt. Then write the file, and run `set-attribution` with the answer.

Leave `.claude/settings.local.json` alone. Do not read it and do not change it. The `/config` memory toggle writes to the user's own settings, which lose to `.claude/settings.json`, so a local file that turns memory back on was put there on purpose.

Write nothing under `~/.claude`.

### 7. Report

Say what was written and what was kept. Say where each Steering file lives:

- `docs/agents/rules/`: `comments.md`, `determinism.md`, `file-placement.md`, `testing.md` and `words.md`. `CLAUDE.md` imports each one, so they load into every session.
- `docs/agents/`: `issue-tracker.md`, `domain.md`, `placement-checks.md`, `review-standards.md`, `review-architecture.md`, `suite.json`, `loop.json` and `surfaces.md`. A skill reads each one when it needs it.

Say that auto-memory is off for this repository, or that the user chose to keep it on. Say whether commits and pull requests credit Claude, or that an earlier `attribution` block was kept. Then tell them what the team fills in before the loop can finish a ticket:

- `docs/agents/suite.json`: the checks that prove their code, each with a command, the folder it runs in, and optionally a readiness command with its message. A check that passes keeps a Proof of its inputs, and does not run again until one of them changes. A check may also name the paths it cannot be changed by, as `"ignores": ["docs", "web"]`: each is a git pathspec from the repo root. A path left off only costs a run, so a slow check is the one to give `ignores`. A check may name an `image`, a Dockerfile in `docs/agents/`, to run in a container. A check that did not run says so in the Suite output, and names its Proof. `runs` says how many times a red Suite runs before the loop believes it. It starts at 1, and a team with tests that flake raises it. Until it names a check, the loop stops with the Suite not ready.
- The allowlist: each tool the Suite runs, such as a build or a test runner, so the loop can run it without a prompt.
- The rules' settings, as the team settles them.

Name `/skillworks:architecture-tests` as the next step after setup. It turns the rules into tests the team owns: it writes each test red first, proves it green, then fills `docs/agents/suite.json`, both tables of `docs/agents/placement-checks.md` and the allowlist. A team runs it again when it adds a language or a rule.

Then tell them the loop is ready:

```
/skillworks:grill-with-docs  →  /skillworks:spec-loop <spec#>
```

The grill runs `/skillworks:to-spec` itself once the user confirms the shape it settled, so it hands them a
spec number rather than a command to type.

Mention they can edit the Steering by hand at any time. Re-running this skill repairs, and brings in a newer seed after a Plugin update.

End the report with a link to the usage docs, so the team finds them at the moment it needs them: [Using Skillworks](https://github.com/MalcolmMcNeely/skillworks/blob/main/docs/usage/README.md)
