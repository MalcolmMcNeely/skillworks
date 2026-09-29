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

Given a list, judge only those items, and write Verdicts for those alone. Every other step runs as usual, and reads the same commits as the first check. The loop counts only the items it asked about, so a Verdict for any other item counts for nothing.

Every ticket Lands straight on the Target branch, and its Job branch goes when it passes, so no branch is left to diff. The base commit is the only thing that says where the work began, and it bounds the search for the spec's commits. The loop stores it in `.spec-loop/<spec>/base.sha` and passes it in. If it was not passed, read that file. If that is missing too, stop and ask — do not guess a base.

The **spec's commits** are the commits after the base commit whose `Ticket:` trailer names one of the spec's tickets, the Gap ticket and the rename ticket among them. A commit with no `Ticket:` trailer is never one of them, whoever made it, and neither is a commit that names another spec's ticket. Other loops and hand commits Land on the same Target branch, so the range from the base commit holds work that is not this spec's.

The Target branch is `target-branch` in `docs/agents/loop.json`. When that says `spec`, the spec names its own branch: under its `## Branch` heading with GitHub, and as `branch` in its frontmatter with files.

## Process

1. Read the spec in full, then every one of its tickets with how each was closed.
   - **GitHub**: the spec issue, then its sub-issues with their Closing notes.
   - **Files**: `spec.md` in the spec's folder on `origin/<target>`, then each file in its `tickets/` folder there, with its `## Closing note`. The remote is where the tickets Landed, and this checkout may not hold them.

2. Get the spec's commits. This one command prints them, oldest first, each with its patch and its `Ticket:` trailer. It fetches the Target branch and reads `origin/<target>`, and not the branch this checkout holds, because the tickets Landed on the remote:

   ```bash
   spec-commits <spec> <base>
   ```

   Build no search of your own, such as a `git log` over the range. The command is how the loop, the re-check and a hand run all read the same commits.

3. Give every user story and implementation decision in the spec one Verdict. A story is `S<n>` and a decision is `D<n>`, by its number in the spec's list:

   - **Done** — the Target branch delivers it
   - **Partial** — started, not finished
   - **Missing** — no code for it
   - **Contradicts** — the code does something the spec ruled out

   Judge the Target branch as it stands, on `origin/<target>`. The spec's commits show where the work is, and the files on the Target branch decide the Verdict. Work that reached the Target branch another way, by a hand fix or by another spec, counts toward Done. Code from any source that does what the spec ruled out is Contradicts.

   Judge against the **spec**, not against the tickets. A ticket that drifted still passed its own criteria, which is exactly why this step exists. Testing Decisions get no Verdict, because the Suite already proves them.

4. Give every Surface the spec names one Verdict, by its bold name. A Surface is a place a change can have to reach besides the code that does the work, such as the README or the user docs. The spec's Surfaces section names each one the change touches, with what it has to say once the change Lands. Read each Surface on `origin/<target>`, at the path the spec gives or at its "Where it lives" in `docs/agents/surfaces.md`:

   - **In step** — it says what the spec asked
   - **Out of step** — it says less, or says something the code no longer does

   A spec whose Surfaces section says "None" has no Surface to judge.

   The README is the one exception. When `docs/agents/surfaces.md` holds a Surface headed `## The README`, outside a code fence, judge the README on every spec, as `The README`, even when the spec names no README item or says "None". Read it on `origin/<target>`, at that Surface's "Where it lives". A link, path or command in the README that the spec's commits removed, renamed or moved makes it Out of step, and the reason names that line. When the spec has a README item, the one Verdict judges that item too. The loop counts this Verdict, so a README you skip is a Gap. Given a list of items without `The README`, do not judge it.

5. List **Unrequested** work: behaviour in the spec's commits that no story and no ticket asked for. Look nowhere else, so another spec's work and a hand commit never show up here. List an item only when it still stands on `origin/<target>`, because a later commit may have taken it out.

6. Look for the failure no per-ticket check can see: two tickets that introduced competing names or competing abstractions for one concept. Look only in the spec's commits, and name a pair only when both still stand on `origin/<target>`. The project glossary is the arbiter.

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

8. Record the report with the spec. Its first line is `## Drift report`, with either Tracker, because the loop finds the report by that heading and reads it back. Write it with the Write tool to `.spec-loop/<spec>/drift-report.md` in this checkout, and record it with this one command, whichever the Tracker:

   ```bash
   tracker-publish drift <spec> .spec-loop/<spec>/drift-report.md
   ```

   Git ignores `.spec-loop/`, so the file leaves the checkout clean. Write nowhere outside the checkout, and make no temp folder: a loop Session has no permission for either, and nobody is there to give it.

   - **GitHub**: the command posts the report as a new comment on the spec issue, and prints the comment's URL. A second run adds a second comment, and the loop reads the last one.
   - **Files**: the command pushes the report to the end of the spec's `spec.md` on the remote, and takes the place of any earlier report. It writes through an index of its own, so the checkout stays clean. The loop turns down a drift check that leaves the checkout changed.

9. **Report only. Fix nothing.** A fix is new work and needs its own ticket. The loop files the Gaps you find as a ticket of its own. Do not close the spec either. With GitHub the human closes it once they have read this report. With files the loop closes it after this step, when the count finds nothing owed.
