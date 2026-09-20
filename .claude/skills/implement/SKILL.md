---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
---

Implement the work described by the user in the spec or tickets.

## What runs

The flag after the ticket number decides which sections run:

| Call | Sections, in order |
|---|---|
| `/implement <n>` | Before you start, Building, Sweeping comments, Finishing |
| `/implement <n> --stop-after-tests` | Before you start, Building |
| `/implement <n> --finish` | Before you start, if this session has not read the ticket; then Finishing |

## Before you start

If a ticket number was given, fetch it, and fetch its parent spec too — the ticket is the what, the spec is the why.

**Refuse a blocked ticket.** A ticket with an open blocker is not ready:

```bash
gh api "repos/$REPO/issues/$N" --jq '.issue_dependencies_summary.blocked_by'
```

Anything but `0` means stop, name the open blockers, and do nothing else.

## Test runs

Tests, typechecks and lints are deterministic validation: their result, not your expectation of it, decides the next step. Run each one in the foreground, with a timeout long enough for it to finish, and read its result before your next action. A caller may drive you with `claude -p`, which ends the session the moment your turn ends, so a run still going at that moment is lost, and so is the commit it would have allowed.

## Building

Use /tdd where possible, at pre-agreed seams.

Run typechecking and single test files regularly.

Building is done when the typecheck is clean and every test the change adds or touches passes.

With `--stop-after-tests`, leave the change uncommitted and the ticket open, and report which tests pass.

## Sweeping comments

Run /comment-sweep on the uncommitted change.

## Finishing

1. **Review.** Run /code-review on the uncommitted change, with the ticket as its spec.
2. **Fix the findings.** Fix each one. If you judge a finding wrong, leave it and give the reason in the closing comment.
3. **Run the full test suite.** A ticket is done only once you have read the full suite's passing result. A partial pass or a skipped suite leaves the ticket open.
4. **Commit to `main`.** Do NOT push. A spec loop pushes once at the end, after every ticket is done, so a half-finished spec never reaches the remote. This repo has no branches and no pull requests. Do not include "co-authored by" in the commit message.
   - **Name the ticket in the message.** See "Two conventions the loop leans on" in `docs/agents/issue-tracker.md` for the form, and for why it is not a closing word.
5. **Leave the working tree clean.** A caller may be driving you in a loop and will stop if it is not.
6. **Close the ticket** with a comment saying what was done and which tests prove it.
