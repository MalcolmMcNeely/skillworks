---
name: what-next
description: Ask which skill fits your situation. A router over the skills in the Plugin.
disable-model-invocation: true
---

# What Next

You don't remember every skill, so ask.

## The Dev loop: idea → landed

The **Dev loop** is two commands, one for each stage. It takes an idea to work that has landed.

1. **`/skillworks:grill`**
2. **`/skillworks:spec-loop <n>`**

Each stage names only the next one. Every other skill is either a step the Dev loop runs for you or a skill for any time, both below.

**`/skillworks:grill`** sharpens the idea with questions. Start here whenever you are **working in a working directory**: it's stateful, retaining what it learns in `CONTEXT.md` and ADRs. When the questions run out it sums up the shape it settled and asks you to confirm it. That is the one gate: on your yes it writes the spec itself and gives you its number `<n>`, so a satisfied Grill never sits idle waiting for you to remember a command.

If a question needs a runnable answer (state, business logic, a UI you have to see), detour through **`/skillworks:prototype`** before you say yes. A prototype lives in its own directory, so **`/skillworks:handoff`** carries the question out to it and the answer back.

**`/skillworks:spec-loop <n>`** builds the spec the Grill published. Type it, then walk away. Typing the command is the whole of your consent, and nothing after it asks you anything until the end. When the spec has no tickets, the driver cuts them first, as a step of its own, and the slices appear in the loop log. It publishes them as the spec's own tickets on its Tracker, as `docs/agents/issue-tracker.md` says. The driver then picks the next unblocked ticket and spends **eight steps** on it, in order:

<!-- steps -->
build → standards → spec → architecture → fix → sweep → suite → finish

That line is held to the driver's own list by a test, so a step added there fails the suite until this document names it. The mark is what the test finds; the prose around it is free to be reworded. **`build`** runs `/skillworks:implement <n> --stop-after-tests` and leaves the change uncommitted; **`standards`**, **`spec`** and **`architecture`** each read that change, report under a heading of their own, and fix what they find; **`fix`** runs `/skillworks:implement <n> --fix` and is the one session holding all three reports at once, so a disagreement between two axes is settled there; **`sweep`** runs `/skillworks:comment-sweep` and is the last step that writes, so nothing can put back a comment it cut; **`suite`** is the driver's own, which runs the whole suite itself and reads the result, so the gate saying a ticket is done rests on nothing a session said about itself, and a machine short of what the Suite file needs stops the loop rather than reaching a session; **`finish`** runs `/skillworks:implement <n> --finish`, which runs no tests of its own, is handed the passing output so its Closing note still names what proved the work, and commits and closes the ticket. The Suite file sets how many times a red suite runs before it is believed, once unless it says more; still red on every run and the loop goes back to **`fix`**, then **`sweep`**, then **`suite`**, once and once only, and a second red stops it with the worktree left to be read. A separate landing script then lands the ticket: it rebases onto the newest Target branch, runs the suite again, and pushes, so every ticket before a stop is already on the remote. Then the driver picks the next one. It stops at the first failure and resumes where it stopped. It ends with three steps, in order: the drift check, which compares the whole diff against the spec — the one check no per-ticket test can do; the Name check, which reads the whole diff against the glossary; and the full run, which runs the whole Suite on the newest Target branch with no Proofs and no images. Reach the end clean and it asks you the one question the loop has left: close the spec? When the spec is reviewed as one pull request, it asks nothing: the driver marks the pull request ready, and a person reviews and merges it.

A team steers each review axis in its review file: `docs/agents/review-standards.md` for Standards, `docs/agents/review-spec.md` for Spec, and `docs/agents/review-architecture.md` for Architecture. Each holds the team's own checks and a "Do not report" list, and the loop and `/skillworks:review-changes` both read it.

### Context hygiene

Keep the Grill in **one unbroken context window** — don't compact or clear until it has published the spec — so the questions and the spec build on the same thinking. After that the hygiene is not yours to keep: the driver starts a new process per step, so every Session gets a genuinely empty window whatever you do with this one.

The limit on this is the **[Smart zone](SMART-AND-DUMB-ZONES.md)**: the part of the window (about 150k tokens on the strongest models) in which the model still keeps every instruction it was given. Past it is the **Dumb zone**, where the model leaves things out and still sounds sure. If a session approaches the line before the spec is published, don't push on — `/compact` at the nearest phase boundary and carry on (see Phase boundaries).

## What is open

Asked what is open, or which ticket is next, read the Tracker. `tracker` in `docs/agents/loop.json` names it, and `docs/agents/issue-tracker.md` says how to read it. Read through those docs, and make no call of your own that they do not name.

- **Files**: list the open specs and their startable tickets, from `.specs/` on the remote, as "List what is open" in the tracker docs says. Name a spec by its number and title, and a ticket as `<spec>/<ticket>` with its title. A spec with a startable ticket goes on at `/skillworks:spec-loop <spec>`.
- **GitHub**: the open work is on GitHub Issues, so point the user there.

## Steps the Dev loop runs for you

The Dev loop runs each of these itself. A developer may type one for a reason the Dev loop does not cover, and the Dev loop never asks them to.

