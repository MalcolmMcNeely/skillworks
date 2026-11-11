---
name: grill
argument-hint: "[the idea or plan]"
description: A relentless interview to sharpen a plan or design, writing the glossary and ADRs as it goes and publishing the spec at the end.
disable-model-invocation: true
---

# Grill

Drive a design from the first question to a published spec.

## Process

### 1. Find the Target branch

When `docs/skillworks/loop.json` is missing on disk, follow [On an Export branch](#on-an-export-branch).

When it is on disk, read `target-branch` and `export` in `steering-file docs/skillworks/loop.json`:

- A branch name is the Target branch. Go on to step 2.
- `pr` with `export` set to `true`: the grill cut the Target branch on the Export branch, and this session is on it. Go on to step 2.
- `pr` without the Export is PR mode. The Target branch is the branch this session is on: the developer's own branch, which the developer made by the team's own rule. Check it before the first question. Run `own-branch`, the one command that checks it, so the steps are the same in every run:

  ```bash
  own-branch
  ```

  It prints the branch, and the grill writes every word and ADR there. When it refuses, the branch cannot hold a design: it is the default branch, a branch under `skillworks/`, or no branch. Then stop the grill there. Ask no question, and write nothing. Pass on what it said, which tells the developer what to do.

In PR mode cut no branch, open no pull request, and make no `gh` call to find the default branch. The developer opens the one pull request, from their own branch, after the loop Lands the spec's tickets on it.

#### On an Export branch

When `docs/skillworks/loop.json` is missing on disk, this session is on an Export branch: the developer's own branch, which holds no Steering. Cut the spec's Target branch before the first question, so the whole design runs on a branch that holds the Steering. Run `cut-target-branch`, the one command that cuts it:

```bash
cut-target-branch
```

It rebases the Steering branch, `skillworks/steering`, onto the commit the Export branch sits on and pushes it to `origin`. Then it cuts the Target branch, `skillworks/spec/<the Export branch>`, from the Steering branch, pushes it, and switches to it. Run no git step of your own to make either branch, so the steps are the same in every run.

Then go on to step 2, as on any branch. Read nothing more after the cut: the session already holds the Steering, because it was loaded when the session started.

Open no pull request, and make no `gh` call to find the default branch. The developer opens the one pull request, from the Export branch, after the loop Exports onto it.

When the command refuses, it cut nothing, so stop the grill there. Ask no question. Pass on what the command said, and add one thing by its cause:

- When the Target branch already exists, add that the developer switches to that branch and starts a new session there.
- When the Steering branch does not rebase, the refusal names each file. Add that the developer mends those files on `skillworks/steering`, pushes it, and starts again on the Export branch.
- When no Steering branch is on `origin`, add nothing. The refusal says how to make one.

### 2. Interview under both disciplines

Call the Skill tool with "skillworks:grilling", then with "skillworks:domain-modeling". The first owns the questions, the
second owns the words. Both run on every round.

### 3. Walk the Surfaces when the frontier is empty

A Surface is a place a change can have to reach besides the code that does the work, such as the
README or the user docs. `steering-file docs/skillworks/surfaces.md` lists the team's Surfaces, one `##` section each,
with where it lives, the question to ask and what to capture. A `##` inside a code fence is an
example, not a Surface. A file with no Surface in it means skip this step. So does a non-zero status from `steering-file`, because then there is no file.

The design is settled now, so each question can fit it. Walk the Surfaces by four rules:

- Ask about one Surface at a time, with the Surface's own question, and never present the list.
- Skip a Surface the change does not touch, without asking about it.
- Capture each answer as a requirement that travels with the spec: what the Surface has to say once
  the change Lands, shaped by the Surface's "What to capture".
- Point at a Surface's content by its path, and never copy it into the answer.

An answer that reopens the design goes back to step 2 as the next round.

The README Surface is the Surface whose heading is `## The README`, outside a code fence. When the
team has one, ask its question as any other. When the answer is that the change deserves README text
beyond what its "What to capture" allows, capture only what the limit allows, and keep the rest for
the gate: it goes into the spec's Out of Scope as "the README: a focused session". Nothing in the loop
builds that session, so file no issue for it.

### 4. Sum up

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

### 5. On yes, write the spec

Call the Skill tool with "skillworks:to-spec". Then end with the spec number it publishes and the
next command, `/skillworks:spec-loop <n>` with that number, and name no other skill.

On no, the frontier was not empty. Take what the developer said as the next round and go back to
step 2.

## When a pull lands on settled ground

`skillworks:domain-modeling` reports when a pull brings down a teammate's change to ground this session already
settled.

Carry that report to the developer as questions. For each decision the change reopens, give the
question, the answer this session gave it, and the teammate's wording that puts that answer in
doubt. Ask them as the next round. The developer reads which decisions are open again, rather than
working it out from a diff.
