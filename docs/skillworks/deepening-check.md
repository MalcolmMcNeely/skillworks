# Deepening check

What the Deepening check counts as a Strong deepening opportunity, your team's own checks, and what the check skips. The Deepening check reads only the commits a spec's tickets Landed, once every ticket has Landed. It judges them with the deep-module vocabulary and the deletion test. It changes no code. The loop files each Strong candidate it lists as a deepening ticket of its own, up to `limit`.

The YAML block at the end holds the setting the loop reads.

## Strong

A candidate is Strong only when every line here holds:

- **It passes the deletion test.** Deleting the shallow module would concentrate its complexity in one place, and not just move it.
- **The spec's commits made it or grew it.** The shallow module, or the friction around it, is in code the spec's tickets wrote or changed.
- **One ticket can build it.** The deepening fits in one build, and it leaves every caller working.
- **The tests stay at a seam.** After the deepening, the tests can prove the module through its interface, and no test needs to reach past it.
- **No decision stands against it.** No ADR records a choice the deepening would undo.

A candidate that misses one line is Worth exploring. A candidate that rests on a guess about future work is Speculative. Neither one becomes a ticket.

## Checks

Your team's own checks for the Deepening check go here, one bullet for each. A check says what to look for, and whether a candidate it finds may be Strong or is never more than Worth exploring. A check that covers only some of the code names the paths it covers. A check with no paths covers every commit of the spec.

```markdown
- A module that wraps one call to a library and adds nothing is a candidate. It may be Strong. Paths: `src/adapters/`.
```

A check that should also shape the build goes in a rule in `docs/skillworks/rules/` instead. A rule loads into every session, and this file is read only by the Deepening check.

This list holds no check yet.

## Do not report

The paths and the kinds of candidate the Deepening check skips go here, one bullet for each, such as generated code or a module your team keeps shallow on purpose.

This list is empty.

## Settings

`limit` is the most deepening tickets the loop files for one spec. The check lists at most this many Strong candidates, strongest first, and names the rest in its report. `0` turns the Deepening check off.

```yaml
limit: 3
```
