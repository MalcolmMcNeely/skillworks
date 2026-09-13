---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
disable-model-invocation: true
---

Implement the work described by the user in the spec or tickets.

## Before you start

If a ticket number was given, fetch it, and fetch its parent spec too — the ticket is the what, the spec is the why.

**Refuse a blocked ticket.** A ticket with an open blocker is not ready:

```bash
gh api "repos/$REPO/issues/$N" --jq '.issue_dependencies_summary.blocked_by'
```

Anything but `0` means stop, name the open blockers, and do nothing else.

## Doing the work

Use /tdd where possible, at pre-agreed seams.

Run typechecking regularly, single test files regularly, and the full test suite once at the end.

Once done, use /code-review to review the work.

## Finishing

A ticket is not done until the full test suite runs and passes. Do not close it on a partial pass or a skipped suite.

Commit your work to the current branch, then push it. Do not include "co-authored by" in the commit message.

Leave the working tree clean. A caller may be driving you in a loop and will stop if it is not.

Close the ticket with a comment saying what was done and which tests prove it.
