# An eval judge is another model, and one judge reads both arms

The judge that says whether a sheet holds a Statement is an Opus when the backfill ran on a Fable,
and a Fable when it ran on an Opus. The harness asks for the alias and records the model id it was
given beside every number. A comparison judges both arms in one go, and keeps every sheet, so when
the judge moves the old arm is judged again at the price of a judge call, never a two-hour run.

## Why

A model recognises its own text and prefers it, so a fresh instance of the writer is not a judge. A
pinned judge version is upkeep nobody does, and one day stops resolving. What a paired comparison
needs is not a fixed judge for ever but one judge for both of its arms, so the judge's drift can never
read as a change in the skill.

## Considered options

**Pin the judge's model id in a setting.** Rejected. The pin goes stale, and a bump between two
comparisons silently changes what the numbers mean.

**Judge with the model that wrote the sheet, in a fresh Session.** Rejected. Self-preference is the
bias the rule exists to stop.
