---
name: resolve-conflict
description: Resolve the conflicting files of the rebase the spec loop stopped on, then stage them and stop.
disable-model-invocation: true
---

# Resolve conflict

The spec loop rebased your ticket onto the newest `main` and hit a conflict. You wrote one side of it.
Resolve the conflicting files, stage them, and stop there.

## Your bias

You are the session that built this ticket. You read its spec, wrote its code and ran its tests, so
your side of every hunk is already in your head. **The other side** — the commits that landed while
this ticket was being built — is a stranger. That asymmetry is the whole risk: the side you understand
will look like the right one every time, because it is the only one whose reasoning you can see.

So argue for the other side first. Before you discard a single line of it, say what its ticket was
trying to do, and why someone thought that line was needed. A line you cannot argue for is a line you
have not read yet.

## What you were given

The driver gathered the other side already and put it in this prompt:

- the commits between this ticket's base and the newest `origin/main`
- the ticket number behind each of those commits
- each of those tickets' closing comments, which name the files touched, the tests run, and the findings
  that agent chose not to fix with its reasons

That is your reading, and it is complete. **Make no tracker calls.** Refusal rule 1 below only means
something because every ticket that bears on this conflict is already in front of you.

## Resolving

Take each hunk in turn and resolve it to the intention behind both sides, rather than to whatever
compiles. A resolution that builds and drops someone's behaviour is the failure this step exists to
catch.

**Taking one side wholesale** is allowed on one condition: you can say which change supersedes the
other, and why the discarded work is genuinely redundant. Say both, in the answer you give at the end.
Short of both, the hunk keeps both intentions.

Keep the resolution to what the two sides asked for. Behaviour on neither side is new work, and it
belongs in a ticket of its own.

**Done when** every conflicting file holds a resolution whose intention you can name, and carries no
conflict marker.

## Refusing

Two cases. Either one means stop:

1. The answer is in neither side and in neither ticket.
2. The project's checks are still failing after one attempt to fix them.

A refusal leaves the conflict where it stands. Begin your answer with the rule that fired, on a line
of its own:

```
REFUSED 1: the count the tile shows is on neither side.
```

Then say which side wanted what, side by side, and stop. The driver reads that first line, so the rule
reaches the loop's log without anybody opening the transcript, and the two intentions beneath it are
what the developer fixes the cause from.

**A refusal never means resolve badly.** The loop stopping is the cheap outcome; a resolution that
quietly deleted a ticket's work is the expensive one, and it is expensive later, when nobody is
looking.

## Finishing

1. Run the project's checks — the typecheck, then the tests the conflict touched. You ran them when you
   built this ticket, so you know them. Fix what the resolution broke. One attempt: a second failure is
   refusal rule 2.
2. Stage the resolved files: `git add <file>...`

Then stop. The rebase, the full suite and the push all belong to the driver, so leave
`git rebase --continue` and `git rebase --abort` to it.

Your answer names each file, the intention you resolved it to, and, for any side you took wholesale,
what it supersedes and why the discarded work was redundant.
