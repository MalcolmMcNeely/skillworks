---
name: what-next
description: Ask which skill or flow fits your situation. A router over the skills in the Plugin.
disable-model-invocation: true
---

# What Next

You don't remember every skill, so ask.

A **flow** is a path through the skills. Most paths run along one **main flow**, and one **on-ramp** merges onto it. Everything else is standalone, or a vocabulary layer that runs underneath.

## The main flow: idea → ship

The route most work travels. You have an idea and want it built.

1. **`/grill-with-docs`** — sharpen the idea by interview. Start here whenever you are **working in a working directory**: it's stateful, retaining what it learns in `CONTEXT.md` and ADRs. When the questions run out it sums up the shape it settled and asks you to confirm it. That is the one gate: on your yes it runs **`/to-spec`** itself, turning the thread into a spec issue, so a satisfied grill never sits idle waiting for you to remember a command.
2. **Branch — can you settle every question in conversation?** If a question needs a runnable answer (state, business logic, a UI you have to see), detour through a prototype, bridged by **`/handoff`** in both directions (a prototype lives in its own directory, which is exactly what `/handoff` is for — see Phase boundaries):
   - **`/handoff`** out, then open a fresh session against that file,
   - **`/prototype`** to answer the question with throwaway code,
   - **`/handoff`** back what you learned, and reference it from the original idea thread.
3. **Branch — is this a multi-session build?**
   - **Yes** → **`/spec-loop <spec#>`** on the spec the grill published, then walk away. Typing the command is the whole of your consent, and nothing after it asks you anything until the end. It cuts the spec into tickets, prints the slices for you to read, publishes them as **sub-issues of the spec**, then hands the rest to `scripts/spec_loop.py`. The script picks the next unblocked ticket and spends **eight steps** on it, in order:

     <!-- steps -->
     build → standards → spec → architecture → fix → sweep → suite → finish

     That line is held to the driver's own list by a test, so a step added there fails the suite until this document names it. The mark is what the test finds; the prose around it is free to be reworded. **`build`** runs `/implement <n> --stop-after-tests` and leaves the change uncommitted; **`standards`**, **`spec`** and **`architecture`** each read that change, report under a heading of their own, and fix what they find; **`fix`** runs `/implement <n> --fix` and is the one session holding all three reports at once, so a disagreement between two axes is settled there; **`sweep`** runs `/comment-sweep` and is the last step that writes, so nothing can put back a comment it cut; **`suite`** is the driver's own, which runs the whole suite itself and reads the result, so the gate saying a ticket is done rests on nothing a session said about itself, and a machine short of Docker or `uv` stops the loop rather than reaching a session; **`finish`** runs `/implement <n> --finish`, which runs no tests of its own, is handed the passing output so its closing comment still names what proved the work, and commits and closes the ticket. A red suite is run a second time before it is believed, because the container-backed tests flake here; still red on both runs and the loop goes back to **`fix`**, then **`sweep`**, then **`suite`**, once and once only, and a second red stops it with the worktree left to be read. A separate landing script then lands the ticket: it rebases onto the newest `main`, runs the suite again, and pushes, so every ticket before a stop is already on the remote. Then the script picks the next one. It stops at the first failure and resumes where it stopped. It finishes with **`/spec-drift`**, which compares the whole diff against the spec — the one check no per-ticket test can do. Reach the end clean and it asks you the one question the flow has left: close the spec?
   - **No** → **`/implement`** right here, in the same context window, against the spec the grill published.

   Either way, **`/implement`** builds each issue by driving **`/tdd`** internally — one red-green slice at a time. Run by hand it works through seven sections, in order: **Before you start** reads the ticket and its parent spec, and refuses a ticket something else still blocks; **Building** writes the code test-first until the typecheck is clean and the tests it touched pass; **Reviewing** runs **`/code-review`** on the uncommitted change, which fans all three axes out at once; then **Fixing**, **Sweeping comments**, **Running the suite** and **Finishing**, which do what the loop's `fix`, `sweep`, `suite` and `finish` steps above do. The loop's `build`, `fix` and `finish` steps call those same sections, a flag on `/implement` picking the one each step needs, so the developer at the keyboard and the driver follow one set of rules. Reach for **`/tdd`** on its own when you just want to build a concrete behaviour test-first without a full spec, and **`/code-review`** on its own whenever you want to review a branch or PR against a fixed point.

### Context hygiene

Keep steps 1–3 in **one unbroken context window** — don't compact or clear until `/spec-loop` has published the tickets — so the grilling, spec, and tickets all build on the same thinking. After that the hygiene is not yours to keep: the script starts a new process per ticket, so every `/implement` gets a genuinely empty window whatever you do with this one.

