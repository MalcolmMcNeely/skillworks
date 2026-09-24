# The Smart zone and the Dumb zone

A context window has two parts, and a session is planned around the line between them.

## The Smart zone

The **Smart zone** is the part of a context window in which a model still keeps every instruction it was given. A session is planned to finish its work inside it. On the strongest models today it runs to about 150k tokens, but the line moves with the model and with the work, so treat the number as a rough guide and not a promise.

## The Dumb zone

The **Dumb zone** is the part of a context window past the Smart zone.

A model in the Dumb zone does not fail loudly. It fails by **omission**: it leaves something out. Three things go missing, and one thing stays:

- **A dropped instruction.** A step you asked for does not happen, and nothing says it was skipped.
- **A dropped constraint.** A rule the work had to keep is broken, because the model no longer holds it.
- **A lost middle.** What sat in the middle of a long read is gone, while the start and the end are still there.
- **A model that still sounds sure.** The tone does not change. The report reads as confident as it did in the Smart zone.

So the error is something missing, and a missing thing is easy to miss. When a session has run long, do not look only for what is wrong. Look for what is absent: the step that never ran, the rule that was not kept, the part of the file nobody quoted back.

## What pushes a model into it sooner

- **Too many constraints.** Every instruction and every rule takes a share of the model's attention. The more of them a session carries, the sooner one of them drops. Keep instructions few, and keep each one short.
- **Lost in the middle.** A model reads the start and the end of its context best, and the middle worst. A long context puts more of what matters in the middle, where it is the first thing to go.

The two add up. A long session with many rules reaches the Dumb zone well before its token count says it should.

## What to do about it

- Plan a session to finish inside the Smart zone. Stop at a phase boundary before the window fills, not after.
- If a session gets near the line, do not push on. Pick a move at the nearest phase boundary (see [PHASE-BOUNDARIES.md](PHASE-BOUNDARIES.md)).
- Give a fresh session only what it needs. Fewer constraints keep it in the Smart zone longer.
- Put what matters most at the start or the end of what you hand over, not in the middle.