- **`/skillworks:to-spec`** — turns the Grill's thread into a spec. The Grill runs it on your yes.
- **`/skillworks:to-tickets`** — cuts a spec into **tracer-bullet tickets** and works out the blocking edges between them. The driver runs it before the first ticket, when a spec has none.
- **`/skillworks:implement`** — builds one ticket. The driver's `build`, `fix` and `finish` steps each run one of its sections, a flag picking the one each step needs. Run by hand with no flag, it works through all seven sections in order, and its Reviewing section runs `/skillworks:review-changes`.
- **The review axes**, **`/skillworks:review-standards`**, **`/skillworks:review-spec`** and **`/skillworks:review-architecture`** — the `standards`, `spec` and `architecture` steps. Each reads the uncommitted change against its review file.
- **`/skillworks:comment-sweep`** — the `sweep` step. It cuts comments back to what the comments rule keeps.
- **`/skillworks:spec-drift`** — the drift check, which reads the whole diff against the spec after the last ticket.
- **`/skillworks:spec-names`** — the Name check, which reads the whole diff against the glossary after the drift check.
- **`/skillworks:resolve-conflict`** — resolves the conflict a ticket's rebase onto its Target branch hits, in the session that built the ticket, against **the other side** the driver hands it. The landing script runs it when its rebase conflicts.

## Skills for any time

Reach for these whenever they fit. The Dev loop never asks for them, and they never stand in for it.

- **`/skillworks:tdd`** — build a concrete behaviour test-first, without a full spec. `implement` calls it for every change that has behaviour to test.
- **`/skillworks:review-changes`** — review a branch or PR against a fixed point. It follows the same axis steps as the loop's review step, and reports without editing. Reach for Claude Code's own `/code-review` when you want a check on correctness alone.
- **`/skillworks:grilling`** — the interview primitive itself: rounds, the frontier, facts are the agent's job and decisions are yours. `/skillworks:grill` is the named way in, and `/skillworks:improve-codebase-architecture` runs it internally. Reach for it directly only when you want the interview with no wrapper around it.
- **`/skillworks:domain-modeling`** — sharpen the project's *domain* language: challenge a fuzzy term, resolve an overloaded word ("account" doing three jobs), record a hard-to-reverse decision as an ADR. It's the active discipline `/skillworks:grill` drives to keep `CONTEXT.md` a clean glossary.
- **`/skillworks:codebase-design`** — the deep-module vocabulary (module, interface, depth, seam, adapter, leverage, locality) for designing a module's *shape*: a lot of behaviour behind a small interface at a clean seam. `/skillworks:tdd` and `/skillworks:improve-codebase-architecture` both speak it.
- **`/skillworks:diagnosing-bugs`** — for the hard bugs: the one that resists a first glance, the intermittent flake, the regression that crept in between two known-good states. It refuses to theorise until it has a **tight feedback loop** — one command that already goes red on *this* bug — then fixes with a regression test. It ends there: it has no post-mortem and hands off to no other skill.
- **`/skillworks:prototype`** — a small, throwaway program that answers one design question: does this state model feel right, or what should this UI look like. Throwaway is a constraint on how the code is written, not a promise to destroy it: the answer folds into the real code, and the prototype itself is kept as a **primary source** on a `prototype/<name>` branch out of the Target branch, pointed at from the implementation issue.
- **`/skillworks:unslop`** — cut AI tells from prose a human will read: docs, READMEs, commit messages, issues. Reach for it whenever writing reads as puffed up or padded.
- **`/skillworks:improve-codebase-architecture`** — run whenever you have a spare moment to keep the codebase good for agents to operate in. It surfaces **deepening opportunities**; picking one _generates an idea_ you can take into the Dev loop at `/skillworks:grill`. It's the survey that finds the candidates; `/skillworks:codebase-design` is the bench you design the chosen one on.
- **`/skillworks:architecture-tests`** — the step after setup. It turns the rules in `docs/agents/rules/` into architecture tests the team owns, and wires each one into the Suite. Run it again when the repo gains a language or a rule.
- **`/skillworks:handoff`** — write a portable markdown file, for a new harness, a new directory or a colleague. See Phase boundaries.

## Phase boundaries

A **phase** is a chunk of work inside a session — the grilling, the implementation, the QA. At the **boundary** between two of them you have five options, and picking between them is the fuzziest decision in this whole map:

- **Continue** — stay put. Costs nothing, loses nothing.
- **`/clear`** — empty the window, when nothing here matters to what's next.
- **`/skillworks:handoff`** — write a portable markdown file. Narrow: only for a **new harness**, a **new directory**, a **colleague**, or forking a side task **mid-phase**. What it buys is portability.
- **Subagent** — send a tightly-scoped task to its own window and get a report back.
- **`/compact`** — compress this context and seed a fresh session with it. The **default**, at the bottom of the tree rather than the first reach.

Read [PHASE-BOUNDARIES.md](PHASE-BOUNDARIES.md) for the ordered tree — the five questions, the reasoning behind each branch, and why the primary-source cost makes **Continue** the one to rule out first. Make the decision **at** a boundary; mid-phase, continue or split the rest into subagents.

## Precondition

**`/skillworks:skillworks-setup`** — run once per repo before your first Dev loop. It asks which Tracker the team uses, `github` or `files`, and seeds the Steering the other skills read: the rules, the tracker and domain docs, the review files and a starting Suite file. With `github` it creates the `ready-for-agent` label. The repo needs a remote with either Tracker.
