---
name: spec-simplify-check
argument-hint: "<spec> <base>"
description: Read a spec's own commits for code harder than it has to be, judge them from the four angles of reuse, simplification, efficiency and altitude, and record the Simplify report with the spec.
disable-model-invocation: true
---

# Spec Simplify Check

The Simplify check. `/skillworks:spec-loop` runs it once every ticket of the spec has Landed and the deepening tickets are built, before the drift check. It looks for one thing: code the spec's work made harder than it has to be. The loop files everything you list as one simplify ticket, and builds it like any ticket.

Two arguments: the spec's number, then the commit the loop started from. The number is the spec's issue number with the GitHub Tracker, or the number its folder under `.specs/` opens with, with the files Tracker.

`/skillworks:spec-simplify-check 42 a1b2c3d`

The base commit bounds the search for the spec's commits. If it was not passed, read `.spec-loop/<spec>/base.sha`. If that is missing too, stop and say so. Do not guess a base.

Read each Steering file with `steering-file <path>`, and never by another route. It prints the file from disk. When the file is missing, it says so.

`tracker` in `steering-file docs/skillworks/loop.json` names the Tracker, and `steering-file docs/skillworks/issue-tracker.md` says how to record the report with each one. The Target branch is `target-branch` in `steering-file docs/skillworks/loop.json`. When that says `pr`, the spec names its own branch: under its `## Branch` heading with GitHub, and as `branch` in its frontmatter with files. In PR mode, read the spec for that branch name and for nothing more.

`steering-file docs/skillworks/simplify-check.md` holds the four angles, your team's own checks, and what never to report. `enabled` in the YAML block at its end says whether the check runs. The loop reads it and runs no Simplify check while it says `false`. When you run the check by hand and it says `false`, say so and stop.

If `steering-file docs/skillworks/loop.json`, `steering-file docs/skillworks/issue-tracker.md` or `steering-file docs/skillworks/simplify-check.md` says the file is missing, stop. Tell the user which file is missing, that `/skillworks:skillworks-setup` writes it, and that nothing was judged. Under the spec loop this is work you cannot do, so begin your last message with a line that starts with `BLOCKED` and holds that message: the loop reads that line and stops at once.

## Four rules

- **Hunt no correctness bugs.** The reviews of each ticket and the Suite judged whether the code works. Judge only whether it could be simpler.
- **Never call `/simplify`.** Claude Code's `/simplify` reads the branch's diff and edits it, and its text is not this Plugin's. The angles in the Steering file are the whole of what you judge by.
- **Ask nobody anything.** The check runs with nobody watching. Where a finding is in doubt, leave it out.
- **Report only. Change no code.** A cleanup is new work, and the loop builds it as a ticket of its own.

## What you read

1. **The spec's commits.** They are the commits after the base commit whose `Ticket:` trailer names one of the spec's tickets, the deepening tickets among them. Under Sidecar Steering no trailer counts: the list of Landed commits the loop keeps in the Sidecar names each commit's ticket instead. A commit with no ticket is never one of them, and neither is a commit of another spec's ticket, so code another spec or a person wrote is never yours to judge. This one command prints them, oldest first, each with its patch and its ticket. It fetches the Target branch and reads `origin/<target>`, because the tickets Landed on the remote:

   ```bash
   spec-commits <spec> <base>
   ```

   Do not read the range from the base commit, and build no search of your own over it. Other loops and hand commits Land on the same Target branch, and their work is not this spec's.

   If `spec-commits` refuses, mend what the refusal names and run it again once. If it refuses again, stop, quote the refusal, and say that nothing was judged. Under the spec loop, begin your last message with a line that starts with `BLOCKED` and names the command, as for a missing file.

2. **The code around the spec's commits** on `origin/<target>`, as far as a finding needs: what the codebase already offers for reuse, and the callers of what the spec changed. Under the spec loop, this checkout was just cut from `origin/<target>`, so read it with the Read tool. In a hand run the checkout may be behind, so read a file with `git -C . show origin/<target>:<path>`.

Under the spec loop, run no `git fetch` of your own, even where `steering-file docs/skillworks/issue-tracker.md` names one. The loop fetched the Target branch before it started this Session, and a loop Session has no permission for a bare fetch.

## What you judge

Judge the code the spec's commits wrote or changed from the four angles the Simplify check's Steering file names:

- **Reuse.** Code that writes again what the codebase already has.
- **Simplification.** Code harder than its job.
- **Efficiency.** Code that does work it does not need.
- **Altitude.** Code at the wrong level.

The file says what each angle covers. Apply your team's checks from the file, and leave out what its Do not report list names. Judge only the lines the spec's commits wrote or changed. Code the spec only reads is not a finding.

## The report

The loop reads its `### Findings` list and quotes every line in the simplify ticket, so its shape is fixed:

- The first line is `## Simplify report`.
- The `### Findings` list comes next. Each line is `- <where it is>, <angle>: <the problem>. <the simpler form>.`, one line per finding. `<where it is>` is a path, and a function or a type where one helps. `<angle>` is one of `reuse`, `simplification`, `efficiency` and `altitude`. The loop quotes the line as an acceptance criterion of the ticket, so it says what to change.
- With nothing found, the list says `- None`.
- Write nothing below the list.

```markdown
## Simplify report

### Findings

- `src/orders/intake.py`, `parse_lines`, reuse: it splits each line by hand, and the CSV reader in `src/io/` already does this. Call the CSV reader.
- `src/orders/totals.py`, efficiency: the tax rate is read once for every line. Read it once before the loop.
```

## Recording it

Record the report with the spec. Its first line is `## Simplify report`, with either Tracker, because the loop finds the report by that heading and reads it back. A finding you only say in this Session is lost.

Write it with the Write tool to `.spec-loop/<spec>/simplify-report.md` in this checkout, and record it with this one command, whichever the Tracker:

```bash
tracker-publish simplify-check <spec> .spec-loop/<spec>/simplify-report.md
```

Git ignores `.spec-loop/`, so the file leaves the checkout clean. Write nowhere outside the checkout, and make no temp folder: a loop Session has no permission for either, and nobody is there to give it.

- **GitHub**: the command posts the report as a new comment on the spec issue, and prints the comment's URL. Post nothing on the spec after it, because the loop reads the last comment.
- **Files**: the command writes the report to the end of the spec's `spec.md` in the Sidecar, below any Deepening report and above any drift report, and takes the place of any earlier Simplify report. The Sidecar sits outside the checkout, so the checkout stays clean.

The report is recorded when the command prints the comment's URL, or the path of `spec.md`. If `tracker-publish` refuses, mend what the refusal names and run it again once. If it refuses again, stop, quote the refusal, and say that the report is not recorded. Under the spec loop, begin your last message with a line that starts with `BLOCKED` and names the command, as for a missing file.
