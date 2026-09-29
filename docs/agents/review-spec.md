# Review: Spec

What the `spec` review checks, beyond what it always checks. It always asks whether the change is the one the ticket asked for: every acceptance criterion delivered, nothing added that no line asked for, and every Surface the spec names kept in step. That check lives in the review itself, so this file holds no list of its own. It holds your team's checks, and what the review skips.

## Checks

Your team's own checks for the `spec` review go here, one bullet for each. A check says what to look for, and whether a breach of it is a hard breach or a judgement call. A hard breach is always fixed and never left. A judgement call may be left, with the reason. A check that covers only some of the code names the paths it covers. A check with no paths covers the whole change.

```markdown
- A change to an API endpoint carries a line in the changelog. A hard breach. Paths: `src/api/`.
```

A check that should also shape the build goes in a rule in `docs/agents/rules/` instead. A rule loads into every session, and this file is read only by its review.

This list holds no check yet.

## Do not report

The paths and the kinds of finding the `spec` review skips go here, one bullet for each, such as generated code or a Surface your team keeps in step by hand.

This list is empty.
