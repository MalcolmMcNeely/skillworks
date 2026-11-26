---
name: spec-deepening-check
argument-hint: "<spec> <base>"
description: Read a spec's own commits for modules the work left shallow, judge each deepening opportunity by the deep-module vocabulary and the deletion test, and record the Deepening report with the spec.
disable-model-invocation: true
---

# Spec Deepening Check

The Deepening check. `/skillworks:spec-loop` runs it once every ticket of the spec has Landed, before the drift check. It looks for one thing: modules the spec's work left shallow, and the refactors that would make them deep. The loop files each Strong candidate you list as a deepening ticket of its own, and builds it like any ticket.

Two arguments: the spec's number, then the commit the loop started from. The number is the spec's issue number with the GitHub Tracker, or the number its folder under `.specs/` opens with, with the files Tracker.

`/skillworks:spec-deepening-check 42 a1b2c3d`

The base commit bounds the search for the spec's commits. If it was not passed, read `.spec-loop/<spec>/base.sha`. If that is missing too, stop and say so. Do not guess a base.

Read each Steering file with `steering-file <path>`, and never by another route. It prints the file from disk. When the file is missing, it says so.

`tracker` in `steering-file docs/skillworks/loop.json` names the Tracker, and `steering-file docs/skillworks/issue-tracker.md` says how to record the report with each one. The Target branch is `target-branch` in `steering-file docs/skillworks/loop.json`. When that says `pr`, the spec names its own branch: under its `## Branch` heading with GitHub, and as `branch` in its frontmatter with files. In PR mode, read the spec for that branch name and for nothing more.

`steering-file docs/skillworks/deepening-check.md` says what counts as Strong, holds your team's own checks, and names what never to report. `limit` in the YAML block at its end is the most deepening tickets the loop files for the spec.

If `steering-file docs/skillworks/loop.json`, `steering-file docs/skillworks/issue-tracker.md`, `steering-file docs/skillworks/domain.md` or `steering-file docs/skillworks/deepening-check.md` says the file is missing, stop. Tell the user which file is missing, that `/skillworks:skillworks-setup` writes it, and that nothing was judged. Under the spec loop this is work you cannot do, so begin your last message with a line that starts with `BLOCKED` and holds that message: the loop reads that line and stops at once.

## Three rules

- **Ask nobody anything.** The check runs with nobody watching. Where a candidate is in doubt, give it a lower strength and go on.
- **Write no HTML report, and open nothing.** The report on the Tracker is the whole output.
- **Report only. Change no code.** A deepening is new work, and the loop builds it as a ticket of its own.

## The vocabulary

Call the Skill tool with "skillworks:codebase-design" for the architecture vocabulary (**module**, **interface**, **depth**, **seam**, **adapter**, **leverage**, **locality**) and its principles. Use those terms exactly in every candidate. Two of its principles decide a candidate:

- **The deletion test.** Would deleting the module concentrate its complexity in one place, or just move it? A module whose deletion concentrates complexity is shallow, and that is the signal you want.
- **The interface is the test surface.** A deepened module is tested through its interface, so a candidate says how the tests change.

## What you read

1. **The spec's commits.** They are the commits after the base commit whose `Ticket:` trailer names one of the spec's tickets. Under Sidecar Steering no trailer counts: the list of Landed commits the loop keeps in the Sidecar names each commit's ticket instead. A commit with no ticket is never one of them, and neither is a commit of another spec's ticket, so code another spec or a person wrote is never yours to judge. This one command prints them, oldest first, each with its patch and its ticket. It fetches the Target branch and reads `origin/<target>`, because the tickets Landed on the remote:

   ```bash
   spec-commits <spec> <base>
   ```

   Do not read the range from the base commit, and build no search of your own over it. Other loops and hand commits Land on the same Target branch, and their work is not this spec's.

   If `spec-commits` refuses, mend what the refusal names and run it again once. If it refuses again, stop, quote the refusal, and say that nothing was judged. Under the spec loop, begin your last message with a line that starts with `BLOCKED` and names the command, as for a missing file.

2. **The glossary of each context the spec's commits touch.** `steering-file docs/skillworks/domain.md` says where this repo keeps its glossaries. Where the repo has a `CONTEXT-MAP.md`, the map says which glossary claims which file. Name each module in the glossary's words.

