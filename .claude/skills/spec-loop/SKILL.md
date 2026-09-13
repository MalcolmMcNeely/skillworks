---
name: spec-loop
description: Turn a published spec into tickets, then drive those tickets to done one at a time, each in its own fresh session.
disable-model-invocation: true
---

# Spec Loop

Take a spec that is already published on the tracker and run it to completion.

The argument is the spec's issue number. If none was given, list the open `SPEC:` issues and ask which one.

## Process

### 1. Check the spec

Read the spec issue in full, comments included. It must be **open** — the loop needs it open as the parent of its tickets. If it is closed, stop and say so.

If it already has sub-issues, the breakdown has happened. Skip to step 3.

### 2. Break it into tickets

Call the Skill tool with "to-tickets", passing the spec's issue number.

That skill quizzes the user on granularity and blocking edges, and publishes nothing until they approve. Let it finish. Every ticket must come back as a **sub-issue of the spec** — that parentage is what stops one person's loop picking up another person's tickets.

### 3. Hand over to the driver

Confirm the user wants to start. Then run, in the background:

```bash
bash scripts/spec-loop.sh <spec-number>
```

Tell the user the log path: `.spec-loop/<spec-number>/loop.log`.

Use `--dry-run` first if the user wants to see the plan without spending anything.

**Do not implement any ticket yourself.** The script owns the loop. It picks the next unblocked ticket and starts a fresh `claude -p` session for each one. If you pick instead, the choice moves back inside a model, which is the one thing this design exists to avoid. See [agent-patterns-for-the-implement-loop](../../../docs/research/claude/agent-patterns-for-the-implement-loop.md).

### 4. Report

When the script exits, say which tickets closed and whether it stopped early.

The script stops on the first failure. It leaves that ticket open, with the reason in the log and the session's stderr beside it. The fix is a human one. After the fix, re-running the same command resumes from the first open ticket.
