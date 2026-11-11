---
name: spec-loop
argument-hint: "<spec-number> [--dry-run | --bypass]"
description: Drive a published spec to done, one ticket at a time, each in its own fresh session.
disable-model-invocation: true
---

# Spec Loop

Take a spec that is already published on the tracker and run it to completion.

The argument is the spec's number: its issue number with the GitHub Tracker, or the number its folder under `.specs/` opens with, such as `7` for `0007-local-tracker`, with the files Tracker. `tracker` in `steering-file docs/skillworks/loop.json` names the Tracker, and `steering-file docs/skillworks/issue-tracker.md` says how to read each one. If no number was given, list the open specs and ask which one.

Read each Steering file with `steering-file <path>`, and never from disk. It prints the file from disk, or from the Steering branch when this branch holds none. When the file is missing, it says so.

Once the spec is known, typing the command is the whole of the user's consent. Ask nothing else until step 3, and there only the close offer, which a spec in PR mode never gets.

## Process

### 1. Check the spec

Read the spec in full: the issue and its comments on GitHub, or `spec.md` on the remote's Target branch with the files Tracker. It must be **open** — the loop needs it open as the parent of its tickets. If it is closed, stop and say so.

Cut no tickets yourself. A spec with no tickets has them cut by the driver, as its first step.

### 2. Hand over to the driver

Run, in the background:

```bash
spec-loop <spec-number>
```

Tell the user the log path: `.spec-loop/<spec-number>/loop.log`.

**Do not implement any ticket yourself.** The script owns the loop. It picks the next unblocked ticket and starts a fresh `claude -p` session for each one. If you pick instead, the choice moves back inside a model, which is the one thing this design exists to avoid. A script reads the blocking edges and picks the same ticket every time. A model can skip a blocker, lose its place as its context fills, and still sound sure.

### 3. Report

When the script exits, read `.spec-loop/<spec-number>/loop.log` and say which tickets closed.

Each ticket Lands on its Target branch. `target-branch` in `steering-file docs/skillworks/loop.json` names it for every spec, or says `pr`, and then each spec names its own branch under `## Branch` and is reviewed as one pull request.

Name each Departure first, then each Choice and each Hand check, from the list at the end of the log to the user, one by one, before any close offer and at an early stop as well.

**A clean finish** is the log's `END` line. The driver decides it and you read it: the driver writes `END` only when every Verdict in the drift report is Done or In step, after the one round in which it files and builds a Gap ticket of its own, when every rename the Name check that follows finds is made, in a rename ticket the driver files and builds and a Name re-check that confirms each one, and when the full run of the Suite, which runs once and last, is green. Do not judge the drift report yourself, so you and the driver never disagree. `/skillworks:spec-drift` records that report with the spec, and the driver reads it back from the Tracker, a comment on the spec issue with GitHub or the `## Drift report` section of `spec.md` with files, and keeps it at `.spec-loop/<spec-number>/drift.md`. Its `DRIFT` line in the log names that file. A log with no `END` line is not a clean finish: a `STOP` line names each Contradicts the count found, each Gap left after the round, or each rename the Name re-check found not made, and a `RED` line names each check the full run found red.

Unrequested work never stops the loop, and the driver writes a `NOTE  Unrequested:` line for each item. Name each of those items to the user, one by one, before any close offer, so they read them at the moment they decide. Then:

- **With the files Tracker**, make no offer. The driver closed the spec itself after the full run, by a commit on the Target branch, and its `CLOSE` line in the log says so. Say that. With `pr`, its `PR` line names the spec's branch. Tell the user to open the pull request from that branch, and that a person reviews and merges it.
- **With the GitHub Tracker and a branch name**, make one offer, and only this one: close the spec. Close it on a yes. The decision is the user's, because closing the spec is where a feature is declared done.
- **With the GitHub Tracker and `pr`**, make no offer. The driver closed the spec issue itself after the full run, with a comment, and its `CLOSE` line in the log says so. Say that. Its `PR` line names the spec's branch. Tell the user to open the pull request from that branch, and that a person reviews and merges it. Never open, mark or merge the pull request yourself: the developer opens it, by the team's own rules.

**Anything else is an early stop.** The script stops on the first failure. Say what failed and give the log path. The close offer belongs to a clean finish alone. The failed ticket stays open, with the reason in the log and the session's stderr beside it. Its worktree stays too, so the broken state can be read; the log names the path. The fix is a human one, unless the stop names Denials, as below.

Re-running the same command is a **real run**, every time. It first Keeps each leftover worktree: it commits what the worktree held, removes the worktree, and renames its branch to `spec-loop/<spec-number>/ticket-<n>-kept-<k>`, naming each branch in a `KEPT` line of the log. Then it starts the first open ticket again from the Target branch, with a fresh build. A Kept build stays on its branch and the rerun never reads it, so a rerun after a long build pays for that build again.

**A stop that names Denials gets one rerun in bypass mode.** A Denial is a tool call Claude Code turned down because the Session had no permission for it, such as a write under `.claude/`. The stop names each one on a `Denial:` line: the `FAIL` line of a step, or the `STOP` line of a Cut or a check that recorded nothing. When it names at least one, run, in the background:

```bash
spec-loop <spec-number> --bypass
```

Run it once, and never again for the same stop. Stop and tell the user, naming each Denial from the first stop, when:

- the bypass rerun stops too, or
- Claude Code will not start in bypass mode, because bypass mode is turned off here.

A stop that names no Denial never gets a `--bypass` rerun. Its cause lies somewhere else, and bypass mode does not fix it.

To see what a run would do, read `spec_loop.py` and run `spec-loop <spec-number> --dry-run`, which starts no session and Keeps nothing. Start a real run only to finish the spec, in the background and with no time limit: a limit that ends the driver mid-step leaves a half-built attempt for the next run to Keep.
