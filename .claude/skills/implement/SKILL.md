---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
---

Implement the work described by the user in the spec or tickets.

## What runs

The flag after the ticket number decides which sections run:

| Call | Sections, in order |
|---|---|
| `/implement <n>` | Before you start, Building, Reviewing, Fixing, Sweeping comments, Finishing |
| `/implement <n> --stop-after-tests` | Before you start, Building |
| `/implement <n> --fix` | Before you start, if this session has not read the ticket; then Fixing |
| `/implement <n> --finish` | Before you start, if this session has not read the ticket; then Finishing |

The order is the spec loop's own, so the developer at the keyboard and the driver follow one set of rules. Each flag is there because the driver calls that section as a step of its own.

## Before you start

If a ticket number was given, fetch it, and fetch its parent spec too — the ticket is the what, the spec is the why.

**Refuse a blocked ticket.** A ticket with an open blocker is not ready:

```bash
gh api "repos/$REPO/issues/$N" --jq '.issue_dependencies_summary.blocked_by'
```

Anything but `0` means stop, name the open blockers, and do nothing else.

## Test runs

Tests, typechecks and lints are deterministic validation: their result, not your expectation of it, decides the next step. Run each one in the foreground, with a timeout long enough for it to finish, and read its result before your next action. A caller may drive you with `claude -p`, which ends the session the moment your turn ends, so a run still going at that moment is lost, and so is the commit it would have allowed.

## A write under `.claude/` refused

A write under `.claude/` is refused as a sensitive file. No allow rule lifts it, only the permission mode does, so the refusal is the harness and not a fault in the call you made. Do not try the write again, and do not route around it with a shell redirection, a patch command or any other tool.

One refused write blocks one line of the ticket and nothing else. Do every other part of the ticket, and run the tests over what you did write. Then:

1. **Commit the verified work**, with the ticket named in the message as Finishing says. Under `--stop-after-tests` the change stays uncommitted, as that flag already says.
2. **Leave the ticket open.** Work that is not done is not closed, and the driver reads the open ticket as the stop.
3. **Write the wall on the ticket.** Comment with the exact path, the exact change you could not write, and that the write was refused as a sensitive file. A developer has to be able to make that change from the comment alone, without opening anything else.

Say the same in your report, so it reaches the driver's log as well.

## Building

Use /tdd where possible, at pre-agreed seams.

Run typechecking and single test files regularly.

Building is done when the typecheck is clean and every test the change adds or touches passes.

With `--stop-after-tests`, leave the change uncommitted and the ticket open, and report which tests pass.

## Reviewing

Run /code-review on the uncommitted change, and give it the ticket number. An uncommitted change carries no commit, so the Spec axis has nothing to find the ticket in unless you pass it.

Its fan-out to sub-agents needs a session still awake to read what comes back, so a headless run cannot use it. That is why the spec loop runs the three axes as three steps of its own instead, and why the difference stays.

The findings it returns are what the Fixing section acts on.

## Fixing

Findings reach this section two ways, and it covers both:

- **Under the spec loop**, `--fix` selects it. Each axis has run in a session of its own, and the reports arrive in this prompt under the axis that wrote each one, each beside a record of what that axis changed.
- **Under a hand run**, the Reviewing section produced them in this same session.

1. **Fix every finding, from every axis.** Under the spec loop an axis fixes what it finds, so a record beside a report says what is already done — read the change before you fix the same thing twice. Under a hand run the axes only report, so nothing is fixed yet.
2. **Settle a disagreement.** This is the one session holding all three reports at once, so a contradiction between two axes is settled here and nowhere else.
3. **Leave a finding you judge wrong**, and keep the reason for the closing comment.
4. **A prompt carrying no reports has nothing to fix**, so go straight on.

Leave the change uncommitted. The sweep has still to run, and committing is Finishing's job.

## Sweeping comments

Run /comment-sweep on the uncommitted change.

It runs after the findings are fixed, because anything that writes after a sweep puts back the comments the sweep cut.

## Finishing

Run no review of your own, and fix no finding here. Under the spec loop the three axes — Standards, Spec and Architecture — have each already run in a session of its own, and the fixing step has already acted on what they found. Under a hand run the Reviewing and Fixing sections have already done the same. A review run again here would be the same work twice, and the two could disagree.

1. **Run the full test suite.** A ticket is done only once you have read the full suite's passing result. A partial pass or a skipped suite leaves the ticket open.
2. **Commit to `main`.** Do NOT push. A spec loop pushes the ticket itself, by a step of its own that runs after this one, so the push is checked rather than taken on trust. This repo has no branches and no pull requests. Do not include "co-authored by" in the commit message.
   - **Name the ticket in the message.** See "Two conventions the loop leans on" in `docs/agents/issue-tracker.md` for the form, and for why it is not a closing word.
3. **Leave the working tree clean.** A caller may be driving you in a loop and will stop if it is not.
4. **Close the ticket** with a comment saying what was done, which tests prove it, and any finding left unfixed with the reason.
