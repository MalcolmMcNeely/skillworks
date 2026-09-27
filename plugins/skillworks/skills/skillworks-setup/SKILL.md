---
name: skillworks-setup
description: Configure a repo for the Skillworks dev loop — GitHub labels, the Steering the skills read (rules, tracker docs, review baselines, a starting Suite file), the CLAUDE.md pointer, the Plugin and the permission allowlist the loop needs to run unattended, and auto-memory off. Run once per repo.
disable-model-invocation: true
---

# Skillworks Setup

Write the Steering the Skillworks skills read, and the settings the loop needs. Run it once. Re-run it to repair, or to bring in a newer seed.

The Plugin carries the Machinery: the skills, the scripts, the hooks and the output style. They run from the Plugin, so setup copies none of them. Steering is what the repo tells the loop about itself. Setup copies a starting version of each piece, and the team owns it from then on. A Plugin update never changes it by itself. A second run of setup brings in the newer seed and keeps the team's edits.

Skillworks is **GitHub only**. There is no tracker question, because there is no other answer. If a repo tracks work somewhere else, it cannot run this loop.

The outputs:

| Output | Why it exists |
|---|---|
| The `ready-for-agent` label | `/skillworks:to-spec` and `/skillworks:to-tickets` apply it, and `gh issue create` fails on a label that does not exist. Nothing in the loop reads it. |
| `docs/agents/rules/*.md` | The four rules: comments, determinism, file placement and words. The review axes read them. Their settings start empty, so nothing is judged until the team fills them in. |
| `docs/agents/issue-tracker.md`, `docs/agents/domain.md` | One copy of the tracker calls and of where the domain docs live. Without one shared copy each skill carries its own and they drift. |
| `docs/agents/placement-checks.md`, `smell-baseline.md`, `arrangement-baseline.md` | What the review axes judge against. The placement checks start with no command listed. A team names the exact commands that prove placement, each with its folder and anything to run first, and the architecture review runs those and nothing else. |
| `docs/agents/suite.json` | The Suite: what green means for this repo's code. It starts with no checks, and a Suite with no checks is not ready, so the loop stops until the team names its checks. |
| `docs/agents/loop.json` | The loop's settings. `target-branch` is the branch the loop Lands on, and it starts as the remote's default branch. |
| `.gitignore` lines | The loop's working folders: `.spec-loop/`, `.handoff/` and `.claude/worktrees/`. They are per machine and never shared. |
| A `## Agent skills` block in `CLAUDE.md` | The pointer. `CLAUDE.md` loads every session; `docs/agents/` does not. |
| The Marketplace and `enabledPlugins` in `.claude/settings.json` | A fresh clone gets the Plugin on trust, with no install by hand. |
| The allowlist in `.claude/settings.json` | Without it every `gh` and `git push` in the loop stops for a prompt, so the loop is not unattended. It names the Plugin's short commands and the `gh` and `git` calls the loop makes. It names no tool the Suite runs: those are the team's to add. |
| `"autoMemoryEnabled": false` in `.claude/settings.json` | Every Load comes from the repository. Claude Code keeps memory files under `~/.claude`, on the machine and outside the repository, and loads them into every session. With memory on, one commit steers two machines differently, and a run cannot be read back from what the repository holds. With it off, one commit steers every machine the same way. The memory files stay on disk, so removing the line brings them back. |

## Process

### 1. Seed the Steering

```bash
seed-steering
```

It copies each seed in [seeds](./seeds) to its place in the repo, and adds the working folders to `.gitignore` where it does not name them yet. `loop.json` is written with the remote's default branch as its `target-branch`.

It keeps a base copy of each seed in `docs/agents/.seeds/`, exactly as it copied it. On a later run it weighs three versions of each file: the base copy, the team's file and the current seed. It prints one line per file:

| Outcome | What happened |
|---|---|
| `wrote` | The seed is new, or the file was never there. The file and its base copy are written. |
| `updated` | The team never edited the file, and the seed moved on. The file and its base copy take the new seed. |
| `kept ..., which you edited` | The team edited the file, and the seed did not move. Nothing changes. |
| `kept ..., the same as the seed` | Nothing changed on either side. |
| `merged` | The team edited the file, and the seed moved on in other lines. The seed's change is applied, and the diff under the line shows it. |
| `asks` | The team's edit and the seed's change touch the same lines. Both sides of each overlap are printed, numbered. |
| `left out` | The team deleted the file. It stays deleted. |
| `kept ..., which differs from the seed` | The file has no base copy, because the repo was set up before base copies existed. The diff against the seed is printed. |
| `kept ..., as you settled it` | The file had no base copy, and the run named it with `--settled`. The file is kept, and its base copy is written. |

Show the user each outcome line and each diff under a `merged` line.

When a line says `asks`, the script has written nothing, and every other line says what it would do. Put each overlap to the user: show the `yours` side and the `seed` side, and ask which to keep. Ask every question before you change anything. Then run it again with one choice per overlap:

```bash
seed-steering --keep docs/agents/domain.md:1=yours --keep docs/agents/domain.md:2=seed
```

When a line says `kept ..., which differs from the seed`, treat the file as edited. Show the user the diff, and change the file only by the lines they pick. When they have decided, even to take no lines, give the file back so the script writes its base copy, and the merge works from the next run on:

