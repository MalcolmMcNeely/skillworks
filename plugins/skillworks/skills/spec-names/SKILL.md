---
name: spec-names
description: Read a spec's own commits against the glossary, list every name whose meaning moved and every concept two tickets named two ways, and record the Name report with the spec.
disable-model-invocation: true
---

# Spec Names

The Name check. `/skillworks:spec-loop` runs it after the drift check and its Gap round, so it sees every name the spec brought in, the Gap build's too. The drift check judges whether the work is there. This judges one thing only: whether the names still say what the code means.

Two arguments: the spec's number, then the commit the loop started from. The number is the spec's issue number with the GitHub Tracker, or the number its folder under `.specs/` opens with, with the files Tracker.

`/skillworks:spec-names 42 a1b2c3d`

The base commit bounds the search for the spec's commits. If it was not passed, read `.spec-loop/<spec>/base.sha`. If that is missing too, stop and ask. Do not guess a base.

A third argument, the rename ticket, makes this the Name re-check: see [The Name re-check](#the-name-re-check). Without one, do everything down to it and stop there.

`tracker` in `docs/agents/loop.json` names the Tracker, and `docs/agents/issue-tracker.md` says how to record the report with each one. The Target branch is `target-branch` in `docs/agents/loop.json`. When that says `spec`, the spec names its own branch: under its `## Branch` heading with GitHub, and as `branch` in its frontmatter with files.

## What you read

Two things, and nothing else. A small context keeps the judge sharp, and one finding is all this step owes.

1. **The spec's commits.** They are the commits after the base commit whose `Ticket:` trailer names one of the spec's tickets, the Gap ticket and the rename ticket among them. A commit with no `Ticket:` trailer is never one of them, and neither is a commit that names another spec's ticket, so a name another spec or a person brought in is never yours to judge. This one command prints them, oldest first, each with its patch and its trailer, so the trailer shows which ticket brought each name in. It fetches the Target branch and reads `origin/<target>`, because the tickets Landed on the remote:

   ```bash
   spec-commits <spec> <base>
   ```

   Do not read the range from the base commit, and build no search of your own over it. Other loops and hand commits Land on the same Target branch, and their names are not this spec's.

2. **The glossary of each context the spec's commits touch.** `CONTEXT-MAP.md` at the repo root names each context, the paths it owns and its glossary. A repo with one context has one `CONTEXT.md` at its root. Read each glossary on `origin/<target>`.

Read nothing else: not the spec, not its tickets, not the drift report, and not the code outside the spec's commits. A name is judged by what the spec's commits make it mean and by what the glossary says it means. The one read beyond them is the check in [What you list](#what-you-list) that a name still stands.

## What you list

Every finding is a rename. A rename is never "Optional", and never a matter of taste: a name that says something the code no longer does is a defect, and so is one concept under two names. The loop treats every rename you list as work owed, and asks no one whether to make it, so list only what must change.

1. **A name whose meaning moved.** The spec's commits changed what a type, function, field, file or glossary word does, and the name stayed. A comment edited above a declaration whose name did not change is the sign to look for. Name the old name and say what it now means.
2. **A concept two tickets named two ways.** Two of the spec's commits with two `Ticket:` trailers brought in two names for one thing. Name both, and say which one the glossary uses. When the glossary has no word for it, write `no glossary word` on the line, and name the one the code and the spec use most. The loop reads those words and tells a person the word needs settling.

A name the glossary lists under _Avoid_ is a finding too, when the spec's commits brought it in.

**List a name only when it still stands on the Target branch.** The patches show each commit as it was, so a name one commit brought in may be one a later commit renamed or removed. Before you list a name, confirm it is still there, such as with a search of `origin/<target>`:

```bash
git -C . grep -n -w "<name>" origin/<target>
```

The search starts with `git -C`, because a loop Session's allowlist holds that rule and no rule for a bare `git grep`.

A name that no longer stands is not a finding. For a concept two tickets named two ways, both names have to stand. With one of them gone, the rename is already made.

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

Write it to a file outside the repo, such as in `$(mktemp -d)`, and record it with this one command, whichever the Tracker:

```bash
tracker-publish names <spec> <file>
```

- **GitHub**: the command posts the report as a new comment on the spec issue, and prints the comment's URL. Post nothing on the spec after it, because the loop reads the last comment.
- **Files**: the command pushes the report to the end of the spec's `spec.md`, below the drift report, and takes the place of any earlier Name report. It writes through an index of its own, so the checkout stays clean. The loop turns down a Name check that leaves the checkout changed.

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
