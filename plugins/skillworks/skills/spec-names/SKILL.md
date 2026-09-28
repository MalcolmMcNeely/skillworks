---
name: spec-names
description: Read a spec's whole diff against the glossary, list every name whose meaning moved and every concept two tickets named two ways, and record the Name report with the spec.
disable-model-invocation: true
---

# Spec Names

The Name check. `/skillworks:spec-loop` runs it after the drift check and its Gap round, so it sees every name the spec brought in, the Gap build's too. The drift check judges whether the work is there. This judges one thing only: whether the names still say what the code means.

Two arguments: the spec's number, then the commit the loop started from. The number is the spec's issue number with the GitHub Tracker, or the number its folder under `.specs/` opens with, with the files Tracker.

`/skillworks:spec-names 42 a1b2c3d`

If the base commit was not passed, read `.spec-loop/<spec>/base.sha`. If that is missing too, stop and ask. Do not guess a base.

A third argument, the rename ticket, makes this the Name re-check: see [The Name re-check](#the-name-re-check). Without one, do everything down to it and stop there.

`tracker` in `docs/agents/loop.json` names the Tracker, and `docs/agents/issue-tracker.md` says how to record the report with each one. The Target branch is `target-branch` in `docs/agents/loop.json`. When that says `spec`, the spec names its own branch: under its `## Branch` heading with GitHub, and as `branch` in its frontmatter with files.

## What you read

Two things, and nothing else. A small context keeps the judge sharp, and one finding is all this step owes.

1. **The spec's whole diff.** The tickets Landed on the remote, so read `origin/<target>`, and not the branch this checkout holds. The log with each commit's patch shows which ticket brought each name in, by the `Ticket:` trailer on its commit:

   ```bash
   git diff <base>..origin/<target>
   git log -p --reverse <base>..origin/<target>
   ```

2. **The glossary of each context the diff touches.** `CONTEXT-MAP.md` at the repo root names each context, the paths it owns and its glossary. A repo with one context has one `CONTEXT.md` at its root. Read each glossary on `origin/<target>`.

Read nothing else: not the spec, not its tickets, not the drift report, and not the code outside the diff. A name is judged by what the diff makes it mean and by what the glossary says it means.

## What you list

Every finding is a rename. A rename is never "Optional", and never a matter of taste: a name that says something the code no longer does is a defect, and so is one concept under two names. The loop treats every rename you list as work owed, and asks no one whether to make it, so list only what must change.

1. **A name whose meaning moved.** The diff changed what a type, function, field, file or glossary word does, and the name stayed. A comment edited above a declaration whose name did not change is the sign to look for. Name the old name and say what it now means.
2. **A concept two tickets named two ways.** Two commits with two `Ticket:` trailers brought in two names for one thing. Name both, and say which one the glossary uses. When the glossary has no word for it, write `no glossary word` on the line, and name the one the code and the spec use most. The loop reads those words and tells a person the word needs settling.

A name the glossary lists under _Avoid_ is a finding too, when the diff brought it in.

## The report

The loop reads its list, so its shape is fixed:

- The first line is `## Name report`.
- The `### Renames` list comes next. Each line is `- <name or concept>: <why it must change>`, one line per finding, and the why is one sentence.
- With nothing to rename, the list says `- None`.
- Any prose follows the list, under a heading of its own.

```markdown
## Name report

### Renames

- `Batch`: it now names a whole run of tickets, and the glossary calls that a Job.
- Gap and Hole: two tickets named one owed item two ways, and the glossary says Gap.
```

## Recording it

Record the report with the spec. Its first line is `## Name report`, with either Tracker, because the loop finds the report by that heading and reads it back. A finding you only say in this Session is lost.

- **GitHub**: post it as a comment on the spec issue. Post nothing on the spec after it, because the loop reads the last comment.
- **Files**: write it to a file outside the repo, such as in `$(mktemp -d)`, and record it:

  ```bash
  tracker-publish names <spec> <file>
  ```

  The command pushes it to the end of the spec's `spec.md`, below the drift report, and takes the place of any earlier Name report. It writes through an index of its own, so the checkout stays clean. The loop turns down a Name check that leaves the checkout changed.

**Report only. Rename nothing.** A rename is new work, and needs a ticket of its own.

## The Name re-check

The loop files every rename in your report as one rename ticket, builds it, and then runs you again with that ticket as the third argument:

`/skillworks:spec-names 42 a1b2c3d 57`

The ticket is named the way the Tracker names it: the issue number with GitHub, and `<spec>/<ticket>` with files. This time you judge one thing: whether the rename ticket made each rename it lists.

Read two things, and nothing else:

1. **The rename ticket.** Each `###` heading in it is one rename, and the heading is its name. Read it the way `docs/agents/issue-tracker.md` says to read a ticket.
2. **The rename ticket's diff.** Its commits carry its `Ticket:` trailer, `#57` with GitHub and `42/3` with files. Read them on `origin/<target>`:

   ```bash
   git log -p --reverse --grep "^Ticket: <trailer>$" <base>..origin/<target>
   ```

Do not look for new renames. Judge only the ones the ticket lists.

Give each rename one Verdict:

- **Done**: the diff renamed it everywhere the old name stood for the concept.
- **Not done**: it did not, or only in part. Follow it with one sentence saying where the old name still stands.

Record the report with the spec, as above, with `## Name report` as its first line. The `### Verdicts` list comes next, one line per rename, each `- <heading>: <Verdict>`. Write each rename exactly as its heading names it, because the loop matches the two:

```markdown
## Name report

### Verdicts

- Batch: Done
- Gap and Hole: Not done. Hole is still the name in two files.
```

Rename nothing here either. A rename still owed comes to a person.
