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

Run no review of your own. The three axes — Standards, Spec and Architecture — have each already run in a session of its own, and their reports arrive in this prompt under the axis that wrote each one. A review run again here would be the same work twice, and the two could disagree.

1. **Fix the findings.** Fix every finding, from every axis in the prompt. If you judge one wrong, leave it and give the reason in the closing comment. A prompt carrying no reports has nothing to fix, so go straight on.
2. **Run the full test suite.** A ticket is done only once you have read the full suite's passing result. A partial pass or a skipped suite leaves the ticket open.
3. **Commit to `main`.** Do NOT push. A spec loop pushes the ticket itself, by a step of its own that runs after this one, so the push is checked rather than taken on trust. This repo has no branches and no pull requests. Do not include "co-authored by" in the commit message.
   - **Name the ticket in the message.** See "Two conventions the loop leans on" in `docs/agents/issue-tracker.md` for the form, and for why it is not a closing word.
4. **Leave the working tree clean.** A caller may be driving you in a loop and will stop if it is not.
5. **Close the ticket** with a comment saying what was done and which tests prove it.
