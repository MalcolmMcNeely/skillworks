---
name: to-tickets
description: Break a plan, spec, or the current conversation into a set of tracer-bullet tickets, each declaring its blocking edges, published to the configured tracker — edges in each ticket file's frontmatter with the files Tracker, or native blocking links on GitHub.
---

# To Tickets

Break a plan, spec, or conversation into a set of **tickets** — tracer-bullet vertical slices, each declaring the tickets that **block** it.

The issue tracker should have been provided to you. Its section "The ticket shape" is the team's taste in tickets: their size, their title and the template each one fills. Read it before step 3, and shape every ticket by it.

If `docs/agents/issue-tracker.md` is missing, or holds no section "The ticket shape", stop. Tell the user which is missing, the file or the section, that `/skillworks:skillworks-setup` writes it, and that no ticket was made.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes a reference (a spec path, an issue number or URL, or a spec number with the files Tracker) as an argument, fetch it and read its full body and comments. With the files Tracker, the tracker docs say where a spec's `spec.md` is read from.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. Ticket titles and descriptions should use the project's domain glossary vocabulary, and respect ADRs in the area you're touching.

Look for opportunities to prefactor the code to make the implementation easier. "Make the change easy, then make the easy change."

### 3. Draft vertical slices

Break the work into **tracer bullet** tickets.

<vertical-slice-rules>

- Each slice cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests) — vertical, NOT a horizontal slice of one layer
- A completed slice is demoable or verifiable on its own
- Each slice is sized as the ticket shape says
- Any prefactoring should be done first

</vertical-slice-rules>

Give each ticket its **blocking edges** — the other tickets that must complete before it can start. A ticket with no blockers can start immediately.

**Keep each Surface in step, ticket by ticket.** A Surface is a place a change can have to reach besides the code that does the work, such as the README or the user docs. The spec's Surfaces section names each Surface the change touches, with what it has to say once the change Lands. Place each Surface's work inside the ticket whose change needs it, and name the Surface and its requirement in that ticket's body, so every ticket that Lands leaves each Surface in step. No ticket only updates a Surface: a Surface would be wrong between the ticket that changed the behaviour and the one that described it. A spec whose Surfaces section says "None", or that has none, adds nothing here.

**Wide refactors are the exception to vertical slicing.** A **wide refactor** is one mechanical change — rename a column, retype a shared symbol — whose **blast radius** fans across the whole codebase, so a single edit breaks thousands of call sites at once and no vertical slice can land green. Don't force it into a tracer bullet; sequence it as **expand–contract**. First expand: add the new form beside the old so nothing breaks. Then migrate the call sites over in batches sized by blast radius (per package, per directory), each batch its own ticket blocked by the expand, keeping CI green batch to batch because the old form still exists. Finally contract: delete the old form once no caller remains, in a ticket blocked by every migrate batch. When even the batches can't stay green alone, keep the sequence but let them share an integration branch that all block a final integrate-and-verify ticket — green is promised only there.

### 4. Show the breakdown

Present the proposed breakdown as a numbered list. For each ticket, show:

- **Title**: short descriptive name
- **Blocked by**: which other tickets (if any) must complete first
- **What it delivers**: the end-to-end behaviour this ticket makes work

Show it every time, whoever invoked you. Even where nobody is asked to approve it, the user reads the slices while the work runs.

**When you were told to skip the approval questions, skip them and go straight to step 5.** Only an unattended run asks for that, and the person who started it consented then.

Otherwise ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the blocking edges correct — does each ticket only depend on tickets that genuinely gate it?
- Should any tickets be merged or split further?

Iterate until the user approves the breakdown.

### 5. Publish the tickets to the configured tracker

Publish the tickets you showed. **How** depends on `tracker` in `docs/agents/loop.json` — the tickets are the same either way, only the shape of the blocking edges changes:

- **`files`** → write one file per ticket to a folder outside the repo, such as `$(mktemp -d)`, named `<NN>-<slug>.md` and numbered from `01` in dependency order, blockers first. Each file opens with the frontmatter the tracker docs show: `status: open`, `blocked-by` listing the numbers of the tickets that block it, such as `blocked-by: [1, 2]`, and `claimed-by` left empty, because the loop sets it. The ticket shape's title and body follow, the title as a `# ` heading. Then publish every file in one call:

  ```bash
  tracker-publish tickets <spec> <file>...
  ```

  It pushes the files into the spec's `tickets/` folder, on the spec's branch in `spec` mode. It turns down a set the loop could not follow: a file with no number, two files with one number, a ticket not `open`, a `claimed-by` already set, or a blocker that is not a ticket before it. It also turns down a spec that already has tickets, so a second run adds nothing. The folder is the parent relationship, so nothing more links a ticket to its spec.
- **`github`** → publish one issue per ticket in dependency order (blockers first) so each ticket's blocking edges can reference real identifiers. Use the platform's native blocking / sub-issue relationship where it has one; otherwise set each ticket's "Blocked by" to the blocking issues. Apply the `ready-for-agent` label unless instructed otherwise — the tickets are agent-grabbable by construction.

Each ticket takes its title and its body from the ticket shape.

Work the **frontier**: any ticket whose blockers are all done. For a purely linear chain that means top to bottom.

**With `github`, when the source was an existing issue, make every ticket a child of it on the tracker.** Not a `Parent:` line in the body — the native parent/child relationship, so it is queryable. `/skillworks:spec-loop` reads a spec's children to find its own work and ignores everything else, which is the only thing stopping two people's loops taking each other's tickets. Your tracker doc carries the exact calls.

**Leave the parent issue open**, or with `files` the spec's `status: open`. It is the loop's anchor and the drift check reads it at the end. With `github` the human closes it when the work merges, and with `files` the loop closes it. (Without a loop — a plain conversation, no parent issue on the tracker — there is nothing to leave open.)
