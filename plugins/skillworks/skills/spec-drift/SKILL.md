---
name: spec-drift
description: Compare the work a spec loop produced against what the spec asked for, and record the gaps with the spec.
disable-model-invocation: true
---

# Spec Drift

The last step of `/skillworks:spec-loop`. Every ticket passed its own acceptance criteria. Nothing so far has asked whether the pile of them is what the spec wanted.

Two arguments: the spec's number, then the commit the loop started from. The number is the spec's issue number with the GitHub Tracker, or the number its folder under `.specs/` opens with, with the files Tracker.

`tracker` in `docs/agents/loop.json` names the Tracker, and `docs/agents/issue-tracker.md` says how to read each one. Read the spec and its tickets through those docs, and make no call of your own that they do not name.

`/skillworks:spec-drift 42 a1b2c3d`

Every ticket Lands straight on the Target branch, and its Job branch goes when it passes, so no branch is left to diff. The base commit is the only thing that says where the work began. The loop stores it in `.spec-loop/<spec>/base.sha` and passes it in. If it was not passed, read that file. If that is missing too, stop and ask — do not guess a base.

The Target branch is `target-branch` in `docs/agents/loop.json`. When that says `spec`, the spec names its own branch: under its `## Branch` heading with GitHub, and as `branch` in its frontmatter with files.

## Process

1. Read the spec in full, then every one of its tickets with how each was closed.
   - **GitHub**: the spec issue, then its sub-issues with their Closing notes.
   - **Files**: `spec.md` in the spec's folder on `origin/<target>`, then each file in its `tickets/` folder there, with its `## Closing note`. The remote is where the tickets Landed, and this checkout may not hold them.

2. Get the accumulated diff. The tickets Landed on the remote, so read `origin/<target>`, and not the branch this checkout holds:

   ```bash
   git diff <base>..origin/<target>
   git log --oneline <base>..origin/<target>
   ```

3. Classify every user story and implementation decision in the spec as one of:

   - **Done** — the diff delivers it
   - **Partial** — started, not finished
   - **Missing** — no code for it
   - **Contradicts** — the code does something the spec ruled out

   Then list **Unrequested** — behaviour in the diff that no story and no ticket asked for.

   Judge against the **spec**, not against the tickets. A ticket that drifted still passed its own criteria, which is exactly why this step exists.

4. Look for the failure no per-ticket check can see: two tickets that introduced competing names or competing abstractions for one concept. The project glossary is the arbiter.

5. Record the report with the spec. Its first line is `## Drift report`, with either Tracker, because the loop finds the report by that heading and reads it back.
   - **GitHub**: post it as a comment on the spec issue.
   - **Files**: there is no issue to comment on, so the report goes at the end of the spec's `spec.md`, under that heading. Write it to a file outside the repo, such as in `$(mktemp -d)`, and record it:

     ```bash
     tracker-publish drift <spec> <file>
     ```

     The command pushes it to the spec's branch on the remote and takes the place of any earlier report. It writes through an index of its own, so the checkout stays clean. The loop turns down a drift check that leaves the checkout changed.

6. **Report only. Fix nothing.** A fix is new work and needs its own ticket. Do not close the spec either. With GitHub the human closes it once they have read this report. With files the loop closes it after this step.
