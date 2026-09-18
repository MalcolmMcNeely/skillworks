---
name: grill-with-docs
description: A relentless interview to sharpen a plan or design, writing the glossary and ADRs as it goes and publishing the spec at the end.
disable-model-invocation: true
---

# Grill With Docs

Drive a design from the first question to a published spec.

## Process

### 1. Interview under both disciplines

Call the Skill tool with "grilling", then with "domain-modeling". The first owns the questions, the
second owns the words. Both run on every round.

### 2. Sum up when the frontier is empty

Sum up the shape that was settled:

- The problem, as the developer stated it.
- The design that answers it, and the decisions that shaped it.
- The words and the ADRs written along the way, each one already pushed.
- What the session ruled out, and why.

Then ask the developer to confirm that this is the design.

This is the one gate. Every question before it is about the design, and everything after it runs
unattended, so the summary is what the developer consents to. It carries every decision the spec
will be built from.

### 3. On yes, write the spec

Call the Skill tool with "to-spec", and report the spec number it publishes.

On no, the frontier was not empty. Take what the developer said as the next round and go back to
step 1.

## When a pull lands on settled ground

`domain-modeling` reports when a pull brings down a teammate's change to ground this session already
settled.

Carry that report to the developer as questions. For each decision the change reopens, give the
question, the answer this session gave it, and the teammate's wording that puts that answer in
doubt. Ask them as the next round. The developer reads which decisions are open again, rather than
working it out from a diff.
