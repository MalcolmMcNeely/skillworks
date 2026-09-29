---
name: review-standards
description: Review a ticket's change against this repo's documented coding standards and its review file, and report under a Standards heading.
disable-model-invocation: true
---

# Review: Standards

The argument is the ticket, named as its Tracker names it: `docs/agents/issue-tracker.md` says how each Tracker names its tickets.

`/skillworks:review-standards 168`
`/skillworks:review-standards 7/2`

Read the axis file `../review-changes/standards.md`, from this skill's base directory, and follow it in loop mode. In loop mode the axis edits what it finds. `/skillworks:review-changes` follows the same file in report-only mode, so a review by hand checks what the loop checks.
