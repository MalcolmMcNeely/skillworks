---
name: review-changes
description: Review the changes since a fixed point (commit, branch, tag, or merge-base), or an uncommitted change, along three axes — Standards (does the code follow this repo's documented coding standards?), Spec (does the code match what the originating ticket or spec asked for?) and Architecture (is it in the right module, pointing the right way?). Runs each axis in a parallel sub-agent that follows the loop's own review skill, and reports them side by side. Use when the user wants to review a branch, a PR, work-in-progress changes, or asks to "review since X". Not for a check on correctness alone: that is Claude Code's own /code-review.
---

Three-axis review of a change:

- **Standards** — does the code conform to this repo's documented coding standards?
- **Spec** — does the code faithfully implement the originating ticket or spec?
- **Architecture** — is the code in the right module, and do its dependencies point the way this repo says they should?

Each axis runs as a **parallel sub-agent** so they don't pollute each other's context, then this skill sets their reports side by side.

This skill holds no review of its own. Each sub-agent follows the axis skill the spec loop runs, so a review by hand checks what the loop checks. The axis skills sit beside this skill's folder in the Plugin:

| Axis | Skill file, from this skill's base directory |
|---|---|
| Standards | `../review-standards/SKILL.md` |
| Spec | `../review-spec/SKILL.md` |
| Architecture | `../review-architecture/SKILL.md` |

The issue tracker should have been provided to you. If `docs/agents/issue-tracker.md` is missing, tell the user to run `/skillworks:skillworks-setup`.

## Pin the fixed point

Whatever the user said is the fixed point — a commit SHA, branch name, tag, `main`, `HEAD~5`, etc. If they didn't specify one, ask for it, unless the review is of an uncommitted change.

Capture the diff command once: `git diff <fixed-point>...HEAD` (three-dot, so the comparison is against the merge-base). Also capture `git diff <fixed-point>...HEAD --stat -M`, and the list of commits via `git log <fixed-point>..HEAD --oneline`.

**An uncommitted change** has no commits for a three-dot diff to see, and needs no fixed point. Run `git add -N .` so new files show, then use `git diff HEAD` and `git diff HEAD --stat -M` in place of the commands above. There is no commit list.

Before going further, confirm the fixed point resolves (`git rev-parse <fixed-point>`) and the diff is non-empty. A bad ref or empty diff should fail here — not inside three parallel sub-agents.

## Find the spec

Look for the ticket or spec the change was built for, in this order:

1. The `Ticket:` trailer on the commits, read back as `docs/agents/issue-tracker.md` says. Fetch the ticket and its parent spec through the same docs.
2. An issue number, or a ticket named as its Tracker names it, passed as this skill's argument. An uncommitted change carries no trailer, so this is where its ticket comes from.
3. With neither, ask the user which ticket or spec the change was built for. If they say there isn't one, skip the Spec sub-agent and note that in the report.

## Spawn the sub-agents in parallel

Give each sub-agent the same four things, and let it read the rest itself:

- The path to its axis skill file, from the table above, resolved against this skill's base directory. Tell it to read that file and follow it in its report-only mode.
- The diff command and the `--stat -M` command.
- The commit list, or a line saying the change is uncommitted.
- The ticket or spec: its number and Tracker, or the fetched contents.

Say in each prompt that the sub-agent edits nothing. A review by hand reports, and the user decides what to change.

## Aggregate

Present the reports under `## Standards`, `## Spec` and `## Architecture` headings, verbatim or lightly cleaned. Do **not** merge or rerank findings — the axes are deliberately separate (see _Why three axes_).

If an axis stops because a file it needs is missing, give its message under its heading as it came.

End with a one-line summary: total findings per axis, and the worst issue _within each axis_ (if any). Don't pick a single winner across axes — that's the reranking the separation exists to prevent.

## Why three axes

A change can pass on one axis and fail on another, so each masks the others when merged:

- Code that follows every standard but implements the wrong thing → **Standards pass, Spec fail.**
- Code that does exactly what the issue asked but breaks the project's conventions → **Spec pass, Standards fail.**
- Code that is well named, well tested, and exactly what the issue asked for, in a module that should never have imported it → **Standards and Spec pass, Architecture fail.**

The third axis is separate from Standards for two further reasons. Its evidence is different — Standards reads the diff, Architecture needs the module graph the diff sits in. And its remedies cost differently: "rename this" and "invert this dependency" do not belong in one ranked list, because the cheap findings crowd out the expensive ones.
