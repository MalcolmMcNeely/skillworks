---
name: review-spec
description: Review a ticket's change against what the ticket asked for, and report the gaps under a Spec heading.
disable-model-invocation: true
---

# Review: Spec

One axis of the three-axis review. This one asks a single question: **is this the change the ticket asked for?**

The argument is the ticket: its issue number with the GitHub Tracker, or `<spec>/<ticket>` with the files Tracker.

`/skillworks:review-spec 168`
`/skillworks:review-spec 7/2`

Two other axes run beside this one, each in a session of its own. Standards asks whether the code follows the written rules. Architecture asks whether it sits in the right place. Neither is this axis's business, so a finding that belongs to them is dropped rather than reported here.

Code that follows every rule can still build the wrong thing. That is the failure this axis exists to catch, and it is the one the other two cannot see.

## What to read

### The ticket

Read the ticket in full, its acceptance criteria included. Read its parent spec too, because a criterion often only makes sense against the job the spec named.

`tracker` in `docs/agents/loop.json` names the Tracker, and `docs/agents/issue-tracker.md` says how to read each one. Read through those docs, and make no call of your own that they do not name.

- **GitHub**: the ticket issue, and the spec issue its parent names.
- **Files**: the ticket's file and the `spec.md` of the folder it sits in. The loop runs this step inside the ticket's worktree, so read both there.

### The review file

This axis always reads its review file, `docs/agents/review-spec.md`. Read it yourself. It holds the team's own checks and a "Do not report" list. The team edits that file, so this skill holds no check of its own. It is the only review file this axis reads.

Apply each team check only to the paths it names. A check that names no paths covers the whole change. A team check is a hard breach or a judgement call, as the check says. Skip every path and every kind of finding that "Do not report" names.

If `docs/agents/review-spec.md` is missing, stop. Tell the user that `docs/agents/review-spec.md` is missing, that `/skillworks:skillworks-setup` writes it, and that nothing was reviewed. End the turn without the `## Spec` heading, so the step fails and the loop stops.

### The change

The loop runs this step before anything is committed, so the change is the working tree:

```bash
git add -N .
git diff HEAD
git diff HEAD --stat
```

If `git diff HEAD` is empty, stop and report that there is nothing to review.

## What to look for

Three kinds of finding, and every one of them quotes the ticket line it turns on:

1. **Missing or partial.** The ticket asked for it and the change does not deliver it, or delivers part of it.
2. **Not asked for.** The change carries behaviour no line of the ticket asked for.
3. **Asked for, built wrong.** The change looks like it delivers the criterion, but the code would not do what the ticket described.

Walk the acceptance criteria one at a time. A criterion with no evidence in the diff is a finding, not a pass.

Then walk the Surfaces. A Surface is a place a change can have to reach besides the code that does the work, such as the README or the user docs. The spec's Surfaces section names each Surface the change touches, with what it has to say once the change Lands. Check the change against each Surface the spec names for this ticket: one the ticket names, or one this ticket's change reaches. Open the Surface at the path the spec gives, or at its "Where it lives" in `docs/agents/surfaces.md`, and read whether it says what this change needs. A Surface left out of step is a Missing or partial finding, and quotes the Surfaces section line it turns on. A spec whose Surfaces section says "None", or that has none, adds nothing here.

Then walk the team checks in `docs/agents/review-spec.md`. A breach of one is a finding. Name the check and quote the hunk it turns on.

Two things are out of scope, because reporting them makes the axis noise:

- **Standing debt.** Report what this change did, not what the file already was.
- **A criterion another ticket owns.** The ticket names what it leaves to its siblings. Take it at its word.

Where a criterion is deliberately left for later, the ticket says so. Quote that line rather than reporting the gap.

Keep the whole report under 400 words.

## Fix what you find

This axis edits the worktree, and it should. A finding you can fix, you fix here. The session that read the ticket against the change is the one that knows what is missing, so a criterion a few lines short is closed here rather than handed on.

Fix only what this axis owns. A finding that belongs to Standards or Architecture is dropped rather than reported here, so it is not yours to fix either.

A hard breach is always fixed and never left. That holds for a breach of a team check marked hard, and for a breach of a rule marked hard. A judgement call may be left, with the reason in the report, and that reason goes on into the Closing note. A gap wide enough to be a ticket of its own is a judgement call of that kind.

The report names every finding either way, and says which ones you fixed.

## How to end the turn

End with the findings under a `## Spec` heading. The driver reads that heading to prove the axis ran, so an axis that found nothing still writes it:

```
## Spec

Every acceptance criterion is delivered. No findings on this change.
```

A turn that ends without that heading fails the step and stops the loop.
