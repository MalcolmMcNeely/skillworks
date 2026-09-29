---
name: grill
description: A relentless interview to sharpen a plan or design, writing the glossary and ADRs as it goes and publishing the spec at the end.
disable-model-invocation: true
---

# Grill

Drive a design from the first question to a published spec.

## Process

### 1. Interview under both disciplines

Call the Skill tool with "skillworks:grilling", then with "skillworks:domain-modeling". The first owns the questions, the
second owns the words. Both run on every round.

### 2. Walk the Surfaces when the frontier is empty

A Surface is a place a change can have to reach besides the code that does the work, such as the
README or the user docs. `docs/agents/surfaces.md` lists the team's Surfaces, one `##` section each,
with where it lives, the question to ask and what to capture. A `##` inside a code fence is an
example, not a Surface. A file with no Surface in it, or no file, means skip this step.

The design is settled now, so each question can fit it. Walk the Surfaces by four rules:

- Ask about one Surface at a time, with the Surface's own question, and never present the list.
- Skip a Surface the change does not touch, without asking about it.
- Capture each answer as a requirement that travels with the spec: what the Surface has to say once
  the change Lands, shaped by the Surface's "What to capture".
- Point at a Surface's content by its path, and never copy it into the answer.

An answer that reopens the design goes back to step 1 as the next round.

The README Surface is the Surface whose heading is `## The README`, outside a code fence. When the
team has one, ask its question as any other. When the answer is that the change deserves README text
beyond what its "What to capture" allows, capture only what the limit allows, and keep the rest for
the gate: it goes into the spec's Out of Scope as "the README: a focused session". Nothing in the loop
builds that session, so file no issue for it.

### 3. Sum up

Sum up the shape that was settled:

- The problem, as the developer stated it.
- The design that answers it, and the decisions that shaped it.
- Each Surface the change touches, with the requirement its answer captured.
- The words and the ADRs written along the way, each one already pushed.
- What the session ruled out, and why.
- When the change deserves README text the README Surface's limit does not allow, that it goes into
  the spec's Out of Scope as "the README: a focused session", and that nothing builds it.

Then ask the developer to confirm that this is the design.

This is the one gate. Every question before it is about the design, and everything after it runs
unattended, so the summary is what the developer consents to. It carries every decision the spec
will be built from.

### 4. On yes, write the spec

Call the Skill tool with "skillworks:to-spec". Then end with the spec number it publishes and the
next command, `/skillworks:spec-loop <n>` with that number, and name no other skill.

On no, the frontier was not empty. Take what the developer said as the next round and go back to
step 1.

## When a pull lands on settled ground

`skillworks:domain-modeling` reports when a pull brings down a teammate's change to ground this session already
settled.

Carry that report to the developer as questions. For each decision the change reopens, give the
question, the answer this session gave it, and the teammate's wording that puts that answer in
doubt. Ask them as the next round. The developer reads which decisions are open again, rather than
working it out from a diff.
