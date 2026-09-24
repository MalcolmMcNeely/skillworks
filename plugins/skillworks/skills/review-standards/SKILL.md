---
name: review-standards
description: Review a ticket's change against this repo's documented coding standards and the smell baseline, and report under a Standards heading.
disable-model-invocation: true
---

# Review: Standards

One axis of the three-axis review. This one asks a single question: **does the code follow the standards this repo has written down?**

The argument is the ticket's issue number.

`/skillworks:review-standards 168`

Two other axes run beside this one, each in a session of its own. Spec asks whether the change is what was asked for. Architecture asks whether the code sits in the right place and points the right way. Neither is this axis's business, so findings that belong to them are dropped rather than reported here.

## What to read

### The change

The loop runs this step before anything is committed, so the change is the working tree:

```bash
git add -N .
git diff HEAD
git diff HEAD --stat
```

If `git diff HEAD` is empty, stop and report that there is nothing to review.

### The standards

Read every file in `.claude/rules/`. The agent wrote this code under those rules, so the review holds it to the same ones. Read any other file the repo uses to say how code is written, such as a `CODING_STANDARDS.md` or a `CONTRIBUTING.md`.

Then read the glossary that claims the changed files. `CONTEXT-MAP.md` says which one, and a word the glossary rejects is a finding on this axis.

## The smell baseline

On top of what the repo writes down, this axis always carries the smell baseline in [`docs/agents/smell-baseline.md`](../../../../docs/agents/smell-baseline.md). Read it yourself. It holds twelve code smells, four test smells beneath them, and the two rules that bind them all.

## What to report

Report per file and hunk where that helps:

1. Every place the change breaches a documented standard. Cite the standard by file and rule, and quote the line it turns on.
2. Every baseline smell. Name the item and quote the hunk.

Mark each finding as a hard breach or a judgement call. A documented standard can be a hard breach. A baseline smell never is.

Keep the whole report under 400 words.

## Fix what you find

This axis edits the worktree, and it should. A finding you can fix, you fix here. The session that read the code is the one that understands the finding, so a one-line rename never waits for a later session to retype it.

Fix only what this axis owns. A finding that belongs to Spec or Architecture is dropped rather than reported here, so it is not yours to fix either.

A finding you judge not worth fixing is named in the report and left, with the reason. A baseline smell is a judgement call, so leaving one is an ordinary answer and not a failure.

The report names every finding either way, and says which ones you fixed.

## How to end the turn

End with the findings under a `## Standards` heading. The driver reads that heading to prove the axis ran, so an axis that found nothing still writes it:

```
## Standards

No findings on this change.
```

A turn that ends without that heading fails the step and stops the loop.
