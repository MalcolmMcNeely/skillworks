# Review: Standards

One axis of the three-axis review. This one asks a single question: **does the code follow the standards this repo has written down?**

Two other axes run beside this one, each in a session of its own. Spec asks whether the change is what was asked for. Architecture asks whether the code sits in the right place and points the right way. Neither is this axis's business, so findings that belong to them are dropped rather than reported here.

## Two modes

**Loop mode** is how the loop's review step runs this axis, through `/skillworks:review-standards`. The argument is the ticket, named as its Tracker names it: `docs/agents/issue-tracker.md` says how each Tracker names its tickets. The change is the working tree. This axis edits what it finds, as "Fix what you find" says.

**Report-only mode** is how `/skillworks:review-changes` runs this axis, in a sub-agent. The caller hands over the diff command, the `--stat -M` command, the commit list, and the ticket or spec. Read the change from those commands, and not from the working tree. This axis reports what it finds and edits nothing, so skip "Fix what you find". Every other section holds in both modes.

## What to read

### The change

In report-only mode, run the commands the caller handed over. In loop mode, the step runs before anything is committed, so the change is the working tree:

```bash
git add -N .
git diff HEAD
git diff HEAD --stat
```

If the diff is empty, stop and report that there is nothing to review.

### The standards

Read every file in `docs/agents/rules/`. The agent wrote this code under those rules, so the review holds it to the same ones. Read any other file the repo uses to say how code is written, such as a `CODING_STANDARDS.md` or a `CONTRIBUTING.md`.

Then read the glossary that claims the changed files. `CONTEXT-MAP.md` says which one, and a word the glossary rejects is a finding on this axis.

## The review file

On top of what the repo writes down, this axis always reads its review file, `docs/agents/review-standards.md`. Read it yourself. It holds the smells list and the rules that bind it, the team's own checks, and a "Do not report" list. The team edits that file, so this file holds none of its own. It is the only review file this axis reads.

Apply each team check only to the paths it names. A check that names no paths covers the whole change. Skip every path and every kind of finding that "Do not report" names.

If `docs/agents/review-standards.md` is missing, stop. Tell the user that `docs/agents/review-standards.md` is missing, that `/skillworks:skillworks-setup` writes it, and that nothing was reviewed. End the turn without the `## Standards` heading, so the step fails and the loop stops.

## What to report

Report per file and hunk where that helps:

1. Every place the change breaches a documented standard. Cite the standard by file and rule, and quote the line it turns on.
2. Every baseline smell. Name the item and quote the hunk.
3. Every breach of a team check. Name the check and quote the hunk.
4. Every existing name whose meaning the change moved. A name that no longer says what its code does misleads the next reader, so rename it in the same ticket. The sign to look for is a comment edited above a declaration whose name did not change: the comment moved with the code, and the name was left behind.

Mark each finding as a hard breach or a judgement call. A documented standard can be a hard breach. A baseline smell never is. A team check is what the check says it is. A moved name is always owed: it is fixed like a hard breach, and never left as a nice-to-have.

Keep the whole report under 400 words.

## Fix what you find

This axis edits the worktree, and it should. A finding you can fix, you fix here. The session that read the code is the one that understands the finding, so a one-line rename never waits for a later session to retype it.

Fix only what this axis owns. A finding that belongs to Spec or Architecture is dropped rather than reported here, so it is not yours to fix either.

A hard breach is always fixed and never left. That holds for a breach of a team check marked hard, for a breach of a rule marked hard, and for a moved name. A judgement call may be left, with the reason in the report, and that reason goes on into the Closing note. A baseline smell is a judgement call, so leaving one is an ordinary answer and not a failure.

The report names every finding either way, and says which ones you fixed.

## How to end the turn

End with the findings under a `## Standards` heading. The driver reads that heading to prove the axis ran, so an axis that found nothing still writes it:

```
## Standards

No findings on this change.
```

A turn that ends without that heading fails the step and stops the loop.