3. **The ADRs in the folder `adr-folder` names**, in the YAML block at the end of `steering-file docs/skillworks/domain.md`. Read each ADR that touches a module you judge. An ADR records a decision a person made, and the loop never reopens one.

Read the code around the spec's commits on `origin/<target>` as far as a candidate needs: the callers of a module and the module's tests. Under the spec loop, this checkout was just cut from `origin/<target>`, so read it with the Read tool. In a hand run the checkout may be behind, so read a file with `git -C . show origin/<target>:<path>`.

Under the spec loop, run no `git fetch` of your own, even where `steering-file docs/skillworks/issue-tracker.md` names one. The loop fetched the Target branch before it started this Session, and a loop Session has no permission for a bare fetch.

## What you judge

Look for the friction the spec's commits brought in or grew:

- One concept spread over many small modules, so understanding it means moving between them.
- A shallow module: its interface is nearly as complex as what it does.
- A pure function pulled out only to be tested, while the bugs hide in how it is called.
- Modules joined so tightly that each leaks across the seam between them.
- Code the spec added that is hard to test through its interface.

Give each candidate one strength, by what the Deepening check's Steering file says counts as Strong:

- **Strong**: it meets every line of the file's Strong section.
- **Worth exploring**: the friction is real, but it misses a line.
- **Speculative**: it rests on a guess about future work.

Apply your team's checks from the file, and leave out what its Do not report list names.

**A candidate that goes against an ADR is never in the `### Strong` list, whatever its strength.** List it under `### ADR` instead, with the ADR's number and why the candidate goes against it, so a person can decide whether to reopen that ADR.

Rank the Strong candidates, strongest first. The `### Strong` list holds at most `limit` lines, strongest first. A Strong candidate past the limit goes under `### Over the limit`.

## The report

The loop reads its `### Strong` list and files each line as a deepening ticket, so its shape is fixed:

- The first line is `## Deepening report`.
- The `### Strong` list comes next. Each line is `- <module>: <the problem>. <the deepening>.`, one line per candidate, in the glossary's words and the vocabulary above. The loop quotes the line as the ticket's acceptance criterion, so it says what to change.
- With no Strong candidate to file, the list says `- None`.
- Prose follows the list, each part under a heading of its own: `### Over the limit` for the Strong candidates past the limit, `### Worth exploring` and `### Speculative` for the weaker candidates, and `### ADR` for each candidate that goes against an ADR. Leave out a heading with nothing under it.

```markdown
## Deepening report

### Strong

- The order intake module: three shallow modules each parse one part of an order, and every caller calls all three. Fold them into one module whose interface takes the whole order.

### Worth exploring

The pricing adapter has one implementation, so its seam is hypothetical. A second one would make it real.

### ADR

- The ledger writer: folding it into the order intake module goes against ADR-0007, which keeps the ledger behind its own seam.
```

## Recording it

Record the report with the spec. Its first line is `## Deepening report`, with either Tracker, because the loop finds the report by that heading and reads it back. A finding you only say in this Session is lost.

Write it with the Write tool to `.spec-loop/<spec>/deepening-report.md` in this checkout, and record it with this one command, whichever the Tracker:

```bash
tracker-publish deepening-check <spec> .spec-loop/<spec>/deepening-report.md
```

Git ignores `.spec-loop/`, so the file leaves the checkout clean. Write nowhere outside the checkout, and make no temp folder: a loop Session has no permission for either, and nobody is there to give it.

- **GitHub**: the command posts the report as a new comment on the spec issue, and prints the comment's URL. Post nothing on the spec after it, because the loop reads the last comment.
- **Files**: the command writes the report to the end of the spec's `spec.md` in the Sidecar, above any drift report, and takes the place of any earlier Deepening report. The Sidecar sits outside the checkout, so the checkout stays clean.

The report is recorded when the command prints the comment's URL, or the path of `spec.md`. If `tracker-publish` refuses, mend what the refusal names and run it again once. If it refuses again, stop, quote the refusal, and say that the report is not recorded. Under the spec loop, begin your last message with a line that starts with `BLOCKED` and names the command, as for a missing file.
