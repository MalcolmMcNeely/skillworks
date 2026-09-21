---
name: review-standards
description: Review a ticket's change against this repo's documented coding standards and the smell baseline, and report under a Standards heading.
disable-model-invocation: true
---

# Review: Standards

One axis of the three-axis review. This one asks a single question: **does the code follow the standards this repo has written down?**

The argument is the ticket's issue number.

`/review-standards 168`

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

On top of what the repo writes down, this axis always carries the baseline below. It applies even where a repo documents nothing. Two rules bind it:

- **The repo overrides.** A documented repo standard always wins. Where the repo endorses what the baseline would flag, the smell is suppressed.
- **Always a judgement call.** Each item is a labelled heuristic, never a hard breach.

Skip anything tooling already enforces. Each item reads *what it is* → *how to fix*:

- **Mysterious Name** — a function, variable or type whose name does not say what it does or holds. → Rename it. If no honest name comes, the design is murky.
- **Duplicated Code** — the same logic shape appears in more than one hunk or file in the change. → Extract the shape, call it from both.
- **Feature Envy** — a method that reaches into another object's data more than its own. → Move the method onto the data it envies.
- **Data Clumps** — the same few fields or parameters keep travelling together. → Bundle them into one type, pass that.
- **Primitive Obsession** — a primitive or string standing in for a domain concept that deserves its own type. → Give the concept its own small type.
- **Repeated Switches** — the same switch or `if`-cascade on the same type recurs across the change. → Replace with polymorphism, or one map both sites share.
- **Shotgun Surgery** — one logical change forces scattered edits across many files in the diff. → Gather what changes together into one module.
- **Divergent Change** — one file or module is edited for several unrelated reasons. → Split it so each module changes for one reason.
- **Speculative Generality** — abstraction, parameters or hooks added for needs the ticket does not have. → Delete it. Inline back until a real need shows.
- **Message Chains** — long `a.b().c().d()` navigation the caller should not depend on. → Hide the walk behind one method on the first object.
- **Middle Man** — a class or function that mostly just delegates onward. → Cut it, call the real target direct.
- **Refused Bequest** — a subclass or implementer that ignores or overrides most of what it inherits. → Drop the inheritance, use composition.

The items above judge code. A test carries them and four of its own, under one question: **what change to the code would make this test fail?** A test with no answer is reported however tidy it reads, because a suite that cannot go red buys nothing and is read as proof.

- **Tautological Assertion** — the expected side is worked out the way the code works it out, so both sides move together and no defect can show. → Write the expected value out by hand.
- **Untriggered Fixture** — the input holds nothing the behaviour under test acts on, so the assertion would still hold with that behaviour deleted. → Put the trigger in the fixture, and settle it by deleting the behaviour and watching the test go red.
- **Unguarded Enumeration** — a test walks files, rows or elements and judges what it found without proving it found any, so an empty walk passes. → Pin the count the walk is expected to reach.
- **Stub Echo** — a stub is handed a value and the assertion only checks that value came back, so it measures the stub. → Assert on what the code made of the value, not on the value.

## What to report

Report per file and hunk where that helps:

1. Every place the change breaches a documented standard. Cite the standard by file and rule, and quote the line it turns on.
2. Every baseline smell. Name the item and quote the hunk.

Mark each finding as a hard breach or a judgement call. A documented standard can be a hard breach. A baseline smell never is.

Keep the whole report under 400 words.

## How to end the turn

End with the findings under a `## Standards` heading. The driver reads that heading to prove the axis ran, so an axis that found nothing still writes it:

```
## Standards

No findings on this change.
```

A turn that ends without that heading fails the step and stops the loop.
