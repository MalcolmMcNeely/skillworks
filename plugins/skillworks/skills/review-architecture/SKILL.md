---
name: review-architecture
description: Review where a ticket's change sits and which way its dependencies point, against this repo's placement rules and boundary checks, and report under an Architecture heading.
disable-model-invocation: true
---

# Review: Architecture

One axis of the three-axis review. This one asks a single question: **is the code in the right place, and does it point the way this repo says it should?**

The argument is the ticket's issue number.

`/skillworks:review-architecture 168`

Two other axes run beside this one, each in a session of its own. Standards asks whether the code follows the written rules. Spec asks whether it is what was asked for. Neither is this axis's business.

This axis reads outside the change. An import is only wrong against the module graph around it, so read the tree, not just the diff.

## What to read

### The change

The loop runs this step before anything is committed, so the change is the working tree. The `-M` matters: it is what turns a rename into a rename rather than a delete and an add.

```bash
git add -N .
git diff HEAD
git diff HEAD --stat -M
```

If `git diff HEAD` is empty, stop and report that there is nothing to review.

### The sources, in order of rank

Three kinds, and each outranks the one before it.

**Documented.** Anything that says how the code is *arranged* rather than how it is written: `CONTEXT-MAP.md`, each context's `CONTEXT.md`, and `docs/adr/`. `docs/agents/domain.md` says where this repo's decisions live. Read that first and follow it.

**Written as rules.** `.claude/rules/file-placement.md` holds the eight Slice rules the code was written under. Read the context map beside it, because a rule reaches only the code the map gives it. Cite a breach by the name of the check that catches it, from the table in `docs/agents/placement-checks.md`. Read that file: it maps each check back to the rule it runs, and it names the two places the arrangement baseline bends where the repo has written the rule down.

**Executable.** A boundary rule the repo can run. This ranks highest, because it is enforced rather than hoped for. **Run it, do not reason about it.**

Run the placement checks, and only those. The placement-checks file names the checks in the Suite file, `docs/agents/suite.json`, that prove placement. Find each one in the Suite file and run its command in its folder. Run a check's readiness command first, and the readiness command of any check before it in the same folder, unless its `unless` path exists. Do not run the rest of the Suite. The driver runs the whole Suite as a step of its own, and this axis would never read the rest.

Each names the rule, the path and what to do. Quote a breach as it came. Say which checks you ran. Where the placement-checks file names no check, or no check exists for the code you are judging, say that too: a repo that cannot check its own boundaries is itself the finding a reader wants.

### The baseline

On top of what the repo has, this axis always carries the arrangement baseline in `docs/agents/arrangement-baseline.md`. Read it yourself, and read the two bends that sit beneath the check table in `docs/agents/placement-checks.md` with it.

## The three binding rules

- **The repo overrides.** A documented rule or a recorded decision wins. Do not re-litigate an ADR. If the change contradicts one, that is the finding. If the ADR itself looks wrong, say so once and move on.
- **Diff-introduced only.** Standing debt is not a finding. Report what this change introduced, or made materially worse. An axis that re-reports the same architecture every run gets skimmed, and then skipped.
- **Cite or drop it.** Every finding names the rule it breaches or the baseline item it matches, and quotes the line, usually a single import. Judgement without evidence is taste, and it is the failure this axis is most prone to.

## What to look for

Run the placement checks first, and report what each one said. Then, for every module the change touches:

1. Does anything added point the wrong way, cross a seam it should not, or reach past a module's public entry point?
2. Is every added or moved file in the module its dependencies say it belongs to, and in the Slice whose job it serves?
3. Does the change introduce a cycle?
4. Does any folder the change creates breach a written placement rule?

Keep the whole report under 400 words.

## When to skip

Skip the axis when the change sits inside one module and touches no config, no dependency manifest, no new file and no file move. There is no arrangement question to answer. A new file asks which folder it belongs in, and a moved file asks which way it now points, so neither of those skips. Note the skip in the report.

## Fix what you find

This axis edits the worktree, and it should. A finding you can fix, you fix here. The session that read the module graph is the one that knows where a file belongs, so a file in the wrong folder is moved here rather than described for somebody else to move.

Fix only what this axis owns. A finding that belongs to Standards or Spec is dropped rather than reported here, so it is not yours to fix either.

Run the placement checks again after a fix, and report what they said about the code as it now stands.

A finding you judge not worth fixing is named in the report and left, with the reason. A move that would spread into modules this change never touched is of that kind.

The report names every finding either way, and says which ones you fixed.

## How to end the turn

End with the findings under an `## Architecture` heading. The driver reads that heading to prove the axis ran, so an axis that found nothing, or that skipped, still writes it:

```
## Architecture

Skipped: the change sits inside one module and adds no file.
```

A turn that ends without that heading fails the step and stops the loop.
