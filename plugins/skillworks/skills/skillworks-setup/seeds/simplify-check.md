# Simplify check

What the Simplify check looks for, your team's own checks, and what the check skips. The Simplify check reads only the commits a spec's tickets Landed, once every ticket has Landed and the deepening tickets are built. It judges them from the four angles below. It hunts no correctness bugs, and it changes no code. The loop files everything it finds as one simplify ticket.

The YAML block at the end holds the setting the loop reads.

## Angles

A finding comes from one of these angles:

- **Reuse.** The spec's code writes again what the codebase already has, such as a helper, a type or a pattern another module already offers.
- **Simplification.** The spec's code is harder than its job: a branch that never runs, a layer that only passes a call on, a value worked out twice, or a name that hides what a thing is.
- **Efficiency.** The spec's code does work it does not need: a read inside a loop that one read before it would do, a copy nobody uses, or a wait that holds up nothing.
- **Altitude.** The spec's code sits at the wrong level: a detail spelled out where its callers only need the intent, or a decision made deep down that its caller should make.

A finding names where it is, its angle, and the simpler form. A finding that rests on a guess about future work is not a finding.

## Checks

Your team's own checks for the Simplify check go here, one bullet for each. A check says what to look for, and which angle it belongs to. A check that covers only some of the code names the paths it covers. A check with no paths covers every commit of the spec.

```markdown
- A function that wraps one call and adds nothing is a finding. Angle: simplification. Paths: `src/adapters/`.
```

A check that should also shape the build goes in a rule in `docs/skillworks/rules/` instead. A rule loads into every session, and this file is read only by the Simplify check.

This list holds no check yet.

## Do not report

The paths and the kinds of finding the Simplify check skips go here, one bullet for each, such as generated code or a copy your team keeps on purpose.

This list is empty.

## Settings

`enabled` says whether the loop runs the Simplify check. `false` turns it off, and the loop goes straight on to the drift check.

```yaml
enabled: true
```
