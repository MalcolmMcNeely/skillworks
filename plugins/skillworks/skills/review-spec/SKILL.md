---
name: review-spec
argument-hint: "<ticket>"
description: Review a ticket's change against what the ticket asked for, and report the gaps under a Spec heading.
disable-model-invocation: true
---

# Review: Spec

The argument is the ticket: its issue number with the GitHub Tracker, or `<spec>/<ticket>` with the files Tracker. The ticket is the first word of the argument. Any text after it comes from the driver, and it still holds.

`/skillworks:review-spec 168`
`/skillworks:review-spec 7/2`

Read the axis file `${CLAUDE_PLUGIN_ROOT}/skills/review-changes/spec.md` and follow it in loop mode. In loop mode the axis edits what it finds. `/skillworks:review-changes` follows the same file in report-only mode, so a review by hand checks what the loop checks.
