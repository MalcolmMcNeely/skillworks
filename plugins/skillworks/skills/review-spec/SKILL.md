---
name: review-spec
description: Review a ticket's change against what its issue asked for, and report the gaps under a Spec heading.
disable-model-invocation: true
---

# Review: Spec

One axis of the three-axis review. This one asks a single question: **is this the change the ticket asked for?**

The argument is the ticket's issue number.

`/skillworks:review-spec 168`

Two other axes run beside this one, each in a session of its own. Standards asks whether the code follows the written rules. Architecture asks whether it sits in the right place. Neither is this axis's business, so a finding that belongs to them is dropped rather than reported here.

Code that follows every rule can still build the wrong thing. That is the failure this axis exists to catch, and it is the one the other two cannot see.

## What to read

### The ticket

Read the ticket in full, its acceptance criteria included. `docs/agents/issue-tracker.md` says how. Read its parent spec too, because a criterion often only makes sense against the job the spec named.

```bash
gh issue view <ticket> --json title,body
```

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

Two things are out of scope, because reporting them makes the axis noise:

- **Standing debt.** Report what this change did, not what the file already was.
- **A criterion another ticket owns.** The ticket names what it leaves to its siblings. Take it at its word.

Where a criterion is deliberately left for later, the ticket says so. Quote that line rather than reporting the gap.

Keep the whole report under 400 words.

## Fix what you find

This axis edits the worktree, and it should. A finding you can fix, you fix here. The session that read the ticket against the change is the one that knows what is missing, so a criterion a few lines short is closed here rather than handed on.

Fix only what this axis owns. A finding that belongs to Standards or Architecture is dropped rather than reported here, so it is not yours to fix either.

A finding you judge not worth fixing is named in the report and left, with the reason. A gap wide enough to be a ticket of its own is of that kind.

The report names every finding either way, and says which ones you fixed.

## How to end the turn

End with the findings under a `## Spec` heading. The driver reads that heading to prove the axis ran, so an axis that found nothing still writes it:

```
## Spec

Every acceptance criterion is delivered. No findings on this change.
```

A turn that ends without that heading fails the step and stops the loop.
