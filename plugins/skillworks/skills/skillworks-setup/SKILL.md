---
name: skillworks-setup
description: Configure a repo for the Skillworks dev loop — GitHub labels, the Steering the skills read (rules, tracker docs, review baselines, a starting Suite file), the CLAUDE.md pointer, the Plugin and the permission allowlist the loop needs to run unattended, and auto-memory off. Run once per repo.
disable-model-invocation: true
---

# Skillworks Setup

Write the Steering the Skillworks skills read, and the settings the loop needs. Run it once. Re-run it to repair.

The Plugin carries the Machinery: the skills, the scripts, the hooks and the output style. They run from the Plugin, so setup copies none of them. Steering is what the repo tells the loop about itself. Setup copies a starting version of each piece, and the team owns it from then on. A Plugin update never overwrites it.

Skillworks is **GitHub only**. There is no tracker question, because there is no other answer. If a repo tracks work somewhere else, it cannot run this loop.

The outputs:

| Output | Why it exists |
|---|---|
| The `ready-for-agent` label | `/skillworks:to-spec` and `/skillworks:to-tickets` apply it, and `gh issue create` fails on a label that does not exist. Nothing in the loop reads it. |
| `docs/agents/rules/*.md` | The four rules: comments, determinism, file placement and words. The review axes read them. Their settings start empty, so nothing is judged until the team fills them in. |
| `docs/agents/issue-tracker.md`, `docs/agents/domain.md` | One copy of the tracker calls and of where the domain docs live. Without one shared copy each skill carries its own and they drift. |
| `docs/agents/placement-checks.md`, `smell-baseline.md`, `arrangement-baseline.md` | What the review axes judge against. The placement checks start with no command listed. A team names the exact commands that prove placement, each with its folder and anything to run first, and the architecture review runs those and nothing else. |
| `docs/agents/suite.json` | The Suite: what green means for this repo's code. It starts with no checks, and a Suite with no checks is not ready, so the loop stops until the team names its checks. |
| `.gitignore` lines | The loop's working folders: `.spec-loop/`, `.handoff/` and `.claude/worktrees/`. They are per machine and never shared. |
| A `## Agent skills` block in `CLAUDE.md` | The pointer. `CLAUDE.md` loads every session; `docs/agents/` does not. |
| The Marketplace and `enabledPlugins` in `.claude/settings.json` | A fresh clone gets the Plugin on trust, with no install by hand. |
| The allowlist in `.claude/settings.json` | Without it every `gh` and `git push` in the loop stops for a prompt, so the loop is not unattended. It names the Plugin's short commands and the `gh` and `git` calls the loop makes. It names no tool the Suite runs: those are the team's to add. |
| `"autoMemoryEnabled": false` in `.claude/settings.json` | Every Load comes from the repository. Claude Code keeps memory files under `~/.claude`, on the machine and outside the repository, and loads them into every session. With memory on, one commit steers two machines differently, and a run cannot be read back from what the repository holds. With it off, one commit steers every machine the same way. The memory files stay on disk, so removing the line brings them back. |

## Process

### 1. Preflight and labels

```bash
skillworks-preflight
```

It checks `gh`, the login, that `origin` is GitHub, that the default branch is `main` and that the loop may push to it, then creates the `ready-for-agent` label. It warns, and does not fail, when another enabled plugin also forces an output style. It creates only what is missing and never overwrites an existing label. Safe to run again.

Expect a permission prompt here on a first run. The allowlist that would clear it is written in step 4, which has not happened yet.

If it fails, stop and report. Every step below assumes the repo is a GitHub clone with a working `gh`, and the script is what proves that.

### 2. Seed the Steering

```bash
seed-steering
```

It copies each seed in [seeds](./seeds) to its place in the repo, and adds the working folders to `.gitignore` where it does not name them yet. A seed that is missing is written. A seed that is there is kept, and when it differs from the seed the script prints the difference. It never overwrites a file.

Show the user each difference it printed. A difference is what a newer seed says against what the team has. Change a kept file only when the user asks, and only by the lines they pick.

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
```

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

Say what was written and what was kept. Say that auto-memory is off for this repository, or that the user chose to keep it on. Then tell them what the team fills in before the loop can finish a ticket:

- `docs/agents/suite.json`: the checks that prove their code, each with a command, the folder it runs in, and optionally a readiness command with its message. A check may also name the paths that wake it, as `"when": ["scripts/setup.sh", "tests/setup"]`: each is a file or a folder from the repo root, and the check runs only when a ticket's own change touches one of them. A check without `when` runs on every ticket, so a slow check that proves a rarely changed file is the one to give paths. A check that did not run says so in the Suite output. `runs` says how many times a red Suite runs before the loop believes it. It starts at 1, and a team with tests that flake raises it. Until it names a check, the loop stops with the Suite not ready.
- The allowlist: each tool the Suite runs, such as a build or a test runner, so the loop can run it without a prompt.
- The rules' settings, as the team settles them.

Then tell them the loop is ready:

```
/skillworks:grill-with-docs  →  /skillworks:spec-loop <spec#>
```

The grill runs `/skillworks:to-spec` itself once the user confirms the shape it settled, so it hands them a
spec number rather than a command to type.

Mention they can edit the Steering by hand at any time. Re-running this skill is only for repair.
