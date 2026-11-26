# The judges at the end of the loop are steps, named for their glossary word

The four judges at the end of the spec loop, the Deepening check, the Simplify check, the drift check
and the Name check, are steps. Each one reads Steering of its own, the Deepening check and the
Simplify check read files the team writes, and a step is what `/skillworks:show-steering` can show.
So a team can see the text a judge reads in its own repo, the same as for `build`.

Each judge takes one name everywhere, made from its glossary word: `deepening-check`,
`simplify-check`, `drift-check` and `name-check`. The step, the plan line, the log, the Session, the
report file, the `tracker-publish` command and the skill (`spec-deepening-check` and the rest) all use
it. A second run takes the name of the check it repeats: `drift-re-check` and `name-re-check`.

## Considered options

**Keep the judges outside the word Step, in a second list `show-steering` reads.** Rejected. The
driver already ran them as steps, so the glossary and the code would go on naming one thing two ways.

**Put the judges in `steps.json` under the driver's short names, `deepen`, `simplify`, `drift` and
`names`.** Rejected. The short names say less than the glossary words, and the files a team edits are
already named `deepening-check.md` and `simplify-check.md`.

**Rename the steps and keep the skills' short names.** Rejected. The plan would print
`/skillworks:spec-deepen` beside the step `deepening-check`, which is two names again.

## Consequences

The other lines of the driver's plan stay out of the step list. The ticket lines read no Steering, and
`baseline`, `full-run`, Landing and the re-checks read nothing a step does not already show.

A loop that stopped before the rename can run again after it, because the loop finds a judge's report
on the Tracker by its heading and not by the step's name.
