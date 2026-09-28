# Each review axis reads one file the team owns

A team had no good place to add a review check, such as "every message handler is idempotent". A new
rule loads into every Session, and an item in the smell baseline could never be a hard breach. So
each of the three review axes now reads one file of its own in `docs/agents/`: `review-standards.md`,
`review-spec.md` and `review-architecture.md`. Each file holds the Plugin's defaults for that axis and
the team's own checks. The smell baseline becomes `review-standards.md`, and the arrangement baseline
becomes `review-architecture.md`. Each check says what to look for, whether it is a hard breach or a
judgement call, and the paths it covers when it covers fewer than all. A "Do not report" list names
what the axis skips. A hard breach is always fixed and never left. A judgement call may be left, with
the reason. A check that should also shape the build is a rule, because a review file is read only by
its review.

`code-review` becomes `review-changes`, so Claude does not confuse it with Claude Code's own
`/code-review`. Its sub-agents each follow one axis skill in a mode that reports and edits nothing,
so each axis has one text, and a review by hand checks what the loop checks.

## Considered options

**One file for every review check.** Rejected. Every axis would read every check, and the file would
grow with each concern. Anthropic warns that a long review file weakens the rules that matter most.

**One file for each concern, such as `review-security.md`.** Rejected. Each change would stay small,
but every axis would read every file to find its own checks.

**A root `REVIEW.md`, so one file also steers Anthropic's Code Review on a pull request.** Rejected
for now. Up to 2026-09-10, Anthropic's docs said that Code Review reads `REVIEW.md` as it stands and
does not expand an `@` import, so a `REVIEW.md` that imports the team's files would reach the review
as one line. A copy would drift from the three axis files.

**Keep the baselines as separate files.** Rejected. The `standards` axis would read two files for its
checks, and a team would look in two places to change one review.

**`code-review` keeps its own brief for each axis.** Rejected. Its briefs had already drifted from
the loop's axis skills, and a review by hand missed checks the loop makes.

## Consequences

A breach of a rule marked hard is now always fixed, as a moved name already was.
