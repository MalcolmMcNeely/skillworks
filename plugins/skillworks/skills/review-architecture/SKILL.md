---
name: review-architecture
argument-hint: "<ticket>"
description: Review where a ticket's change sits and which way its dependencies point, against this repo's placement rules and boundary checks, and report under an Architecture heading.
disable-model-invocation: true
---

# Review: Architecture

The argument is the ticket, named as its Tracker names it: `docs/agents/issue-tracker.md` says how each Tracker names its tickets.

`/skillworks:review-architecture 168`
`/skillworks:review-architecture 7/2`

Read the axis file `${CLAUDE_PLUGIN_ROOT}/skills/review-changes/architecture.md` and follow it in loop mode. From this skill's folder that file is `../review-changes/architecture.md`. In loop mode the axis edits what it finds. `/skillworks:review-changes` follows the same file in report-only mode, so a review by hand checks what the loop checks.
