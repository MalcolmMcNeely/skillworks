---
name: skillworks-setup
description: Configure a repo for the Skillworks dev loop — GitHub labels, the tracker doc the skills read, the CLAUDE.md pointer, and the permission allowlist the loop needs to run unattended. Run once per repo.
disable-model-invocation: true
---

# Skillworks Setup

Write the per-repo configuration the Skillworks skills assume. Run it once. Re-run it to repair.

Skillworks is **GitHub only**. There is no tracker question, because there is no other answer. If a repo tracks work somewhere else, it cannot run this loop.

Four outputs:

| Output | Why it exists |
|---|---|
| The `ready-for-agent` label | `/to-spec` and `/to-tickets` apply it, and `gh issue create` fails on a label that does not exist. Nothing in the loop reads it. |
| `docs/agents/*.md` | One copy of the tracker calls. `/to-spec`, `/to-tickets`, `/implement`, `/code-review` and `/wayfinder` all need them. Without one shared copy each skill carries its own and they drift. |
| A `## Agent skills` block in `CLAUDE.md` | The pointer. `CLAUDE.md` loads every session; `docs/agents/` does not. |
| `.claude/settings.json` | The permission allowlist. Without it every `gh` and `git push` in the loop stops for a prompt, so the loop is not unattended. |

## Process

### 1. Preflight and labels

```bash
bash scripts/skillworks-preflight.sh
```

It checks `gh`, the login, and that `origin` is GitHub, then creates the `ready-for-agent` label. It creates only what is missing and never overwrites an existing label. Safe to run again.

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

### 4. Write the permission allowlist

Copy [settings.json](./settings.json) to `.claude/settings.json`.

If the file exists, merge: add the missing entries to `permissions.allow`, leave everything else as the user has it.

Read the allowlist out loud to the user before writing. It lets an unattended loop run `git push` and `gh issue close` with no prompt, which is the whole point and also the whole risk. They should agree to it knowingly.

### 5. Report

Say what was written and what was skipped. Then tell them the loop is ready:

```
/grill-with-docs  →  /to-spec  →  /spec-loop <spec#>
```

Mention they can edit `docs/agents/*.md` by hand later. Re-running this skill is only for repair.
