# Stage one: settle the design

Part of [the Dev loop](../the-loop.md).

## The grill

`/skillworks:grill` asks the questions one at a time. Each one is numbered and carries a
recommended answer. It asks only what can be answered now: a question that hangs on a decision you
have not made yet waits for that decision.

Finding facts is never your job. A question that needs a fact from the code or the Tracker goes to a
sub-agent. The decisions are yours. The lookups are not.

Your glossary, `CONTEXT.md`, and your ADRs in `docs/adr/` are edited the moment a word or a decision
settles, not at the end. Every Session after this one starts with an empty context, and can only find
those decisions in the repo.

When no design question is left, the grill walks your Surfaces: the places in
`docs/agents/surfaces.md` a change can have to reach besides its code. It asks about one Surface at a
time, and skips a Surface the change does not touch. Each answer becomes a requirement the spec
carries. A file with no Surface in it skips this step.
[Steering](../steering.md#the-surfaces-file) says how to write the file.

With a README Surface, the grill asks about the README only as its Surface asks. A change that
deserves new README text, beyond what the Surface allows, is named at the gate and goes into the
spec's Out of Scope as "the README: a focused session". Nothing in the loop builds it, and no issue
is filed for it. The spec names the README only in its Surfaces section.

## The gate

When no question is left, the Session sums up the problem, the design, each Surface's answer, the
words and ADRs written on the way, and what was ruled out. Then it asks you to confirm.

- On **no**, what you said becomes the next round of questions.
- On **yes**, everything after runs with nobody watching. So the summary is the thing you consent to.
  It carries every decision the spec will be built from.

## The spec

On your yes, `/skillworks:to-spec` runs. With `github`, it publishes a `SPEC:` issue with the
`ready-for-agent` label. With `files`, it writes the spec's folder in `.specs/` and pushes it. It
commits and pushes what the interview changed on disk to the Target branch, and it reports the spec's
number. With `spec`, the spec names its own branch: under `## Branch` in the issue, or as `branch` in
`spec.md`. Its Surfaces section holds the requirement the grill captured for each Surface the change
touches.

The loop counts the drift check's Verdicts against the spec, so three sections come in a fixed shape,
the **counted shape**:

- **User Stories** is a numbered list that starts at 1, and skips and repeats no number. Each story
  is an item, called `S1`, `S2` and on.
- **Implementation Decisions** is a numbered list in the same way. Each decision is an item, called
  `D1`, `D2` and on.
- **Surfaces** holds one list item per Surface, and each item opens with the Surface's name in bold,
  such as `- **The user docs** (docs/usage/): ...`. The bold name is the item. A spec that touches no
  Surface says "None" there, and has no Surface items.

A line indented under an item is part of it, so a nested list or a snippet stays with its item.
Testing Decisions are not counted, because the Suite already proves them. `to-spec` writes every spec
in this shape.

The loop reads the shape before it claims any ticket. A spec in another shape is turned down then, in
seconds, and no ticket runs. The stop names each fault: a missing heading, a section with no numbered
list, a skipped or repeated number, or a Surface item with no bold name.

The push matters as much as the spec. The spec points at decisions that must already be in the repo,
because no later Session can see this one.

That number is what you give to `/skillworks:spec-loop`.