```bash
seed-steering --settled docs/agents/domain.md
```

Give the `--keep` and `--settled` choices in one run when both are due. A choice that names no overlap, or a `--settled` for a file that has a base copy, is refused, and nothing is written.

The user reviews every changed file before they commit. Setup commits nothing.

Expect a permission prompt here on a first run. The allowlist that would clear it is written in step 4, which has not happened yet.

### 2. Preflight and labels

```bash
skillworks-preflight
```

It checks `gh`, the login, that `origin` is GitHub, and the Target branch that `docs/agents/loop.json` names. A branch name must be on the remote and must take a direct push from this login. With `spec`, the default branch must be on the remote, and its protection does not matter. Then it creates the `ready-for-agent` label. It warns, and does not fail, when another enabled plugin also forces an output style. It creates only what is missing and never overwrites an existing label. Safe to run again.

It runs after the seeding, because it reads `loop.json`. Expect a permission prompt here too on a first run.

If it fails, stop and report. Every step below assumes the repo is a GitHub clone with a working `gh`, and the script is what proves that.

### 3. Point CLAUDE.md at the docs

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
@docs/agents/rules/words.md
```

The imports are what load the rules, so keep one for each file in `docs/agents/rules/`. An import path is relative to `CLAUDE.md`.

If the repo has `CONTEXT-MAP.md`, write the Domain docs line as multi-context: `CONTEXT-MAP.md` and `docs/adr/` at the repo root, and one `CONTEXT.md` per context.

If the repo has `AGENTS.md` and no `CLAUDE.md`, edit `AGENTS.md` instead. Never create the one that is missing when the other exists.

### 4. Write the settings

Copy [settings.json](./settings.json) to `.claude/settings.json`. The Marketplace `path` in it is a placeholder. Write the folder that holds this Plugin's `.claude-plugin/marketplace.json`, which is three folders above this skill's base directory. Write it relative to the repo root, starting `./`, when it sits inside the repo, and in full otherwise.

If the file exists, merge:

- Add the missing entries to `permissions.allow`. Remove none.
- Add `extraKnownMarketplaces.skillworks` and `enabledPlugins["skillworks@skillworks"]` where missing. If either is there with another value, show the user both and ask which to keep.
- Settle `autoMemoryEnabled` by the table below.
- Leave every other key as the user has it.

| What is there | What to do |
|---|---|
| No `autoMemoryEnabled`, or no file | Set it to `false`. Leave every other key alone. |
| `false` | Nothing. |
| `true` | Show the user the key and what it costs: memory files on each machine steer the loop, so it runs differently from one machine to the next. Ask which to keep. Never change it without asking. |

Read the allowlist out loud to the user before writing, and read the memory line out with it. The allowlist lets an unattended loop run `git push` and `gh issue close` with no prompt, which is the whole point and also the whole risk. The memory line turns off the memory files Claude Code keeps on this machine, for this repository only. They should agree to both knowingly, in this one pass, with no second prompt.

Leave `.claude/settings.local.json` alone. Do not read it and do not change it. The `/config` memory toggle writes to the user's own settings, which lose to `.claude/settings.json`, so a local file that turns memory back on was put there on purpose.

Write nothing under `~/.claude`.

### 5. Report

Say what was written and what was kept. Say where each Steering file lives:

- `docs/agents/rules/`: `comments.md`, `determinism.md`, `file-placement.md` and `words.md`. `CLAUDE.md` imports each one, so they load into every session.
- `docs/agents/`: `issue-tracker.md`, `domain.md`, `placement-checks.md`, `smell-baseline.md`, `arrangement-baseline.md`, `suite.json` and `loop.json`. A skill reads each one when it needs it.

Say that auto-memory is off for this repository, or that the user chose to keep it on. Then tell them what the team fills in before the loop can finish a ticket:

- `docs/agents/suite.json`: the checks that prove their code, each with a command, the folder it runs in, and optionally a readiness command with its message. A check that passes keeps a Proof of its inputs, and does not run again until one of them changes. A check may also name the paths it cannot be changed by, as `"ignores": ["docs", "web"]`: each is a git pathspec from the repo root. A path left off only costs a run, so a slow check is the one to give `ignores`. A check may name an `image`, a Dockerfile in `docs/agents/`, to run in a container. A check that did not run says so in the Suite output, and names its Proof. `runs` says how many times a red Suite runs before the loop believes it. It starts at 1, and a team with tests that flake raises it. Until it names a check, the loop stops with the Suite not ready.
- The allowlist: each tool the Suite runs, such as a build or a test runner, so the loop can run it without a prompt.
- The rules' settings, as the team settles them.

Then tell them the loop is ready:

```
/skillworks:grill-with-docs  →  /skillworks:spec-loop <spec#>
```

The grill runs `/skillworks:to-spec` itself once the user confirms the shape it settled, so it hands them a
spec number rather than a command to type.

Mention they can edit the Steering by hand at any time. Re-running this skill repairs, and brings in a newer seed after a Plugin update.

End the report with a link to the usage docs, so the team finds them at the moment it needs them: [Using Skillworks](https://github.com/MalcolmMcNeely/skillworks/blob/main/docs/usage/README.md)
