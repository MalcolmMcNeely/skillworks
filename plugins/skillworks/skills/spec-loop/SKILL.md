---
name: spec-loop
description: Turn a published spec into tickets, then drive those tickets to done one at a time, each in its own fresh session.
disable-model-invocation: true
---

# Spec Loop

Take a spec that is already published on the tracker and run it to completion.

The argument is the spec's number: its issue number with the GitHub Tracker, or the number its folder under `.specs/` opens with, such as `7` for `0007-local-tracker`, with the files Tracker. `tracker` in `docs/agents/loop.json` names the Tracker, and `docs/agents/issue-tracker.md` says how to read each one. If no number was given, list the open specs and ask which one.

Once the spec is known, typing the command is the whole of the user's consent. Ask nothing else until step 4, and there only the close offer, which a spec reviewed as a pull request never gets.

## Process

### 1. Check the spec

Read the spec in full: the issue and its comments on GitHub, or `spec.md` on the remote's Target branch with the files Tracker. It must be **open** — the loop needs it open as the parent of its tickets. If it is closed, stop and say so.

If it already has tickets, as sub-issues or as files in its `tickets/` folder, the breakdown has happened. Skip to step 3.

### 2. Break it into tickets

Call the Skill tool with "skillworks:to-tickets", passing the spec's issue number and telling it to skip its approval questions.

Let it finish. Every ticket must come back as a **sub-issue of the spec**, or with the files Tracker as a file in the spec's own `tickets/` folder — that parentage is what stops one person's loop picking up another person's tickets.

### 3. Hand over to the driver

Run, in the background:

```bash
spec-loop <spec-number>
```

Tell the user the log path: `.spec-loop/<spec-number>/loop.log`.

**Do not implement any ticket yourself.** The script owns the loop. It picks the next unblocked ticket and starts a fresh `claude -p` session for each one. If you pick instead, the choice moves back inside a model, which is the one thing this design exists to avoid. A script reads the blocking edges and picks the same ticket every time. A model can skip a blocker, lose its place as its context fills, and still sound sure.

### 4. Report

When the script exits, read `.spec-loop/<spec-number>/loop.log` and say which tickets closed.

Each ticket Lands on its Target branch. `target-branch` in `docs/agents/loop.json` names it for every spec, or says `spec`, and then each spec names its own branch under `## Branch` and is reviewed as one pull request.

**A clean finish** takes two things together: the log reaches its `END` line, and the drift report `/skillworks:spec-drift` posted as a comment on the spec issue lists nothing Missing, Partial or Contradicts. A drift check that found gaps still exits 0, so the log alone never settles it — read the comment. Then:

- **With the files Tracker**, make no offer. The driver closed the spec itself after the drift check, by a commit on the Target branch, and its `CLOSE` line in the log says so. Say that, and name any gap the drift report found.
- **With the GitHub Tracker and a branch name**, make one offer, and only this one: close the spec. Close it on a yes. The decision is the user's, because closing the spec is where a feature is declared done.
- **With the GitHub Tracker and `spec`**, make no offer. The driver has marked the spec's pull request ready for review, and its `READY` line in the log says so. Say that a person reviews and merges it. Never merge it, and never close the spec: the pull request closes the spec when it merges, so the spec is done only when its code is on the default branch.

**Anything else is an early stop.** The script stops on the first failure. Say what failed and give the log path. The close offer belongs to a clean finish alone. The failed ticket stays open, with the reason in the log and the session's stderr beside it. Its worktree stays too, so the broken state can be read; the log names the path. The fix is a human one, unless the stop names Denials, as below.

Re-running the same command is a **real run**, every time. It first Keeps each leftover worktree: it commits what the worktree held, removes the worktree, and renames its branch to `spec-loop/<spec-number>/ticket-<n>-kept-<k>`, naming each branch in a `KEPT` line of the log. Then it starts the first open ticket again from the Target branch, with a fresh build. A Kept build stays on its branch and the rerun never reads it, so a rerun after a long build pays for that build again.

**A stop that names Denials gets one rerun in bypass mode.** A Denial is a tool call Claude Code turned down because the Session had no permission for it, such as a write under `.claude/`. The `FAIL` line names each one on a `Denial:` line. When it names at least one, run, in the background:

```bash
spec-loop <spec-number> --bypass
```

Run it once, and never again for the same stop. Stop and tell the user, naming each Denial from the first stop, when:

- the bypass rerun stops too, or
- Claude Code will not start in bypass mode, because bypass mode is turned off here.

A stop whose `FAIL` line names no Denial never gets a `--bypass` rerun. Its cause lies somewhere else, and bypass mode does not fix it.

To see what a run would do, read `spec_loop.py` and run `spec-loop <spec-number> --dry-run`, which starts no session and Keeps nothing. Start a real run only to finish the spec, in the background and with no time limit: a limit that ends the driver mid-step leaves a half-built attempt for the next run to Keep.