The limit on this is the **[Smart zone](SMART-AND-DUMB-ZONES.md)**: the part of the window (about 150k tokens on the strongest models) in which the model still keeps every instruction it was given. Past it is the **Dumb zone**, where the model leaves things out and still sounds sure. If a session approaches the line before the tickets are published, don't push on — `/compact` at the nearest phase boundary and carry on (see Phase boundaries).

## On-ramps

A starting situation that generates work, then merges onto the main flow.

- **Something's broken** → **`/diagnosing-bugs`**. For the hard ones: the bug that resists a first glance, the intermittent flake, the regression that crept in between two known-good states. It refuses to theorise until it has a **tight feedback loop** — one command that already goes red on *this* bug — then fixes with a regression test. Its post-mortem hands off to **`/improve-codebase-architecture`** when the real finding is that there's no good seam to lock the bug down.

## Codebase health

Not feature work — upkeep.

- **`/improve-codebase-architecture`** — run whenever you have a spare moment to keep the codebase good for agents to operate in. It surfaces **deepening opportunities**; picking one _generates an idea_ you can take into the main flow at `/grill-with-docs`. It's the survey that finds the candidates; **`/codebase-design`** (below) is the bench you design the chosen one on.

## Vocabulary underneath

Two model-invoked references that run *beneath* the other skills — each the single source of truth for its vocabulary. Reach for them directly when the **words**, not the process, are the problem; or let the skills above pull them in.

- **`/domain-modeling`** — sharpen the project's *domain* language: challenge a fuzzy term, resolve an overloaded word ("account" doing three jobs), record a hard-to-reverse decision as an ADR. It's the active discipline `/grill-with-docs` drives to keep `CONTEXT.md` a clean glossary.
- **`/codebase-design`** — the deep-module vocabulary (module, interface, depth, seam, adapter, leverage, locality) for designing a module's *shape*: a lot of behaviour behind a small interface at a clean seam. `/tdd` and `/improve-codebase-architecture` both speak it.

## Phase boundaries

A **phase** is a chunk of work inside a session — the grilling, the implementation, the QA. At the **boundary** between two of them you have five options, and picking between them is the fuzziest decision in this whole map:

- **Continue** — stay put. Costs nothing, loses nothing.
- **`/clear`** — empty the window, when nothing here matters to what's next.
- **`/handoff`** — write a portable markdown file. Narrow: only for a **new harness**, a **new directory**, a **colleague**, or forking a side task **mid-phase**. What it buys is portability.
- **Subagent** — send a tightly-scoped task to its own window and get a report back.
- **`/compact`** — compress this context and seed a fresh session with it. The **default**, at the bottom of the tree rather than the first reach.

Read [PHASE-BOUNDARIES.md](PHASE-BOUNDARIES.md) for the ordered tree — the five questions, the reasoning behind each branch, and why the primary-source cost makes **Continue** the one to rule out first. Make the decision **at** a boundary; mid-phase, continue or split the rest into subagents.

## Inside other skills

Each one runs because another skill reached for it. This map routes you to that caller, never to the skill inside, so read these as parts rather than as steps.

- **`/to-tickets`** — cuts a spec into **tracer-bullet tickets** and works out the blocking edges between them. `/spec-loop` reaches for it, at step 3 above.
- **`/resolve-conflict`** — resolves the conflict a ticket's rebase onto `main` hits, in the session that built the ticket, against **the other side** the driver hands it. `/spec-loop` will reach for it once its driver rebases per ticket.

## Standalone

Off the main flow entirely.

- **`/grilling`** — the interview primitive itself: rounds, the frontier, facts are the agent's job and decisions are yours. `/grill-with-docs` is the named way in, and `/improve-codebase-architecture` runs it internally. Reach for it directly only when you want the interview with no wrapper around it.
- **`/prototype`** — a small, throwaway program that answers one design question: does this state model feel right, or what should this UI look like. Throwaway is a constraint on how the code is written, not a promise to destroy it: the answer folds into the real code, and the prototype itself is kept as a **primary source** on a `prototype/<name>` branch out of main, pointed at from the implementation issue. It's the detour in step 2 of the main flow, but reach for it any time a design question is hard to settle on paper.
- **`/unslop`** — cut AI tells from prose a human will read: docs, READMEs, commit messages, issues. Reach for it whenever writing reads as puffed up or padded.

## Precondition

**`/skillworks-setup`** — run once per repo before your first engineering flow. It creates the `ready-for-agent` label on GitHub and writes the tracker and domain-doc references the other skills read. GitHub only.
