---
name: spec-loop
description: Turn a published spec into tickets, then drive those tickets to done one at a time, each in its own fresh session.
disable-model-invocation: true
---

# Spec Loop

Take a spec that is already published on the tracker and run it to completion.

The argument is the spec's issue number. If none was given, list the open `SPEC:` issues and ask which one.

Once the spec is known, typing the command is the whole of the user's consent. Ask nothing else until the close offer in step 4.

## Process

### 1. Check the spec

Read the spec issue in full, comments included. It must be **open** — the loop needs it open as the parent of its tickets. If it is closed, stop and say so.

If it already has sub-issues, the breakdown has happened. Skip to step 3.

### 2. Break it into tickets

Call the Skill tool with "skillworks:to-tickets", passing the spec's issue number and telling it to skip its approval questions.

Let it finish. Every ticket must come back as a **sub-issue of the spec** — that parentage is what stops one person's loop picking up another person's tickets.

### 3. Hand over to the driver

Run, in the background:

```bash
spec-loop <spec-number>
```

Tell the user the log path: `.spec-loop/<spec-number>/loop.log`.

**Do not implement any ticket yourself.** The script owns the loop. It picks the next unblocked ticket and starts a fresh `claude -p` session for each one. If you pick instead, the choice moves back inside a model, which is the one thing this design exists to avoid. A script reads the blocking edges and picks the same ticket every time. A model can skip a blocker, lose its place as its context fills, and still sound sure.

### 4. Report

When the script exits, read `.spec-loop/<spec-number>/loop.log` and say which tickets closed.

**A clean finish** takes two things together: the log reaches its `END` line, and the drift report `/skillworks:spec-drift` posted as a comment on the spec issue lists nothing Missing, Partial or Contradicts. A drift check that found gaps still exits 0, so the log alone never settles it — read the comment. Then make one offer, and only this one: close the spec. Close it on a yes. The decision is the user's, because closing the spec is where a feature is declared done.

**Anything else is an early stop.** The script stops on the first failure. Say what failed and give the log path. The close offer belongs to a clean finish alone. The failed ticket stays open, with the reason in the log and the session's stderr beside it. Its worktree stays too, so the broken state can be read; the log names the path. The fix is a human one.

Re-running the same command is a **real run**, every time. It first Keeps each leftover worktree: it commits what the worktree held, removes the worktree, and renames its branch to `spec-loop/<spec-number>/ticket-<n>-kept-<k>`, naming each branch in a `KEPT` line of the log. Then it starts the first open ticket again from `main`, with a fresh build. A Kept build stays on its branch and the rerun never reads it, so a rerun after a long build pays for that build again.

To see what a run would do, read `spec_loop.py` and run `spec-loop <spec-number> --dry-run`, which starts no session and Keeps nothing. Start a real run only to finish the spec, in the background and with no time limit: a limit that ends the driver mid-step leaves a half-built attempt for the next run to Keep.
