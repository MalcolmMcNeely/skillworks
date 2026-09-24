---
name: skillworks-setup
description: Configure a repo for the Skillworks dev loop — GitHub labels, the tracker doc the skills read, the CLAUDE.md pointer, the permission allowlist the loop needs to run unattended, auto-memory off, and the skillworks output style. Run once per repo.
disable-model-invocation: true
---

# Skillworks Setup

Write the per-repo configuration the Skillworks skills assume. Run it once. Re-run it to repair.

Skillworks is **GitHub only**. There is no tracker question, because there is no other answer. If a repo tracks work somewhere else, it cannot run this loop.

The outputs:

| Output | Why it exists |
|---|---|
| The `ready-for-agent` label | `/skillworks:to-spec` and `/skillworks:to-tickets` apply it, and `gh issue create` fails on a label that does not exist. Nothing in the loop reads it. |
| `docs/agents/*.md` | One copy of the tracker calls. `/skillworks:to-spec`, `/skillworks:to-tickets`, `/skillworks:implement`, `/skillworks:code-review` and `/wayfinder` all need them. Without one shared copy each skill carries its own and they drift. |
| A `## Agent skills` block in `CLAUDE.md` | The pointer. `CLAUDE.md` loads every session; `docs/agents/` does not. |
| `.claude/settings.json` | The permission allowlist. Without it every `gh` and `git push` in the loop stops for a prompt, so the loop is not unattended. |
| `.claude/output-styles/skillworks.md`, set as `outputStyle` in `.claude/settings.json` | The output style. Without it every clone and every loop session uses whatever style its own machine sets, so the loop reports differently from one machine to the next. |
| `"autoMemoryEnabled": false` in `.claude/settings.json` | Every Load comes from the repository. Claude Code keeps memory files under `~/.claude`, on the machine and outside the repository, and loads them into every session. With memory on, one commit steers two machines differently, and a run cannot be read back from what the repository holds. With it off, one commit steers every machine the same way. The memory files stay on disk, so removing the line brings them back. |

## Process

### 1. Preflight and labels

```bash
skillworks-preflight
```

It checks `gh`, the login, that `origin` is GitHub, that the default branch is `main` and that the loop may push to it, then creates the `ready-for-agent` label. It warns, and does not fail, when another enabled plugin also forces an output style. It creates only what is missing and never overwrites an existing label. Safe to run again.

Expect a permission prompt here on a first run. The allowlist that would clear it is written in step 4, which has not happened yet.

If it fails, stop and report. Every step below assumes the repo is a GitHub clone with a working `gh`, and the script is what proves that.

### 2. Write the tracker docs

Copy the two seeds in this skill folder to `docs/agents/`, unchanged:

| Seed | Destination |
|---|---|
| [issue-tracker.md](./issue-tracker.md) | `docs/agents/issue-tracker.md` |
| [domain.md](./domain.md) | `docs/agents/domain.md` |

If a destination already exists, show the user the difference and let them choose. Never overwrite their edits without asking.

### 3. Point CLAUDE.md at them

Add this block to `CLAUDE.md`. Create the file if it is missing. If the block is already there, update it in place — never append a second copy. Leave every other section alone.

```markdown
## Agent skills

### Issue tracker

GitHub Issues, driven by the `gh` CLI. A spec is a parent issue; its tickets are its sub-issues. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
```

If the repo has `AGENTS.md` and no `CLAUDE.md`, edit `AGENTS.md` instead. Never create the one that is missing when the other exists.

### 4. Write the permission allowlist and the memory line

Copy [settings.json](./settings.json) to `.claude/settings.json`.

If the file exists, merge: add the missing entries to `permissions.allow`, settle `autoMemoryEnabled` by the table below, and leave everything else as the user has it.

| What is there | What to do |
|---|---|
| No `autoMemoryEnabled`, or no file | Set it to `false`. Leave every other key alone. |
| `false` | Nothing. |
| `true` | Show the user the key and what it costs: memory files on each machine steer the loop, so it runs differently from one machine to the next. Ask which to keep. Never change it without asking. |

Read the allowlist out loud to the user before writing, and read the memory line out with it. The allowlist lets an unattended loop run `git push` and `gh issue close` with no prompt, which is the whole point and also the whole risk. The memory line turns off the memory files Claude Code keeps on this machine, for this repository only. They should agree to both knowingly, in this one pass, with no second prompt.

Leave `.claude/settings.local.json` alone for this key. Do not read it and do not change it. The `/config` memory toggle writes to the user's own settings, which lose to `.claude/settings.json`, so a local file that turns memory back on was put there on purpose.

Write nothing under `~/.claude`.

### 5. Write and set the output style

Copy [skillworks.md](./skillworks.md) to `.claude/output-styles/skillworks.md`, unchanged. If the destination already exists, show the user the difference and let them choose. Never overwrite their edits without asking.

Then read `outputStyle` in `.claude/settings.json`:

| What is there | What to do |
|---|---|
| No `outputStyle`, or no file | Set it to `skillworks`. Create the file if it is missing. Leave every other key alone. |
| `skillworks` | Nothing. |
| Any other style | Show the user their style and `skillworks` side by side, and ask which to keep. Never change it without asking. |

Then read `outputStyle` in `.claude/settings.local.json`. `/config` saves a style there, and that file wins over `.claude/settings.json` on this machine. If it sets a style other than `skillworks`, show the user both side by side and ask which to keep. If they pick `skillworks`, remove `outputStyle` from `.claude/settings.local.json` and leave every other key alone.

### 6. Report

Say what was written and what was skipped. Say which output style the repo now sets. Say that auto-memory is off for this repository, or that the user chose to keep it on. A new style file loads only when Claude Code starts, so tell them to restart it. Then tell them the loop is ready:

```
/skillworks:grill-with-docs  →  /skillworks:spec-loop <spec#>
```

The grill runs `/skillworks:to-spec` itself once the user confirms the shape it settled, so it hands them a
spec number rather than a command to type.

Mention they can edit `docs/agents/*.md` by hand later. Re-running this skill is only for repair.
