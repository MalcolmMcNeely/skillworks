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

A list of items can follow the base commit, separated by commas. The loop gives one when it checks the Gaps again after the Gap ticket Lands:

`/skillworks:spec-drift 42 a1b2c3d S2, D1, The user docs`

Given a list, judge only those items, and write Verdicts for those alone. Every other step runs as usual. The loop counts only the items it asked about, so a Verdict for any other item counts for nothing.

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

3. Give every user story and implementation decision in the spec one Verdict. A story is `S<n>` and a decision is `D<n>`, by its number in the spec's list:

   - **Done** — the diff delivers it
   - **Partial** — started, not finished
   - **Missing** — no code for it
   - **Contradicts** — the code does something the spec ruled out

   Judge against the **spec**, not against the tickets. A ticket that drifted still passed its own criteria, which is exactly why this step exists. Testing Decisions get no Verdict, because the Suite already proves them.

4. Give every Surface the spec names one Verdict, by its bold name. A Surface is a place a change can have to reach besides the code that does the work, such as the README or the user docs. The spec's Surfaces section names each one the change touches, with what it has to say once the change Lands. Read each Surface on `origin/<target>`, at the path the spec gives or at its "Where it lives" in `docs/agents/surfaces.md`:

   - **In step** — it says what the spec asked
   - **Out of step** — it says less, or says something the code no longer does

   A spec whose Surfaces section says "None" has no Surface to judge.

5. List **Unrequested** work: behaviour in the diff that no story and no ticket asked for.

6. Look for the failure no per-ticket check can see: two tickets that introduced competing names or competing abstractions for one concept. The project glossary is the arbiter.

7. Write the report. The loop reads its lists, so their shape is fixed:

   - The first line is `## Drift report`.
   - The `### Verdicts` list comes next. Each line is `- <item>: <Verdict>`, one line per item, and every item of the spec gets exactly one. Given a list of items, every item in the list gets exactly one, and no other item gets any. The loop counts them: an item with no Verdict, or with two, is a Gap, like a Missing one.
   - After the Verdict, every Verdict other than Done or In step carries one sentence of reason, on the same line.
   - The prose follows: what each Partial, Missing and Contradicts lacks or breaks, then a `### Surfaces` heading with what each Out of step Surface lacks, then the glossary notes from step 6.
   - The `### Unrequested` list comes last, one item per line. With nothing Unrequested it says `- None`.

   ```markdown
   ## Drift report

   ### Verdicts

   - S1: Done
   - S2: Partial. The stop line names the Contradicts but not the Gaps beside it.
   - D1: Missing. No code reads the report's Verdicts.
   - D2: Contradicts. The driver closes the spec when a Gap is left.
   - The user docs: Out of step. `the-loop.md` does not say what a Gap is.

   S2 is half there: ...

   ### Surfaces

   The user docs: ...

   ### Unrequested

   - A helper that trims the log's lines to 80 characters.
   ```

8. Record the report with the spec. Its first line is `## Drift report`, with either Tracker, because the loop finds the report by that heading and reads it back.
   - **GitHub**: post it as a comment on the spec issue.
   - **Files**: there is no issue to comment on, so the report goes at the end of the spec's `spec.md`, under that heading. Write it to a file outside the repo, such as in `$(mktemp -d)`, and record it:

     ```bash
     tracker-publish drift <spec> <file>
     ```

     The command pushes it to the spec's branch on the remote and takes the place of any earlier report. It writes through an index of its own, so the checkout stays clean. The loop turns down a drift check that leaves the checkout changed.

9. **Report only. Fix nothing.** A fix is new work and needs its own ticket. The loop files the Gaps you find as a ticket of its own. Do not close the spec either. With GitHub the human closes it once they have read this report. With files the loop closes it after this step, when the count finds nothing owed.
